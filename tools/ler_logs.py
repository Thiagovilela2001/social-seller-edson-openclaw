#!/usr/bin/env python3
"""Leitor de logs JSONL de observabilidade do Social Seller.

Uso:
    python ler_logs.py [--tipo decisoes|mcp|ingress] [--exec-id ID] [--bloqueado]
        [--liberado] [--incerto] [--limit N] [--dir PATH]

Filtros podem ser combinados. Sem filtro mostra todas as linhas recentes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Fallback: deriva do proprio script se IG_STATE_DIR nao estiver setado.
RAIZ = Path(__file__).resolve().parents[1]
STATE_DIR = Path(
    Path(sys.path[0]) if sys.path[0] else RAIZ / "state"
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ler logs de observabilidade do Social Seller")
    p.add_argument(
        "--tipo",
        choices=["decisoes", "mcp", "ingress"],
        default="decisoes",
        help="Tipo de log a ler (default: decisoes)",
    )
    p.add_argument("--exec-id", help="Filtrar por execution_id")
    p.add_argument("--bloqueado", action="store_true", help="Mostrar so bloqueios")
    p.add_argument("--liberado", action="store_true", help="Mostrar so liberados")
    p.add_argument("--incerto", action="store_true", help="Mostrar so incertos")
    p.add_argument(
        "--limit", type=int, default=50, help="Maximo de linhas (default: 50)"
    )
    p.add_argument(
        "--dir",
        type=Path,
        default=STATE_DIR,
        help=f"Diretorio de state (default: {STATE_DIR})",
    )
    return p.parse_args()


def _caminho(tipo: str, base: Path) -> Path:
    mapa = {
        "decisoes": "decisoes.jsonl",
        "mcp": "mcp_traces.jsonl",
        "ingress": "ingress.jsonl",
    }
    return base / mapa[tipo]


def _formata_linha(tipo: str, linha: dict) -> dict:
    """Extrai campos relevantes para a tabela, conforme o tipo."""
    ts = linha.get("at", "")
    # Tenta deixar timestamp mais legivel
    try:
        if "T" in ts:
            dt = datetime.fromisoformat(ts.replace("+", "+00:00"))
            ts = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass

    exec_id = linha.get("execution_id", "-")

    if tipo == "decisoes":
        return {
            "timestamp": ts,
            "exec_id": exec_id[:12],
            "acao": linha.get("acao", "-"),
            "resultado": linha.get("resultado", "-"),
            "regra": linha.get("regra", "-"),
        }
    elif tipo == "mcp":
        return {
            "timestamp": ts,
            "exec_id": exec_id[:12],
            "tool": linha.get("tool", "-"),
            "igsid": linha.get("igsid", "-")[:12],
            "resultado": linha.get("resultado", "-"),
            "bloqueio": (linha.get("bloqueio") or "-")[:40],
        }
    else:  # ingress
        return {
            "timestamp": ts,
            "exec_id": exec_id[:12],
            "evento": linha.get("evento", "-"),
            "chave": linha.get("chave", "-")[:12],
            "diretiva": linha.get("diretiva", "-"),
        }


def _cabecalhos(tipo: str) -> list[str]:
    if tipo == "decisoes":
        return ["timestamp", "exec_id", "acao", "resultado", "regra"]
    elif tipo == "mcp":
        return ["timestamp", "exec_id", "tool", "igsid", "resultado", "bloqueio"]
    else:
        return ["timestamp", "exec_id", "evento", "chave", "diretiva"]


def _largura(coluna: str, valor: str) -> int:
    return max(len(coluna), len(valor))


def _imprimir_tabela(cabecalhos: list[str], linhas: list[dict[str, str]]) -> None:
    if not linhas:
        print("nenhuma linha para exibir")
        return
    valores = [[l.get(c, "-") for c in cabecalhos] for l in linhas]
    larguras = [_largura(c, max((v[i] for v in valores), key=len)) for i, c in enumerate(cabecalhos)]
    sep = "  "
    formato = sep.join(f"{{:<{l}}}" for l in larguras)
    print(formato.format(*cabecalhos))
    print(sep.join("-" * l for l in larguras))
    for v in valores:
        print(formato.format(*v))


def main() -> int:
    args = _parse_args()
    caminho = _caminho(args.tipo, args.dir)

    if not caminho.exists():
        print(f"[ler_logs] nenhum log encontrado: {caminho}")
        return 1

    linhas: list[dict] = []
    try:
        with caminho.open(encoding="utf-8") as fh:
            for linha in fh:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    dados = json.loads(linha)
                except json.JSONDecodeError:
                    continue

                # Filtros
                if args.exec_id and dados.get("execution_id") != args.exec_id:
                    continue
                if args.bloqueado and dados.get("resultado") != "bloqueado":
                    continue
                if args.liberado and dados.get("resultado") != "liberado":
                    continue
                if args.incerto and dados.get("resultado") != "incerto":
                    continue

                linhas.append(dados)
                if len(linhas) >= args.limit:
                    break
    except OSError as e:
        print(f"[ler_logs] erro ao ler {caminho}: {e}", file=sys.stderr)
        return 1

    _imprimir_tabela(_cabecalhos(args.tipo), [_formata_linha(args.tipo, l) for l in linhas])
    print(f"\n({len(linhas)} linha(s) em {caminho.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
