"""Interface de linha de comando."""

import argparse

import requests

from .client import RothbardPPRClient
from .config import PPRConfig
from .data import WorldBankDataLoader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ranking PPR com dados do Banco Mundial (USD correntes).")
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--alpha", type=float, default=2.0, help="Penalidade de G, entre 0 e 2.")
    parser.add_argument("--min-population", type=int, default=100_000)
    parser.add_argument("--countries", nargs="+", help="Códigos de três letras: BRA USA ARG")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--export", metavar="ARQUIVO", help="Dataset completo em .csv ou .json.")
    parser.add_argument("--cache-dir", default=".cache/ppr")
    parser.add_argument("--refresh", action="store_true", help="Atualizar o cache pela API.")
    args = parser.parse_args(argv)
    try:
        if args.top < 1:
            raise ValueError("--top deve ser positivo.")
        client = RothbardPPRClient(
            PPRConfig(args.year, args.alpha, args.min_population, args.countries),
            WorldBankDataLoader(args.cache_dir),
        )
        client.load_data(refresh=args.refresh)
        data = client.calculate()
        if data.empty:
            print("Nenhum país com dados essenciais válidos para os filtros selecionados.")
        else:
            print(f"PPR {args.year} | alpha={args.alpha:g} | {len(data)} economias | USD correntes")
            print(client.get_top(args.top).to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
        if args.export:
            print(f"Exportado: {client.export(args.export)}")
    except (ValueError, OSError, requests.RequestException) as exc:
        parser.exit(1, f"Erro: {exc}\n")
    return 0
