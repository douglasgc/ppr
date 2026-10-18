"""Atalho compatível com `python ppr_client.py --year 2023`."""

from ppr import PPRConfig, RothbardPPRClient, RothbardEngine, WorldBankDataLoader
from ppr.cli import main

__all__ = ["PPRConfig", "RothbardPPRClient", "RothbardEngine", "WorldBankDataLoader"]

if __name__ == "__main__":
    raise SystemExit(main())
