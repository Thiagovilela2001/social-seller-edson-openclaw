#!/usr/bin/env python3
"""Verificador das automations.

Confere os arquivos de `automations/` contra a forma que a ferramenta de
automations do OpenClaw aceita (`schedule`, `payload`, `sessionTarget`,
`delivery`, `enabled`). O que ele pega:

  - JSON invalido, nome repetido, chave desconhecida
  - expressao cron malformada (5 campos) ou `tz` ausente/invalida
  - payload sem os campos obrigatorios do seu tipo
  - script referenciado que nao existe no disco  (falha silenciosa: o job fica
    agendado e nunca produz nada)
  - job que NAO nasceu desligado  (a licao do Hermes: cron de distribution
    instalado ligado e falha silenciosa)
  - segredo literal, vocabulario do runtime antigo

LIMITE DECLARADO: valida FORMA. Nao prova que o agendador aceita o job, nem que
o efeito real acontece. Isso exige um Gateway alvo.

Uso:  python tools/check_automations.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "automations"

KINDS_SCHEDULE = {"at", "every", "cron", "stream"}
KINDS_PAYLOAD = {"systemEvent", "agentTurn", "script", "command"}
MODES_DELIVERY = {"announce", "webhook", "none"}
TZ_ESPERADO = "America/Sao_Paulo"
RESOLVIVEIS = {"SOCIAL_SELLER_REPO": str(RAIZ)}

falhas: list[str] = []
ok: list[str] = []


def checar(cond: bool, descricao: str) -> None:
    (ok if cond else falhas).append(descricao)


def expandir(valor: str) -> str:
    return re.sub(
        r"\$\{([A-Z0-9_]+)\}", lambda m: RESOLVIVEIS.get(m.group(1), m.group(0)), valor
    )


def campo_cron_ok(campo: str) -> bool:
    if campo == "*":
        return True
    if not re.fullmatch(r"[0-9*/,\-]+", campo):
        return False
    return all(re.fullmatch(r"(\*|\d+)(-\d+)?(/\d+)?", p) for p in campo.split(","))


def tz_valida(tz: str) -> bool | None:
    """True/False se der para julgar; None quando falta tzdata no host."""
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(tz)
        return True
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    print("=== verificador das automations ===\n")

    arquivos = sorted(PASTA.glob("*.json"))
    checar(bool(arquivos), f"{len(arquivos)} automation(oes) encontradas")

    nomes: list[str] = []

    for arq in arquivos:
        try:
            j = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            checar(False, f"{arq.name}: JSON invalido ({e})")
            continue

        rotulo = j.get("name") or arq.stem
        nomes.append(rotulo)

        # --- o job precisa nascer DESLIGADO -----------------------------------
        checar(
            j.get("enabled") is False,
            f"{rotulo}: nasce desligado (enabled: false)",
        )
        checar(bool(j.get("description")), f"{rotulo}: tem `description` (motivo do pause)")

        # --- schedule ---------------------------------------------------------
        sch = j.get("schedule") or {}
        checar(
            sch.get("kind") in KINDS_SCHEDULE,
            f"{rotulo}: schedule.kind valido ({sch.get('kind')})",
        )
        if sch.get("kind") == "cron":
            expr = (sch.get("expr") or "").strip()
            campos = expr.split()
            checar(len(campos) == 5, f"{rotulo}: cron com 5 campos ({len(campos)})")
            checar(
                all(campo_cron_ok(c) for c in campos),
                f"{rotulo}: cron com sintaxe valida ({expr})",
            )
            checar(
                sch.get("tz") == TZ_ESPERADO,
                f"{rotulo}: fuso explicito {TZ_ESPERADO} (nunca hora do host)",
            )
            if tz_valida(sch.get("tz") or "") is None:
                print(f"    AVISO: tzdata ausente no host — nao foi possivel validar {sch.get('tz')}")

        # --- sessionTarget ----------------------------------------------------
        st = j.get("sessionTarget")
        checar(
            st in {"main", "isolated", "current"} or str(st).startswith("session:"),
            f"{rotulo}: sessionTarget valido ({st})",
        )

        # --- payload ----------------------------------------------------------
        pl = j.get("payload") or {}
        kind = pl.get("kind")
        checar(kind in KINDS_PAYLOAD, f"{rotulo}: payload.kind valido ({kind})")

        if kind == "agentTurn":
            msg = (pl.get("message") or "").strip()
            checar(bool(msg), f"{rotulo}: agentTurn com `message`")
            checar(
                "portugues do Brasil" in msg or "português do Brasil" in msg,
                f"{rotulo}: mensagem declara o idioma (automacao NAO infere idioma)",
            )
        elif kind == "command":
            argv = pl.get("argv") or []
            checar(bool(argv), f"{rotulo}: command com `argv`")
            for item in argv:
                alvo = expandir(str(item))
                if "/" in alvo or alvo.endswith(".py"):
                    checar(
                        Path(alvo).is_file(),
                        f"{rotulo}: arquivo do argv existe ({Path(alvo).name})",
                    )
            # Placeholder em `argv` NAO e defeito: o artefato precisa ser portavel, e
            # o payload 'command' executa argv SEM shell — entao `${VAR}` nao expande.
            # A substituicao e passo de instalacao, nao de autoria. O risco residual
            # (operador esquecer) e RUIDOSO: exit != 0 vira run 'error' e alerta de
            # falha apos 2 execucoes. Por isso e aviso, nao falha.
            pendentes = [str(a) for a in argv if "${" in str(a)]
            if pendentes:
                print(
                    f"    AVISO: {rotulo} — substituir placeholder por caminho absoluto "
                    f"antes de habilitar (argv nao passa por shell): {pendentes}"
                )
        elif kind == "script":
            alvo = expandir(str(pl.get("script") or ""))
            checar(bool(alvo), f"{rotulo}: script declarado")
            if alvo:
                checar(Path(alvo).is_file(), f"{rotulo}: arquivo do script existe")
        elif kind == "systemEvent":
            checar(bool((pl.get("text") or "").strip()), f"{rotulo}: systemEvent com `text`")

        # --- delivery ---------------------------------------------------------
        dl = j.get("delivery") or {}
        checar(
            dl.get("mode") in MODES_DELIVERY,
            f"{rotulo}: delivery.mode valido ({dl.get('mode')})",
        )
        if dl.get("mode") == "announce":
            checar(bool(dl.get("channel")), f"{rotulo}: announce declara `channel`")
            checar(bool(dl.get("to")), f"{rotulo}: announce declara `to`")

        # --- higiene ----------------------------------------------------------
        bruto = arq.read_text(encoding="utf-8")
        checar(
            not re.search(r"hermes", bruto, re.IGNORECASE),
            f"{rotulo}: sem vocabulario do runtime antigo",
        )
        checar(
            re.search(
                r"(gho_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|EAA[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})",
                bruto,
            )
            is None,
            f"{rotulo}: nenhum segredo literal",
        )

    checar(len(nomes) == len(set(nomes)), f"nomes de automation unicos ({len(nomes)})")

    print("\n=== resultado ===")
    for linha in ok:
        print(f"  PASS  {linha}")
    for linha in falhas:
        print(f"  FAIL  {linha}")
    print(f"\n{len(ok)} passaram, {len(falhas)} falharam")
    print("\nAVISO: valida FORMA. Nao prova que o agendador aceita o job.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
