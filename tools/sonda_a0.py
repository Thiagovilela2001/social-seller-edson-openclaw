#!/usr/bin/env python3
"""Sonda A0 — rodada positivo/negativo das regras de escalada.

Por que existe: a suíte de testes prova o que os casos dela cobrem, e o caso do
F07 (parecer OpenClaw) mostrou que isso não basta — a calibragem passou na suíte
e ao mesmo tempo deixou de escalar "vou te processar". Teste escrito pelo mesmo
autor da mudança tende a cobrir só o que a mudança acertou.

Esta sonda roda o intake DE VERDADE (subprocesso, como o gateway roda), frase por
frase, e compara com o esperado. As baterias:

  A. F07 — falso positivo comercial do parecer × positivos originais
  B. variantes de ameaça (formas que a 1ª calibragem deixou passar)
  C. frases novas, escritas fora de qualquer briefing — pegam sobreajuste

Uso:  python tools/sonda_a0.py
Saída: uma linha por caso; termina com "TUDO COMO ESPERADO" ou "N CASO(S) FORA DO ESPERADO".
Não é teste unitário: é evidência de comportamento ponta a ponta.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tests"))
import test_intake as T  # noqa: E402  — reusa o helper de payload dos testes

SCRIPT = RAIZ / "ingress" / "instagram-intake.py"

BATERIAS: dict[str, list[tuple[str, str]]] = {
    "A — F07 (parecer OpenClaw)": [
        ("POSITIVO", "vou te processar"),
        ("POSITIVO", "vou processar voces, isso e roubo"),
        ("POSITIVO", "to pensando em processar a loja"),
        ("POSITIVO", "meu advogado vai entrar em contato"),
        ("POSITIVO", "vou no procon reclamar"),
        ("POSITIVO", "quero morrer"),
        ("POSITIVO", "estou com depressao profunda"),
        ("POSITIVO", "tenho ansiedade e tomo medicacao todo dia"),
        ("NEGATIVO", "qual o processo pra comprar?"),
        ("NEGATIVO", "como funciona o processo de entrega"),
        ("NEGATIVO", "minha psicologa me indicou esse livro"),
        ("NEGATIVO", "quanto custa o livro?"),
    ],
    "B — variantes de ameaca": [
        ("POSITIVO", "vamos processar voces"),
        ("POSITIVO", "vou entrar com um processo contra voces"),
        ("POSITIVO", "vou abrir um processo"),
        ("POSITIVO", "vou levar isso pro processo"),
        ("POSITIVO", "penso em processar voces"),
        ("POSITIVO", "isso vai dar processo"),
        ("POSITIVO", "vou te processar"),
        ("POSITIVO", "vou falar com meu advogado"),
        ("POSITIVO", "vou procurar meus direitos no procon"),
        ("NEGATIVO", "qual o processo pra comprar?"),
        ("NEGATIVO", "como funciona o processo de entrega"),
        ("NEGATIVO", "voces vao processar meu pedido quando?"),
        ("NEGATIVO", "preciso saber o processo de troca"),
        ("NEGATIVO", "qual o processo pra fazer o pedido"),
        ("NEGATIVO", "minha psicologa me indicou esse livro"),
    ],
    "C — frases novas (sobreajuste)": [
        ("POSITIVO", "to pensando em abrir um processo contra a loja"),
        ("POSITIVO", "vamos levar isso pra justica"),
        ("POSITIVO", "isso vai virar processo"),
        ("POSITIVO", "vou acionar a justica"),
        ("POSITIVO", "quero processar voces"),
        ("POSITIVO", "meu advogado ja ta sabendo disso"),
        ("NEGATIVO", "qual o passo a passo do processo de compra?"),
        ("NEGATIVO", "estou no processo de emagrecimento, esse livro ajuda?"),
        ("NEGATIVO", "meu processo seletivo ta chegando, queria um livro"),
        ("NEGATIVO", "como faco o processo para ser revendedor?"),
        ("NEGATIVO", "quanto custa o livro?"),
    ],
}


def diretiva_de(texto: str, *, cid: str, mid: str) -> tuple[bool, str, str]:
    """Roda o intake com um comentario e devolve (escalou, flags, diretiva)."""
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        (home / "logs").mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(T.comentario(texto, cid=cid, mid=mid)),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "HERMES_HOME": str(home), "IG_STATE_DB": str(home / "estado.db")},
        )
    try:
        d = json.loads((proc.stdout or "").strip())
    except ValueError:
        return False, "-", (proc.stdout or proc.stderr or "").strip()[:40]
    alerta = d.get("alerta_telegram") or {}
    return d.get("diretiva") == "escalar", alerta.get("flags", "-"), d.get("diretiva", "?")


def main() -> int:
    falhas = 0
    total = 0
    for bateria, casos in BATERIAS.items():
        print(f"--- {bateria} ---")
        for i, (esperado, texto) in enumerate(casos):
            total += 1
            # cid/mid unicos: o intake descarta reentrega (dedupe) e o caso viraria [SILENT]
            escalou, flags, diretiva = diretiva_de(texto, cid=f"{bateria[0]}{i}", mid=f"m{i}")
            correto = escalou if esperado == "POSITIVO" else not escalou
            falhas += 0 if correto else 1
            print(
                f'{"OK " if correto else "!!! "}[{esperado:<8}] escalou={str(escalou):<5} '
                f"flags={flags:<10} diretiva={diretiva:<10} {texto!r}"
            )
        print()
    if falhas:
        print(f"RESULTADO: {falhas} de {total} CASO(S) FORA DO ESPERADO")
        return 1
    print(f"RESULTADO: TUDO COMO ESPERADO ({total} casos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
