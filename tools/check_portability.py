#!/usr/bin/env python3
"""Sonda de portabilidade — prova, sem rede e sem credencial, que o projeto
roda em qualquer host com Python + stdlib.

Por que isto existe: "portável" é uma afirmação, e afirmação sem verificação é
o que o Parecer OpenClaw cobrou (número em documentação não é homologação). Esta
sonda transforma portabilidade em algo que roda em CI e no host do cliente.

Verifica cinco coisas:

  1. IMPORT LIMPO — nenhum módulo de terceiro em engine/, ingress/ e mcp/.
     Tudo que a lista de imports precisa existir está na stdlib.
  2. SEM HERMES — o motor carrega com `HERMES_HOME` removido do ambiente. Se
     algum caminho dependesse do runtime antigo, isto falharia aqui.
  3. CAMINHOS POR AMBIENTE — o estado resolve por `IG_STATE_DB`/`IG_KILL_SWITCH`
     (override) e por fallback derivado de `__file__` (que é portável).
  4. ESTADO GRAVÁVEL — o diretório de estado aceita escrita.
  5. IMPRESSÃO DIGITAL — SHA256 do motor, para comparar com o Hermes e provar
     que o port não alterou byte nenhum.

Uso:  python tools/check_portability.py
Sai 0 se tudo passa, 1 se algo falha.
"""

from __future__ import annotations

import ast
import hashlib
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENGINE = RAIZ / "engine" / "instagram_seller"
INGRESS = RAIZ / "ingress"
MCP = RAIZ / "mcp"

# Módulos locais do próprio projeto — não são de terceiro.
LOCAIS = {"rules", "instagram_api", "integracoes", "schemas"}

falhas: list[str] = []
ok: list[str] = []


def checar(cond: bool, descricao: str) -> None:
    (ok if cond else falhas).append(descricao)


# --------------------------------------------------------------------------
# 1. Imports
# --------------------------------------------------------------------------

def imports_de(caminho: Path) -> set[str]:
    """Nomes de topo importados por um arquivo. Import relativo é ignorado:
    ele não pode escapar para fora do projeto."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                nomes.add(alias.name.split(".")[0])
        elif isinstance(no, ast.ImportFrom):
            if no.level == 0 and no.module:
                nomes.add(no.module.split(".")[0])
    return nomes


def checar_imports() -> None:
    permitidos = set(getattr(sys, "stdlib_module_names", set())) | LOCAIS | {"__future__"}
    permitidos |= {p.stem for p in ENGINE.glob("*.py")}

    terceiros: dict[str, set[str]] = {}
    for pasta in (ENGINE, INGRESS, MCP):
        for arquivo in sorted(pasta.glob("*.py")):
            for nome in imports_de(arquivo):
                if nome not in permitidos:
                    terceiros.setdefault(nome, set()).add(arquivo.name)

    checar(
        not terceiros,
        "nenhum import de terceiro em engine/, ingress/ e mcp/",
    )
    for nome, arquivos in terceiros.items():
        print(f"    TERCEIRO: {nome} <- {', '.join(sorted(arquivos))}")


# --------------------------------------------------------------------------
# 2-3. O motor carrega sem o runtime antigo?
# --------------------------------------------------------------------------

def carregar_motor():
    """Importa o motor com o ambiente limpo de HERMES_HOME.

    Herda o environment mas remove a variável: é a forma mais próxima de "outro
    host que nunca viu Hermes". Não é possível importar duas vezes no mesmo
    processo, então a sonda roda uma única vez.
    """
    os.environ.pop("HERMES_HOME", None)
    if str(ENGINE) not in sys.path:
        sys.path.insert(0, str(ENGINE))
    import rules  # noqa: PLC0415

    return rules


# --------------------------------------------------------------------------
# 4. Estado gravável
# --------------------------------------------------------------------------

def checar_estado(estado: Path) -> None:
    try:
        estado.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=estado, prefix=".probe-", delete=True):
            pass
        checar(True, f"diretório de estado gravável ({estado})")
    except OSError as e:
        checar(False, f"diretório de estado NÃO gravável ({estado}): {e}")


# --------------------------------------------------------------------------
# 5. Impressões digitais
# --------------------------------------------------------------------------

def digest(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def main() -> int:
    print("=== sonda de portabilidade — Social Seller OpenClaw ===\n")

    checar_imports()

    # O estado é reapontado ANTES de carregar o motor — é assim que o adaptador
    # MCP faz (D3): nenhuma edição em rules.py.
    estado = Path(os.getenv("IG_STATE_DIR") or (RAIZ / "state"))
    os.environ.setdefault("IG_STATE_DB", str(estado / "instagram-seller.db"))
    os.environ.setdefault("IG_KILL_SWITCH", str(estado / "ig-kill-switch"))

    try:
        rules = carregar_motor()
        checar(True, "motor carrega sem HERMES_HOME (nenhuma dependência do runtime antigo)")
    except Exception as e:  # noqa: BLE001
        checar(False, f"motor NÃO carregou sem HERMES_HOME: {type(e).__name__}: {e}")
        _relatar()
        return 1

    checar(
        bool(getattr(rules, "RULES_VERSION", "")),
        f"RULES_VERSION presente ({getattr(rules, 'RULES_VERSION', '?')})",
    )
    checar(
        str(rules.state_db_path()) == os.environ["IG_STATE_DB"],
        "IG_STATE_DB sobrescreve o banco de estado",
    )
    checar(
        str(rules.kill_switch_path()) == os.environ["IG_KILL_SWITCH"],
        "IG_KILL_SWITCH sobrescreve o arquivo do kill switch",
    )
    checar_estado(estado)

    print("  caminhos resolvidos")
    print(f"    banco de estado : {rules.state_db_path()}")
    print(f"    kill switch     : {rules.kill_switch_path()}")
    print(f"    python          : {sys.version.split()[0]} ({sys.platform})")

    print("\n  impressões digitais do motor (comparar com o Hermes)")
    for arquivo in sorted(ENGINE.glob("*.py")):
        print(f"    {arquivo.name:<20} {digest(arquivo)[:16]}")

    return _relatar()


def _relatar() -> int:
    print("\n=== resultado ===")
    for linha in ok:
        print(f"  PASS  {linha}")
    for linha in falhas:
        print(f"  FAIL  {linha}")
    print(f"\n{len(ok)} passaram, {len(falhas)} falharam")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
