#!/usr/bin/env python3
"""Servidor MCP (stdio) do Social Seller — casca OpenClaw sobre o motor Hermes.

POR QUE MCP
    O OpenClaw não executa plugins Python. O motor de regras (rules.py +
    instagram_api.py) é stdlib puro, determinístico e já validado (205 testes).
    A decisão D1 do PORT-PLAN é NÃO reescrevê-lo. Este servidor expõe as três
    tools de envio por MCP; cada chamada atravessa `instagram_api._autorizar()`,
    que é a última barreira antes da rede.

O QUE ESTE ARQUIVO É
    ADAPTADOR. Nenhuma regra de negócio mora aqui. Se uma regra precisa mudar,
    ela muda em `engine/instagram_seller/rules.py`, e vale para os dois runtimes.
    O que está replicado do `__init__.py` do Hermes é só a OBRIGATORIEDADE dos
    campos (`acao`, `proativo`) — que é contrato de interface, não regra.

TRANSPORTE
    JSON-RPC 2.0, uma mensagem por linha, stdin/stdout (MCP stdio).
    stdout é o canal do protocolo: todo log/erro de diagnóstico vai para stderr.

ESTADO (D3 — sem editar o motor)
    `rules.py` resolve os caminhos por variável de ambiente:
        IG_STATE_DB     -> banco SQLite do motor
        IG_KILL_SWITCH  -> arquivo-flag da parada de emergência
    Quando não vêm do ambiente, apontamos para `<repo>/state/`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Caminhos e reapontamento de estado (nenhuma edição no motor)
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine" / "instagram_seller"
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("IG_STATE_DB", str(STATE / "instagram-seller.db"))
os.environ.setdefault("IG_KILL_SWITCH", str(STATE / "ig-kill-switch"))

sys.path.insert(0, str(ENGINE))

import rules  # noqa: E402  (precisa vir depois do sys.path)
import schemas  # noqa: E402
from instagram_api import (  # noqa: E402
    PolicyBlock,
    ResultadoIncerto,
    reply_comment_public,
    send_dm,
    send_private_reply,
)

# --------------------------------------------------------------------------
# Protocolo
# --------------------------------------------------------------------------

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "instagram-seller"
SERVER_VERSION = "0.5.0+openclaw.1"

# Códigos de motivo — mesmos do plugin Hermes, para não divergir a auditoria.
BLOCKED_BY_POLICY = "blocked_by_policy"
TOOL_ERROR = "tool_error"
RESULTADO_INCERTO = "resultado_incerto"

MENSAGEM_INCERTO = (
    "NÃO REPITA ESTE ENVIO. A chamada foi feita e não se sabe se chegou (RN-021). "
    "A pendência ficou registrada para conferência humana e trava nova tentativa no "
    "mesmo alvo — repetir no escuro pode duplicar a resposta ao cliente."
)


def _log(msg: str) -> None:
    """Diagnóstico vai para stderr — stdout é o canal do protocolo."""
    print(f"[{SERVER_NAME}] {msg}", file=sys.stderr, flush=True)


def _configurar_stdio() -> None:
    """Força UTF-8 no stdio.

    O protocolo MCP é JSON UTF-8, mas no Windows o Python abre stdout/stdin na
    codificação do locale (cp1252). Sem isto, uma mensagem com acento sai em
    cp1252 e o cliente que lê UTF-8 quebra — foi exatamente o primeiro erro do
    smoke test. Também fixa '\n' para não depender da tradução de newline.
    """
    for fluxo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------
# Obrigatoriedade de campos (achado F04) — contrato de interface
# --------------------------------------------------------------------------

def _acao_obrigatoria(args: dict) -> tuple[str, str]:
    acao = (args.get("acao") or "").strip()
    if not acao:
        return "", (
            "Parâmetro obrigatório ausente: acao. Omissão não é autorização (RN-009) — "
            "declare uma ação do vocabulário fechado."
        )
    return acao, ""


def _proatividade_obrigatoria(args: dict) -> tuple[bool, str]:
    if args.get("proativo") is None:
        return False, (
            "Parâmetro obrigatório ausente: proativo. Sem ele a abordagem não teria "
            "horário nem cota (RN-006/RN-007) — e o padrão silencioso esconderia isso."
        )
    return bool(args.get("proativo")), ""


# --------------------------------------------------------------------------
# Executores — mesma forma do __init__.py do Hermes
# --------------------------------------------------------------------------

def _erro(kind: str, message: str, **extra) -> tuple[bool, dict]:
    return True, {"success": False, "error": kind, "message": message, **extra}


def _ok(payload: dict) -> tuple[bool, dict]:
    return False, {"success": True, **payload}


def exec_send_dm(args: dict) -> tuple[bool, dict]:
    text = (args.get("text") or "").strip()
    if len(text) > 900:
        return _erro(
            BLOCKED_BY_POLICY,
            "Mensagem longa demais para DM. Quebre em até 2 mensagens de 3 linhas.",
        )
    proativo, erro = _proatividade_obrigatoria(args)
    if erro:
        return _erro(TOOL_ERROR, erro)
    acao, erro = _acao_obrigatoria(args)
    if erro:
        return _erro(TOOL_ERROR, erro)
    try:
        result = send_dm(args["igsid"], text, proativo=proativo, acao=acao)
    except PolicyBlock as e:
        return _erro(BLOCKED_BY_POLICY, str(e))
    except ResultadoIncerto as e:
        return _erro(RESULTADO_INCERTO, f"{MENSAGEM_INCERTO} Detalhe: {e}")
    except KeyError as e:
        return _erro(TOOL_ERROR, f"Parâmetro obrigatório ausente: {e}")
    except Exception as e:  # noqa: BLE001 — devolver erro é melhor que quebrar o turno
        return _erro(TOOL_ERROR, str(e))
    return _ok({"message_id": result.get("message_id"), "canal": "ig_dm"})


def exec_private_reply(args: dict) -> tuple[bool, dict]:
    text = (args.get("text") or "").strip()
    lowered = text.lower()
    if "http://" in lowered or "https://" in lowered:
        return _erro(
            BLOCKED_BY_POLICY,
            "Private reply vai SEMPRE em texto puro — sem link. "
            "O link vai na DM depois que a pessoa responder.",
        )
    acao, erro = _acao_obrigatoria(args)
    if erro:
        return _erro(TOOL_ERROR, erro)
    try:
        # A identidade NÃO vem daqui: send_private_reply resolve o autor pelo
        # comentário (RN-020).
        result = send_private_reply(args["comment_id"], text, acao=acao)
    except PolicyBlock as e:
        return _erro(BLOCKED_BY_POLICY, str(e))
    except ResultadoIncerto as e:
        return _erro(RESULTADO_INCERTO, f"{MENSAGEM_INCERTO} Detalhe: {e}")
    except KeyError as e:
        return _erro(TOOL_ERROR, f"Parâmetro obrigatório ausente: {e}")
    except Exception as e:  # noqa: BLE001
        return _erro(TOOL_ERROR, str(e))
    return _ok(
        {
            "message_id": result.get("message_id"),
            "canal": "ig_private_reply",
            "aviso": "Cota única deste comentário consumida.",
        }
    )


def exec_reply_comment(args: dict) -> tuple[bool, dict]:
    acao, erro = _acao_obrigatoria(args)
    if erro:
        return _erro(TOOL_ERROR, erro)
    try:
        result = reply_comment_public(
            args["comment_id"], (args.get("text") or "").strip(), acao=acao
        )
    except PolicyBlock as e:
        return _erro(BLOCKED_BY_POLICY, str(e))
    except ResultadoIncerto as e:
        return _erro(RESULTADO_INCERTO, f"{MENSAGEM_INCERTO} Detalhe: {e}")
    except KeyError as e:
        return _erro(TOOL_ERROR, f"Parâmetro obrigatório ausente: {e}")
    except Exception as e:  # noqa: BLE001
        return _erro(TOOL_ERROR, str(e))
    return _ok({"message_id": result.get("id"), "canal": "ig_comment_public"})


EXECUTORES = {
    "ig_send_dm": exec_send_dm,
    "ig_private_reply": exec_private_reply,
    "ig_reply_comment": exec_reply_comment,
}

# --------------------------------------------------------------------------
# Catálogo de tools — derivado de schemas.py (fonte única)
# --------------------------------------------------------------------------

def _tools() -> list[dict]:
    return [
        {
            "name": s["name"],
            "description": s["description"],
            "inputSchema": s["parameters"],
        }
        for s in (schemas.SEND_DM, schemas.PRIVATE_REPLY, schemas.REPLY_COMMENT)
    ]


# --------------------------------------------------------------------------
# Loop MCP (JSON-RPC 2.0 sobre stdio)
# --------------------------------------------------------------------------

def _respond(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _result(id_, result: dict) -> None:
    _respond({"jsonrpc": "2.0", "id": id_, "result": result})


def _error(id_, code: int, message: str) -> None:
    _respond({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def _handle(req: dict) -> None:
    method = req.get("method")
    id_ = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        _result(
            id_,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
        return

    if method in ("notifications/initialized", "initialized"):
        return  # notificação: sem resposta

    if method == "ping":
        _result(id_, {})
        return

    if method == "tools/list":
        _result(id_, {"tools": _tools()})
        return

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        executor = EXECUTORES.get(name)
        if executor is None:
            _error(id_, -32602, f"Tool desconhecida: {name}")
            return
        try:
            is_error, payload = executor(args)
        except Exception as e:  # noqa: BLE001 — nunca derrubar o servidor por um call
            _log(f"falha inesperada em {name}: {type(e).__name__}: {e}")
            is_error, payload = _erro(TOOL_ERROR, f"{type(e).__name__}: {e}")
        _result(
            id_,
            {
                "content": [
                    {"type": "text", "text": json.dumps(payload, ensure_ascii=False)}
                ],
                "isError": is_error,
            },
        )
        return

    _error(id_, -32601, f"Método não suportado: {method}")


def main() -> int:
    _configurar_stdio()
    _log(f"servidor no ar · rules {rules.RULES_VERSION} · engine {ENGINE}")
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            req = json.loads(linha)
        except json.JSONDecodeError as e:
            _log(f"mensagem ilegível: {e}")
            continue
        try:
            _handle(req)
        except Exception as e:  # noqa: BLE001
            _log(f"erro no handler: {type(e).__name__}: {e}")
            if isinstance(req, dict) and req.get("id") is not None:
                _error(req["id"], -32603, f"Erro interno: {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
