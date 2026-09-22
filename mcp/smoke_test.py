#!/usr/bin/env python3
"""Smoke test do servidor MCP — prova o protocolo E o gate, sem rede.

O que este teste prova (e por que cada um importa):

  1. O servidor sobe e responde `initialize` / `tools/list` — o adaptador carrega
     o motor e publica as três tools.
  2. `ig_send_dm` SEM `acao` é recusado — a obrigatoriedade do achado F04
     sobreviveu ao port (omitir não é autorização).
  3. `ig_private_reply` COM link é recusado — a trava de texto puro sobreviveu.
  4. Com o KILL SWITCH ligado, QUALQUER envio é recusado com `blocked_by_policy`
     — a parada de emergência é imposta no caminho da chamada, não no prompt.

Nada aqui toca a rede: os cenários 2–4 são recusados ANTES de qualquer HTTP.

Uso:  python mcp/smoke_test.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp" / "instagram_seller_mcp.py"
KILL_SWITCH = ROOT / "state" / "ig-kill-switch"

falhas: list[str] = []
ok: list[str] = []


def checar(cond: bool, descricao: str) -> None:
    (ok if cond else falhas).append(descricao)


class Servidor:
    def __init__(self) -> None:
        # PYTHONIOENCODING: o servidor também força UTF-8 internamente
        # (_configurar_stdio); isto aqui é defesa em profundidade.
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        self.p = subprocess.Popen(
            [sys.executable, str(SERVER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        self._id = 0

    def chamar(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        req = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            req["params"] = params
        self.p.stdin.write(json.dumps(req) + "\n")
        self.p.stdin.flush()
        linha = self.p.stdout.readline()
        if not linha:
            raise RuntimeError("servidor fechou stdout sem responder")
        return json.loads(linha)

    def notificar(self, method: str) -> None:
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.p.stdin.flush()

    def fechar(self) -> None:
        self.p.stdin.close()
        self.p.wait(timeout=10)


def texto(resp: dict) -> tuple[bool, dict]:
    """Extrai (isError, payload) de uma resposta tools/call."""
    res = resp.get("result") or {}
    conteudo = (res.get("content") or [{}])[0]
    return bool(res.get("isError")), json.loads(conteudo.get("text") or "{}")


def main() -> int:
    if KILL_SWITCH.exists():
        KILL_SWITCH.unlink()  # estado limpo para o teste

    srv = Servidor()
    try:
        # 1. protocolo
        init = srv.chamar("initialize", {"protocolVersion": "2024-11-05"})
        checar(
            init.get("result", {}).get("serverInfo", {}).get("name") == "instagram-seller",
            "initialize responde com serverInfo",
        )
        srv.notificar("notifications/initialized")

        lista = srv.chamar("tools/list")
        nomes = {t["name"] for t in lista.get("result", {}).get("tools", [])}
        checar(
            nomes == {"ig_send_dm", "ig_private_reply", "ig_reply_comment"},
            f"tools/list publica as 3 tools (veio: {sorted(nomes)})",
        )
        esquema = [
            t for t in lista.get("result", {}).get("tools", []) if t["name"] == "ig_send_dm"
        ][0]
        checar(
            set(esquema["inputSchema"]["required"]) == {"igsid", "text", "proativo", "acao"},
            "schema de ig_send_dm exige igsid/text/proativo/acao",
        )
        checar(
            "enum" in esquema["inputSchema"]["properties"]["acao"],
            "acao tem vocabulário fechado (enum do motor)",
        )

        # 2. F04 — omitir acao não é autorização
        ie, pl = texto(
            srv.chamar(
                "tools/call",
                {
                    "name": "ig_send_dm",
                    "arguments": {"igsid": "u1", "text": "oi", "proativo": False},
                },
            )
        )
        checar(ie and "acao" in pl.get("message", ""), "ig_send_dm sem acao e recusado (F04)")

        # 3. private reply não aceita link
        ie, pl = texto(
            srv.chamar(
                "tools/call",
                {
                    "name": "ig_private_reply",
                    "arguments": {
                        "comment_id": "c1",
                        "text": "olha aqui https://exemplo.com",
                        "acao": "private_reply_palavra_chave",
                    },
                },
            )
        )
        checar(
            ie and "texto puro" in pl.get("message", ""),
            "ig_private_reply com link e recusado",
        )

        # 4. kill switch — parada de emergência
        KILL_SWITCH.write_text("", encoding="utf-8")
        ie, pl = texto(
            srv.chamar(
                "tools/call",
                {
                    "name": "ig_send_dm",
                    "arguments": {
                        "igsid": "u1",
                        "text": "oi",
                        "proativo": False,
                        "acao": "responder_duvida_rag",
                    },
                },
            )
        )
        checar(
            ie
            and pl.get("error") == "blocked_by_policy"
            and "RN-001" in pl.get("message", ""),
            "kill switch bloqueia o envio com o carimbo [RN-001]",
        )
    finally:
        srv.fechar()
        if KILL_SWITCH.exists():
            KILL_SWITCH.unlink()

    print("\n=== smoke test do servidor MCP ===")
    for linha in ok:
        print(f"  PASS  {linha}")
    for linha in falhas:
        print(f"  FAIL  {linha}")
    print(f"\n{len(ok)} passaram, {len(falhas)} falharam")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
