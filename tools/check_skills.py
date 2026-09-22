#!/usr/bin/env python3
"""Verificador estrutural das skills — barato, offline, sem dependência.

O QUE ELE É: um conferidor de ESTRUTURA do frontmatter. Não é um parser YAML
completo (o projeto é stdlib-only e não traz PyYAML de propósito). Ele pega os
erros que realmente acontecem numa conversão de runtime:

  - frontmatter ausente ou não fechado
  - `name` / `description` faltando ou vazios  (o OpenClaw exige os dois)
  - sobra de vocabulário do runtime antigo (`hermes:`)
  - bloco `metadata` apontando para runtime que não é `openclaw`
  - descrição longa demais (custo de prompt por skill)

O QUE ELE NÃO É: validação de sintaxe YAML/JSON5. Um erro de indentação pode
passar aqui e aparecer no carregamento real do OpenClaw. Isso está declarado
para o verificador não virar garantia que ele não dá.

Uso:  python tools/check_skills.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# O OpenClaw carrega skills de <workspace>/skills (precedência mais alta). Por isso
# elas moram dentro do workspace do agente, e não na raiz do repo.
SKILLS = RAIZ / "agent" / "workspace" / "skills"

# Custo de prompt: o OpenClaw injeta name+description de toda skill elegível.
DESCRICAO_MAX_CHARS = 200

falhas: list[str] = []
ok: list[str] = []


def checar(cond: bool, descricao: str) -> None:
    (ok if cond else falhas).append(descricao)


def frontmatter(caminho: Path) -> str | None:
    texto = caminho.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        return None
    fim = texto.find("\n---", 3)
    if fim == -1:
        return None
    return texto[3:fim]


def valor(bloco: str, chave: str) -> str | None:
    m = re.search(rf"^{chave}:\s*(.+)$", bloco, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else None


def main() -> int:
    print("=== verificador estrutural das skills ===\n")

    pastas = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    checar(bool(pastas), f"{len(pastas)} skill(s) encontradas em skills/")

    for pasta in pastas:
        arquivo = pasta / "SKILL.md"
        nome = pasta.name

        if not arquivo.exists():
            checar(False, f"{nome}: SKILL.md ausente")
            continue

        bloco = frontmatter(arquivo)
        if bloco is None:
            checar(False, f"{nome}: frontmatter ausente ou nao fechado (---)")
            continue

        nome_da_skill = valor(bloco, "name")
        descricao = valor(bloco, "description")

        checar(bool(nome_da_skill), f"{nome}: frontmatter tem `name` ({nome_da_skill or 'VAZIO'})")
        checar(
            nome_da_skill == nome,
            f"{nome}: `name` do frontmatter casa com a pasta ({nome_da_skill or '?'})",
        )
        checar(bool(descricao), f"{nome}: frontmatter tem `description`")
        if descricao:
            checar(
                len(descricao) <= DESCRICAO_MAX_CHARS,
                f"{nome}: descricao com {len(descricao)} chars (<= {DESCRICAO_MAX_CHARS})",
            )

        # Runtime antigo: nao pode sobrar vocabulario do Hermes no frontmatter.
        checar(
            "hermes" not in bloco.lower(),
            f"{nome}: frontmatter sem `hermes` (vocabulario do runtime antigo)",
        )

        # `metadata` so pode apontar para openclaw.
        tem_metadata = re.search(r"^metadata:", bloco, re.MULTILINE) is not None
        if tem_metadata:
            checar(
                re.search(r"^\s+openclaw:", bloco, re.MULTILINE) is not None,
                f"{nome}: bloco `metadata` aponta para `openclaw`",
            )
        else:
            checar(True, f"{nome}: sem `metadata` (skill sempre elegivel, sem gating)")

    print("=== resultado ===")
    for linha in ok:
        print(f"  PASS  {linha}")
    for linha in falhas:
        print(f"  FAIL  {linha}")
    print(f"\n{len(ok)} passaram, {len(falhas)} falharam")
    print("\nAVISO: validacao ESTRUTURAL. Sintaxe YAML/JSON5 nao e verificada aqui.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
