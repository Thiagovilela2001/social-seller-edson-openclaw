#!/usr/bin/env python3
"""Gera a tabela de credenciais a partir do registro de capacidades.

POR QUE GERAR, E NAO ESCREVER A MAO
    A pergunta "quais credenciais eu preciso?" tem UMA fonte de verdade:
    `capacidades.py`. Checklist escrito a mao diverge no primeiro commit — e
    checklist divergente e pior que checklist nenhum, porque manda a pessoa
    buscar a coisa errada.

    Aqui a lista sai do codigo. Se alguem adicionar uma capacidade sem declarar a
    variavel, ela aparece como "sem credencial mapeada" em vez de ficar invisivel.

MODO --check
    Compara o arquivo em disco com o que seria gerado agora. Serve para CI: se
    divergir, o documento esta mentindo sobre o codigo.

Uso:
    python tools/checklist_credenciais.py            # imprime
    python tools/checklist_credenciais.py --write    # grava docs/CREDENCIAIS-TABELA.md
    python tools/checklist_credenciais.py --check    # falha se estiver desatualizado
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import capacidades as cap  # noqa: E402

DESTINO = RAIZ / "docs" / "CREDENCIAIS-TABELA.md"

INTRO = """<!-- GERADO por tools/checklist_credenciais.py — NAO editar a mao. -->
# Tabela de credenciais

Fonte unica: `capacidades.py`. Regerar com
`python tools/checklist_credenciais.py --write`.

> **Ter a credencial NAO libera a capacidade.** A escada da §02 continua valendo:
> `configurada` e diferente de `liberada`. Falta a leitura implementada e a
> homologacao contra o recurso autorizado.
"""


def montar() -> str:
    por_var: dict[str, list[tuple[str, cap.Capacidade]]] = {}
    sem_variavel: list[str] = []

    for nome, c in cap.CAPACIDADES.items():
        if c.variaveis:
            for v in c.variaveis:
                por_var.setdefault(v, []).append((nome, c))
        else:
            sem_variavel.append(nome)

    liberadas = sum(1 for c in cap.CAPACIDADES.values() if c.liberada())

    linhas = [
        INTRO,
        "## Resumo",
        "",
        f"- capacidades declaradas: **{len(cap.CAPACIDADES)}**",
        f"- liberadas: **{liberadas}**",
        f"- variaveis de credencial mapeadas: **{len(por_var)}**",
        f"- capacidades sem credencial mapeada: **{len(sem_variavel)}** "
        "(nao dependem de fornecedor externo)",
        "",
        "## Variaveis",
        "",
        "| Variavel | Familias | O que ela destrava |",
        "|---|---|---|",
    ]

    for var in sorted(por_var):
        itens = por_var[var]
        familias = sorted({c.familia for _, c in itens})
        destravadas = ", ".join(f"`{n}`" for n, _ in sorted(itens))
        linhas.append(f"| `{var}` | {', '.join(familias)} | {destravadas} |")

    if sem_variavel:
        linhas += [
            "",
            "## Sem credencial mapeada",
            "",
            "Nao dependem de fornecedor externo (ou sao do proprio motor):",
            "",
        ]
        linhas += [f"- `{n}`" for n in sorted(sem_variavel)]

    return "\n".join(linhas) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Tabela de credenciais")
    parser.add_argument("--write", action="store_true", help="grava o arquivo")
    parser.add_argument("--check", action="store_true", help="falha se desatualizado")
    args = parser.parse_args()

    gerado = montar()

    if args.write:
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        DESTINO.write_text(gerado, encoding="utf-8", newline="\n")
        print(f"gravado: {DESTINO}")
        return 0

    if args.check:
        if not DESTINO.exists():
            print(f"FAIL  {DESTINO.name} nao existe — rode --write")
            return 1
        atual = DESTINO.read_text(encoding="utf-8")
        if atual != gerado:
            print(
                "FAIL  a tabela de credenciais esta desatualizada em relacao ao codigo. "
                "Rode: python tools/checklist_credenciais.py --write"
            )
            return 1
        print("PASS  tabela de credenciais em dia com capacidades.py")
        return 0

    print(gerado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
