#!/usr/bin/env python3
"""Testes do ingress (sidecar) — HTTP em loopback, sem rede externa e sem credencial.

O que esta suíte prova, e por que cada bloco importa:

  1. ASSINATURA  — sem assinatura válida da Meta, o evento é recusado ANTES de
     qualquer processamento. "Autenticidade antes de conteúdo."
  2. HANDSHAKE   — o GET de verificação da Meta é respondido (é o que dispensa o
     proxy de borda do Hermes), e verify token errado não passa.
  3. PONTE DO INTAKE — o intake roda como SUBPROCESSO, com o contrato real
     (stdin -> stdout, `[SILENT]` descarta) e falha fechado quando ele quebra.
  4. ORDENAÇÃO   — a coalescência serializa por remetente sem perder evento nem
     rodar dois turnos da mesma pessoa em paralelo.
  5. TURNO       — o corpo enviado ao `/hooks/agent` tem as decisões declaradas
     (`deliver: false`, `sessionMode: isolated`).

O dispatch para o Gateway é apontado para uma porta fechada de propósito: o que
interessa aqui é o comportamento do ingress, não o Gateway.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "ingress"))

import sidecar  # noqa: E402


def payload_comentario(texto: str = "quanto custa?", igsid: str = "55", cid: str = "c1") -> dict:
    return {
        "object": "instagram",
        "entry": [
            {
                "id": "1",
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "from": {"id": igsid, "username": "cliente"},
                            "media": {"id": "m1"},
                            "id": cid,
                            "text": texto,
                        },
                    }
                ],
            }
        ],
    }


def assinar(corpo: bytes, segredo: str) -> str:
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


class AmbienteIngress(unittest.TestCase):
    """Base que monta um ambiente hermético: estado e logs em pasta temporária."""

    tmp: tempfile.TemporaryDirectory
    originais: dict[str, str | None] = {}
    CFG = {
        "META_APP_SECRET": "segredo-de-teste",
        "META_VERIFY_TOKEN": "verify-de-teste",
        "OPENCLAW_HOOK_TOKEN": "hook-de-teste",
        # Porta 1 é fechada: o dispatch falha e o Coalescer engole (comportamento real).
        "OPENCLAW_GATEWAY_URL": "http://127.0.0.1:1",
        "OPENCLAW_HOOK_AGENT_ID": "social-seller",
        "IG_WEBHOOK_HOST": "127.0.0.1",
        "IG_WEBHOOK_PORT": "0",
        "IG_COALESCE_PAUSA_SEGUNDOS": "0",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.CFG = {
            **cls.CFG,
            "IG_STATE_DIR": str(base / "state"),
            "IG_STATE_DB": str(base / "state" / "estado.db"),
            "IG_LOG_DIR": str(base / "logs"),
        }
        for chave, valor in cls.CFG.items():
            cls.originais[chave] = os.environ.get(chave)
            os.environ[chave] = valor

    @classmethod
    def tearDownClass(cls) -> None:
        for chave, valor in cls.originais.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor
        cls.tmp.cleanup()

    def cfg(self) -> sidecar.Config:
        return sidecar.Config()


class TestAssinatura(AmbienteIngress):
    def test_assinatura_correta_passa(self) -> None:
        corpo = b'{"a":1}'
        self.assertTrue(sidecar.assinatura_valida(corpo, assinar(corpo, "s3"), "s3"))

    def test_sem_cabecalho_recusa(self) -> None:
        self.assertFalse(sidecar.assinatura_valida(b"{}", None, "s3"))

    def test_prefixo_errado_recusa(self) -> None:
        corpo = b"{}"
        cabecalho = assinar(corpo, "s3").replace("sha256=", "sha1=")
        self.assertFalse(sidecar.assinatura_valida(corpo, cabecalho, "s3"))

    def test_segredo_vazio_recusa(self) -> None:
        corpo = b"{}"
        # Sem segredo configurado, NADA passa — fail closed, não fail open.
        self.assertFalse(sidecar.assinatura_valida(corpo, assinar(corpo, "s3"), ""))

    def test_corpo_alterado_recusa(self) -> None:
        cabecalho = assinar(b'{"a":1}', "s3")
        self.assertFalse(sidecar.assinatura_valida(b'{"a":2}', cabecalho, "s3"))


class TestChaveDeCoalescencia(AmbienteIngress):
    def test_usa_igsid(self) -> None:
        e = {"evento": {"igsid": "55", "comment_id": "c1"}}
        self.assertEqual(sidecar.chave_de_coalescencia(e), "55")

    def test_cai_para_comment_id(self) -> None:
        e = {"evento": {"igsid": "", "comment_id": "c1"}}
        self.assertEqual(sidecar.chave_de_coalescencia(e), "c1")

    def test_sem_identidade_nao_agrupa_tudo_em_branco(self) -> None:
        self.assertEqual(sidecar.chave_de_coalescencia({}), "desconhecido")


class TestTurno(AmbienteIngress):
    def test_decisoes_do_turno(self) -> None:
        cfg = self.cfg()
        enriquecido = {
            "briefing": "texto",
            "diretiva": "responder",
            "evento": {"tipo_evento": "comentario"},
            "auditoria": {"event_id": "ev1"},
        }
        turno = sidecar.montar_turno(enriquecido, cfg)
        self.assertEqual(turno["agentId"], cfg.agent_id)
        # O envio no Instagram é feito pelas tools do MCP, não pelo anúncio do runner.
        self.assertFalse(turno["deliver"])
        self.assertEqual(turno["sessionMode"], "isolated")
        # O payload tem de ir DENTRO da mensagem: é o que o agente lê.
        self.assertIn('"diretiva": "responder"', turno["message"])
        self.assertIn("NO_REPLY", turno["message"])


class TestOrdenacaoPorRemetente(AmbienteIngress):
    def test_serializa_sem_perder_evento(self) -> None:
        entregues: list[str] = []
        simultaneos = {"max": 0, "agora": 0}
        trava = threading.Lock()

        def fake(_chave, item):
            with trava:
                simultaneos["agora"] += 1
                simultaneos["max"] = max(simultaneos["max"], simultaneos["agora"])
            entregues.append(item)
            with trava:
                simultaneos["agora"] -= 1

        c = sidecar.Coalescer(fake, paralelismo=4, pausa=lambda: None)
        for i in range(3):
            c.adicionar("mesma-pessoa", f"ev{i}")

        limite = 5
        while c.ativos() and limite:
            import time as _t

            _t.sleep(0.05)
            limite -= 1

        self.assertEqual(entregues, ["ev0", "ev1", "ev2"], "ordem preservada, nada perdido")
        self.assertEqual(simultaneos["max"], 1, "nunca dois turnos da mesma pessoa em paralelo")

    def test_remetentes_diferentes_nao_se_bloqueiam(self) -> None:
        c = sidecar.Coalescer(lambda *_: None, paralelismo=4, pausa=lambda: None)
        self.assertEqual(c.adicionar("a", 1), "despachado")
        self.assertEqual(c.adicionar("b", 2), "despachado")


class TestPonteDoIntake(AmbienteIngress):
    def test_evento_normal_vira_payload_enriquecido(self) -> None:
        cfg = self.cfg()
        corpo = json.dumps(payload_comentario()).encode()
        saida, motivo = sidecar.rodar_intake(cfg, corpo)
        self.assertNotEqual(saida, sidecar.FALHA_INTAKE, motivo)
        self.assertNotEqual(saida, sidecar.SILENCIO, motivo)
        dados = json.loads(saida)
        self.assertEqual(dados["diretiva"], "responder")
        self.assertIn("briefing", dados)
        self.assertIn("estado", dados)

    def test_eco_e_descartado(self) -> None:
        """Comentário da própria conta: o intake devolve [SILENT] e nada é despachado."""
        cfg = self.cfg()
        p = payload_comentario()
        p["entry"][0]["changes"][0]["value"]["from"]["id"] = p["entry"][0]["id"]
        saida, _ = sidecar.rodar_intake(cfg, json.dumps(p).encode())
        self.assertEqual(saida, sidecar.SILENCIO)

    def test_payload_ilegivel_falha_fechado(self) -> None:
        cfg = self.cfg()
        saida, _ = sidecar.rodar_intake(cfg, b"isto nao e json")
        self.assertEqual(saida, sidecar.SILENCIO)

    def test_intake_ausente_falha_fechado(self) -> None:
        cfg = self.cfg()
        cfg.intake = Path(self.tmp.name) / "nao-existe.py"
        saida, motivo = sidecar.rodar_intake(cfg, b"{}")
        self.assertEqual(saida, sidecar.FALHA_INTAKE)
        self.assertIn("ausente", motivo)


class TestHTTP(AmbienteIngress):
    servidor: sidecar.ThreadingHTTPServer
    thread: threading.Thread
    base: str

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.servidor = sidecar.construir_servidor(sidecar.Config())
        porta = cls.servidor.server_address[1]
        cls.base = f"http://127.0.0.1:{porta}"
        cls.thread = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.servidor.shutdown()
        cls.servidor.server_close()
        super().tearDownClass()

    def _get(self, caminho: str):
        try:
            with urllib.request.urlopen(self.base + caminho, timeout=5) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def _post(self, corpo: bytes, assinatura: str | None):
        req = urllib.request.Request(
            self.base + "/webhooks/instagram", data=corpo, method="POST"
        )
        if assinatura:
            req.add_header("X-Hub-Signature-256", assinatura)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    def test_health(self) -> None:
        codigo, corpo = self._get("/health")
        self.assertEqual(codigo, 200)
        self.assertEqual(json.loads(corpo)["status"], "ok")

    def test_handshake_da_meta_devolve_o_desafio(self) -> None:
        codigo, corpo = self._get(
            "/webhooks/instagram?hub.mode=subscribe&hub.verify_token=verify-de-teste&hub.challenge=12345"
        )
        self.assertEqual(codigo, 200)
        self.assertEqual(corpo, "12345")

    def test_handshake_com_token_errado_recusa(self) -> None:
        codigo, _ = self._get(
            "/webhooks/instagram?hub.mode=subscribe&hub.verify_token=errado&hub.challenge=12345"
        )
        self.assertEqual(codigo, 403)

    def test_post_sem_assinatura_recusa(self) -> None:
        corpo = json.dumps(payload_comentario()).encode()
        codigo, dados = self._post(corpo, None)
        self.assertEqual(codigo, 401)

    def test_post_com_assinatura_errada_recusa(self) -> None:
        corpo = json.dumps(payload_comentario()).encode()
        codigo, _ = self._post(corpo, assinar(corpo, "segredo-errado"))
        self.assertEqual(codigo, 401)

    def test_post_assinado_com_payload_ilegivel_descarta(self) -> None:
        corpo = b"isto nao e json"
        codigo, dados = self._post(corpo, assinar(corpo, "segredo-de-teste"))
        self.assertEqual(codigo, 200)
        self.assertTrue(dados["descartado"])

    def test_post_assinado_de_evento_real_aceita(self) -> None:
        corpo = json.dumps(payload_comentario(igsid="99", cid="c99")).encode()
        codigo, dados = self._post(corpo, assinar(corpo, "segredo-de-teste"))
        self.assertEqual(codigo, 200)
        self.assertFalse(dados["descartado"])
        self.assertIn(dados["ordem"], {"despachado", "enfileirado"})


if __name__ == "__main__":
    unittest.main()
