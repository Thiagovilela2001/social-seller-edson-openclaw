#!/usr/bin/env python3
"""Testes de observabilidade do MCP — traces JSONL e execution_id.

Executa junto com os demais: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

# Carrega o modulo com variaveis de ambiente ja setadas.
os.environ["IG_STATE_DIR"] = ""  # força fallback para state/ dentro do repo.


class TestTraceFunction(unittest.TestCase):
    """Testa a funcao _trace do MCP."""

    tmp: tempfile.TemporaryDirectory

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        # Aponta IG_STATE_DIR para o tmp e recarrega o modulo.
        os.environ["IG_STATE_DIR"] = str(base)
        import importlib
        import instagram_seller_mcp as mcp
        importlib.reload(mcp)

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.pop("IG_STATE_DIR", None)
        cls.tmp.cleanup()

    def test_trace_escreve_jsonl_valido(self) -> None:
        """Verifica que _trace() escreve JSONL com todos os campos obrigatorios."""
        import instagram_seller_mcp as mcp

        base = Path(os.environ["IG_STATE_DIR"])
        trace_file = base / "mcp_traces.jsonl"

        # Limpa fixture.
        trace_file.unlink(missing_ok=True)

        mcp._trace(
            execution_id="abc123",
            tool="ig_send_dm",
            igsid="u123",
            acao="informar_preco",
            resultado="sucesso",
            bloqueio=None,
        )
        mcp._trace(
            execution_id="abc123",
            tool="ig_send_dm",
            igsid="u123",
            acao="informar_preco",
            resultado="bloqueado",
            bloqueio="[RN-009] acao A0",
        )

        self.assertTrue(trace_file.exists())
        linhas = trace_file.read_text().strip().splitlines()
        self.assertEqual(len(linhas), 2)

        for linha in linhas:
            dados = json.loads(linha)
            self.assertIn("at", dados)
            self.assertEqual(dados["execution_id"], "abc123")
            self.assertEqual(dados["tool"], "ig_send_dm")
            self.assertEqual(dados["igsid"], "u123")
            self.assertEqual(dados["acao"], "informar_preco")
            self.assertIn("resultado", dados)

    def test_trace_nao_vaza_texto_livre(self) -> None:
        """O JSONL nao deve conter campos de texto do cliente alem de acao/tool."""
        import instagram_seller_mcp as mcp

        base = Path(os.environ["IG_STATE_DIR"])
        trace_file = base / "mcp_traces.jsonl"
        trace_file.unlink(missing_ok=True)

        # Nao passa 'text' nem 'mensagem' para _trace — esses campos nao existem.
        mcp._trace(
            execution_id="x1",
            tool="ig_send_dm",
            igsid="u1",
            acao="responder_duvida_rag",
            resultado="sucesso",
            bloqueio=None,
        )

        dados = json.loads(trace_file.read_text())
        self.assertNotIn("text", dados)
        self.assertNotIn("mensagem", dados)
        self.assertNotIn("preco", dados)


class TestExecSendDmTrace(unittest.TestCase):
    """Testa que exec_send_dm() chama _trace() nos casos corretos."""

    tmp: tempfile.TemporaryDirectory

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        os.environ["IG_STATE_DIR"] = str(base)
        import importlib
        import instagram_seller_mcp as mcp
        importlib.reload(mcp)

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.pop("IG_STATE_DIR", None)
        cls.tmp.cleanup()

    def test_exec_send_dm_log_trace_em_bloqueio(self) -> None:
        """PolicyBlock gera trace com resultado bloqueado."""
        import instagram_seller_mcp as mcp
        from instagram_api import PolicyBlock

        base = Path(os.environ["IG_STATE_DIR"])
        trace_file = base / "mcp_traces.jsonl"
        trace_file.unlink(missing_ok=True)

        # Mock send_dm para levantar PolicyBlock.
        import instagram_seller_mcp as _mcp_module
        original = _mcp_module.send_dm

        def mock_send_dm(igsid, text, **kw):
            raise PolicyBlock("[RN-009] acao A0: humano sempre")

        _mcp_module.send_dm = mock_send_dm
        try:
            is_error, payload = mcp.exec_send_dm({
                "igsid": "u1",
                "text": "quanto custa?",
                "acao": "desconto",
                "proativo": False,
                "execution_id": "exec-block-1",
            })
        finally:
            _mcp_module.send_dm = original

        self.assertTrue(is_error)
        self.assertEqual(payload["error"], "blocked_by_policy")

        # Verifica trace.
        self.assertTrue(trace_file.exists())
        dados = json.loads(trace_file.read_text())
        self.assertEqual(dados["resultado"], "bloqueado")
        self.assertEqual(dados["execution_id"], "exec-block-1")
        self.assertEqual(dados["acao"], "desconto")

    def test_exec_send_dm_execution_id_vai_para_traces(self) -> None:
        """execution_id e propagado corretamente no trace."""
        import instagram_seller_mcp as mcp

        base = Path(os.environ["IG_STATE_DIR"])
        trace_file = base / "mcp_traces.jsonl"
        trace_file.unlink(missing_ok=True)

        # Mock send_dm para sucesso.
        import instagram_seller_mcp as _mcp_module
        original = _mcp_module.send_dm

        def mock_ok(igsid, text, **kw):
            return {"message_id": "mid-1"}

        _mcp_module.send_dm = mock_ok
        try:
            mcp.exec_send_dm({
                "igsid": "u1",
                "text": "oi",
                "acao": "agradecimento",
                "proativo": False,
                "execution_id": "exec-ok-1",
            })
        finally:
            _mcp_module.send_dm = original

        dados = json.loads(trace_file.read_text())
        self.assertEqual(dados["execution_id"], "exec-ok-1")
        self.assertEqual(dados["resultado"], "sucesso")


if __name__ == "__main__":
    unittest.main(verbosity=2)
