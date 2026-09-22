#!/usr/bin/env python3
"""Verificador do fragmento de config do agente.

Confere o arquivo contra as chaves que eu **inspecionei no schema do gateway
real** (`mcp.servers`, `agents.entries`), não contra suposição. O que ele pega:

  - JSON inválido (o arquivo é JSON estrito, e por isso é parseável de verdade —
    JSON5 com comentários não seria verificável pelo Python da stdlib)
  - chave de topo desconhecida
  - servidor MCP sem `command` nem `url`, ou com script que não existe no disco
  - `toolFilter.include` citando tool que o servidor não publica
  - skill na allowlist que não existe no workspace  (falha silenciosa clássica:
    allowlist aponta para nada e o agente sobe sem instrução)
  - `workspace` que não existe
  - segredo literal (token colado) em vez de placeholder
  - sobra de vocabulário do runtime antigo

LIMITE DECLARADO: ele valida FORMA e PRESENÇA DE ARQUIVO. Não valida o
comportamento do gateway (se ele aceita o config, se substitui `${VAR}`, se
conecta no MCP). Isso está na seção "o que ainda não foi provado" do README.

Uso:  python tools/check_agent_config.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "agent" / "openclaw.config.json"
WORKSPACE = RAIZ / "agent" / "workspace"
SKILLS_DIR = WORKSPACE / "skills"

# Chaves de topo aceitas — do schema inspecionado + o que o fragmento declara.
TOPO_ACEITO = {"mcp", "agents", "hooks", "skills", "bindings", "plugins"}

# As 3 tools que o nosso servidor MCP publica (fonte: schemas.py).
TOOLS_PUBLICADAS = {"ig_send_dm", "ig_private_reply", "ig_reply_comment"}

# Placeholders que o verificador sabe resolver para checar caminho.
RESOLVIVEIS = {"SOCIAL_SELLER_REPO": str(RAIZ)}

falhas: list[str] = []
ok: list[str] = []


def checar(cond: bool, descricao: str) -> None:
    (ok if cond else falhas).append(descricao)


def expandir(valor: str) -> tuple[str, list[str]]:
    """Troca ${VAR} resolvível pelo valor. Devolve o texto e os que sobraram."""
    restantes: list[str] = []

    def troca(m: re.Match[str]) -> str:
        nome = m.group(1)
        if nome in RESOLVIVEIS:
            return RESOLVIVEIS[nome]
        restantes.append(nome)
        return m.group(0)

    return re.sub(r"\$\{([A-Z0-9_]+)\}", troca, valor), restantes


def main() -> int:
    print("=== verificador do fragmento de config do agente ===\n")

    if not CONFIG.exists():
        print(f"FAIL  {CONFIG} nao existe")
        return 1

    bruto = CONFIG.read_text(encoding="utf-8")
    try:
        cfg = json.loads(bruto)
        checar(True, "JSON estrito valido (parseavel sem JSON5)")
    except json.JSONDecodeError as e:
        checar(False, f"JSON invalido: {e}")
        return _relatar()

    checar(
        not re.search(r"hermes", bruto, re.IGNORECASE),
        "sem vocabulario do runtime antigo (`hermes`)",
    )

    # --- segredos literais -------------------------------------------------
    padrao_segredo = r"(gho_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|EAA[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,})"
    checar(
        re.search(padrao_segredo, bruto) is None,
        "nenhum segredo literal (só placeholders ${VAR})",
    )

    # --- chaves de topo ----------------------------------------------------
    desconhecidas = set(cfg) - TOPO_ACEITO
    checar(not desconhecidas, f"chaves de topo conhecidas (extra={sorted(desconhecidas)})")

    # --- MCP ---------------------------------------------------------------
    servidores = (cfg.get("mcp") or {}).get("servers") or {}
    checar(bool(servidores), "declara ao menos um servidor MCP")

    for nome, srv in servidores.items():
        tem_command = bool(srv.get("command"))
        tem_url = bool(srv.get("url"))
        checar(
            tem_command != tem_url,
            f"mcp.servers.{nome}: tem `command` (stdio) OU `url`, nunca ambos",
        )
        checar(
            srv.get("transport") in {"stdio", "sse", "streamable-http"},
            f"mcp.servers.{nome}: transport valido ({srv.get('transport')})",
        )

        if tem_command:
            args = srv.get("args") or []
            alvo, sobrando = expandir(args[0]) if args else ("", [])
            checar(bool(args), f"mcp.servers.{nome}: declara o script em `args`")
            if args:
                checar(
                    Path(alvo).is_file(),
                    f"mcp.servers.{nome}: script existe no disco ({Path(alvo).name})",
                )

        incluir = set((srv.get("toolFilter") or {}).get("include") or [])
        if incluir:
            checar(
                incluir <= TOOLS_PUBLICADAS,
                f"mcp.servers.{nome}: toolFilter.include so cita tool publicada ({sorted(incluir)})",
            )

        # Credenciais precisam ser placeholder, nunca valor.
        for chave, valor in (srv.get("env") or {}).items():
            if isinstance(valor, str):
                checar(
                    "${" in valor or not valor or chave.startswith("IG_STATE"),
                    f"mcp.servers.{nome}.env.{chave}: placeholder, nao valor literal",
                )

    # --- agentes -----------------------------------------------------------
    entradas = (cfg.get("agents") or {}).get("entries") or {}
    checar(bool(entradas), "declara ao menos um agente em agents.entries")

    skills_existentes = (
        {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()} if SKILLS_DIR.is_dir() else set()
    )

    for aid, ag in entradas.items():
        ws, _ = expandir(ag.get("workspace") or "")
        checar(Path(ws).is_dir(), f"agents.entries.{aid}: workspace existe ({Path(ws).name})")

        skills = ag.get("skills") or []
        checar(bool(skills), f"agents.entries.{aid}: declara allowlist de skills")
        if skills:
            faltando = set(skills) - skills_existentes
            checar(
                not faltando,
                f"agents.entries.{aid}: toda skill da allowlist existe ({sorted(faltando)} ausentes)"
                if faltando
                else f"agents.entries.{aid}: as {len(skills)} skills da allowlist existem no workspace",
            )
            checar(
                len(skills) == len(set(skills)),
                f"agents.entries.{aid}: allowlist sem repeticao",
            )

        atraso = (ag.get("humanDelay") or {}).get("mode")
        if atraso is not None:
            checar(
                atraso in {"off", "natural", "custom"},
                f"agents.entries.{aid}: humanDelay.mode valido ({atraso})",
            )

        # Não pinar modelo é decisão do port (o dono escolhe, como no Hermes).
        checar(
            "model" not in ag,
            f"agents.entries.{aid}: sem pin de modelo (decisão do port)",
        )

    # --- hooks: não pode vir armado por descuido ---------------------------
    hooks = cfg.get("hooks")
    checar(
        hooks is None or hooks.get("enabled") is not True,
        "`hooks` ausente ou nao armado (endpoint de entrada pertence a etapa 5)",
    )

    print("  placeholders nao resolvidos pelo verificador (esperado: credenciais)")
    for m in sorted(set(re.findall(r"\$\{([A-Z0-9_]+)\}", bruto))):
        if m not in RESOLVIVEIS:
            print(f"    ${{{m}}}")

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
