import json
import unittest
from unittest.mock import Mock

import requests
from fastapi.testclient import TestClient

from ppr.data import WorldBankDataLoader
from ppr.server import create_app
from tests.test_ppr import sample_data
from tests.test_presentation import china_data


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.loader = Mock(spec=WorldBankDataLoader)
        self.loader.fetch.return_value = sample_data()
        self.client = self.enterContext(TestClient(create_app(self.loader, token=""), base_url="http://127.0.0.1:8000"))

    def test_http_full_dataset_and_metadata(self):
        response = self.client.get("/api/data?min_population=0")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["metadata"]["record_count"], len(data["records"]))
        self.assertEqual(len(data["records"]), 2)
        self.assertEqual(len(data["raw_records"]), 2)
        self.assertEqual(self.client.get("/api/metadata?lang=pt").status_code, 200)
        self.assertIn("government_consumption", self.client.get("/api/metadata").json()["fields"])
        self.assertIn("/mcp", self.client.get("/llms.txt").text)
        self.assertIn("/api/data", self.client.get("/openapi.json").json()["paths"])

    def test_http_filters_invalid_arguments_and_country(self):
        result = self.client.get("/api/countries/BRA?min_population=0").json()
        self.assertEqual(result["records"][0]["rank_ppr_per_capita"], 2)
        self.assertEqual(self.client.get("/api/countries/ZZZ?min_population=0").status_code, 404)
        for query in ("alpha=3", "alpha=nan", "year=1900", "lang=es", "china_mode=partial", "sort_by=bad"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"/api/data?{query}").status_code, 422)

    def test_combined_china_http(self):
        self.loader.fetch.return_value = china_data()
        result = self.client.get("/api/data?china_mode=combined&countries=CHN_AGG&min_population=0").json()
        self.assertEqual(result["records"][0]["country_code"], "CHN_AGG")
        self.assertEqual(len(result["raw_records"]), 3)

    def test_source_failure_is_not_reported_as_empty_success(self):
        self.loader.fetch.side_effect = requests.Timeout()
        self.assertEqual(self.client.get("/api/data").status_code, 502)

    def test_bearer_auth_protects_http_and_mcp(self):
        with TestClient(create_app(self.loader, token="test-only-not-a-real-secret"), base_url="http://127.0.0.1:8000") as client:
            for path in ("/api/data", "/mcp", "/llms.txt", "/health"):
                self.assertEqual(client.get(path).status_code, 401)
            self.assertEqual(client.get("/health", headers={"Authorization": "Bearer test-only-not-a-real-secret"}).status_code, 200)

    def rpc(self, method, params=None, request_id=1):
        response = self.client.post("/mcp", headers={
            "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18",
        }, json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]

    def test_real_mcp_initialize_list_call_and_resource(self):
        initialized = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                               "clientInfo": {"name": "ppr-test", "version": "1"}})
        self.assertEqual(initialized["serverInfo"]["name"], "PPR study")
        tools = self.rpc("tools/list")["tools"]
        self.assertEqual({tool["name"] for tool in tools}, {"get_metadata", "get_dataset", "get_country"})
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools))
        result = self.rpc("tools/call", {"name": "get_dataset", "arguments": {"min_population": 0}})
        self.assertFalse(result.get("isError", False), result)
        content = result.get("structuredContent") or json.loads(result["content"][0]["text"])
        self.assertEqual(len(content["records"]), 2)
        self.assertEqual(len(content["raw_records"]), 2)
        resources = self.rpc("resources/list")["resources"]
        self.assertEqual(resources[0]["uri"], "ppr://metadata")
        resource = self.rpc("resources/read", {"uri": "ppr://metadata"})
        self.assertEqual(json.loads(resource["contents"][0]["text"])["schema_version"], "1.0")
