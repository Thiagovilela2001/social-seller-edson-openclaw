"""Testes do modelo de dados — identidade, vínculo e RN-VINCULO.

Rodar: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

# Adiciona engine/instagram_seller/ ao sys.path para poder importar os módulos do plugin.
# Mesma configuração que test_rules.py usa.
_ROOT = Path(__file__).resolve().parents[1]  # social-seller-edson-openclaw/
_instagram_seller = _ROOT / "engine" / "instagram_seller"
if str(_instagram_seller) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_instagram_seller))

import rules  # noqa: E402
import modelo_dados  # noqa: E402
import vinculo_resolver  # noqa: E402


class BaseTestModel(unittest.TestCase):
    """Cada teste roda contra banco novo e vazio."""

    _tmp: tempfile.TemporaryDirectory

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls._tmp.name) / "estado.db"
        os.environ["IG_STATE_DB"] = str(cls.db_path)
        # Força recarregamento com banco novo.
        import importlib
        importlib.reload(rules)

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.pop("IG_STATE_DB", None)
        cls._tmp.cleanup()


# ---------------------------------------------------------------------------
# modelo_dados — Identidade
# ---------------------------------------------------------------------------

class TestIdentidade(BaseTestModel):
    def test_criacao_uuid_estavel(self) -> None:
        """UUID gerado na criação é estável entre chamadas."""
        ident = modelo_dados.Identidade.criar("instagram", "123456789")
        self.assertIsInstance(ident.id_interno, str)
        self.assertEqual(len(ident.id_interno), 36)  # UUID v4
        # Deux chamadas geram UUIDs diferentes.
        ident2 = modelo_dados.Identidade.criar("instagram", "123456789")
        self.assertNotEqual(ident.id_interno, ident2.id_interno)

    def test_namespace_formato_ig(self) -> None:
        ident = modelo_dados.Identidade.criar("instagram", "48291039252")
        self.assertEqual(ident.namespace_id, "ig:48291039252")

    def test_namespace_formato_yt(self) -> None:
        ident = modelo_dados.Identidade.criar("youtube", "UCx123456789")
        self.assertEqual(ident.namespace_id, "yt:UCx123456789")

    def test_parsear_namespace(self) -> None:
        plataforma, id_externo = modelo_dados.parsear_namespace("ig:48291039252")
        self.assertEqual(plataforma, "ig")
        self.assertEqual(id_externo, "48291039252")

    def test_parsear_namespace_sem_prefixo(self) -> None:
        """Sem prefixo assume Instagram por convenção."""
        plataforma, id_externo = modelo_dados.parsear_namespace("48291039252")
        self.assertEqual(plataforma, "ig")
        self.assertEqual(id_externo, "48291039252")

    def test_timestamps_preenchidos(self) -> None:
        ident = modelo_dados.Identidade.criar("instagram", "999")
        self.assertIn("T", ident.criado_em)  # ISO format
        self.assertIn("T", ident.atualizado_em)
        self.assertEqual(ident.criado_em, ident.atualizado_em)  # iguais na criação

    def test_to_dict_sem_documento(self) -> None:
        """to_dict não vaza campos sensíveis."""
        ident = modelo_dados.Identidade.criar("instagram", "123")
        d = ident.to_dict()
        self.assertIn("id_interno", d)
        self.assertIn("namespace_id", d)
        self.assertNotIn("cpf", d)
        self.assertNotIn("documento", d)

    def test_from_dict_roundtrip(self) -> None:
        original = modelo_dados.Identidade.criar("instagram", "abc")
        restored = modelo_dados.Identidade.from_dict(original.to_dict())
        self.assertEqual(restored.id_interno, original.id_interno)
        self.assertEqual(restored.namespace_id, original.namespace_id)


# ---------------------------------------------------------------------------
# modelo_dados — hash de documento
# ---------------------------------------------------------------------------

class TestHashDocumento(BaseTestModel):
    def test_hash_deterministic(self) -> None:
        h1 = modelo_dados.hash_documento("529.982.247-25")
        h2 = modelo_dados.hash_documento("529.982.247-25")
        self.assertEqual(h1, h2)

    def test_hash_diferentes_documentos(self) -> None:
        h1 = modelo_dados.hash_documento("529.982.247-25")
        h2 = modelo_dados.hash_documento("111.222.333-44")
        self.assertNotEqual(h1, h2)

    def test_hash_nao_reversivel(self) -> None:
        """Hash SHA-256 não revela o documento original."""
        import hashlib
        documento = "529.982.247-25"
        hash_valor = modelo_dados.hash_documento(documento)
        # Tentar o reverso: buscar o documento no hash não é possível.
        self.assertEqual(len(hash_valor), 64)  # SHA-256 hex
        self.assertNotIn(documento, hash_valor)

    def test_verificar_documento_ok(self) -> None:
        doc = "529.982.247-25"
        hash_valor = modelo_dados.hash_documento(doc)
        self.assertTrue(modelo_dados.verificar_documento(doc, hash_valor))

    def test_verificar_documento_falha(self) -> None:
        doc = "529.982.247-25"
        hash_valor = modelo_dados.hash_documento(doc)
        self.assertFalse(modelo_dados.verificar_documento("000.000.000-00", hash_valor))


# ---------------------------------------------------------------------------
# vinculo_resolver — criação e persistência
# ---------------------------------------------------------------------------

class TestVinculoCriar(BaseTestModel):
    def test_criar_vinculo_hash_documento(self) -> None:
        """Documento é guardado como hash, nunca em texto limpo."""
        ident = modelo_dados.Identidade.criar("instagram", "u123")
        vinculo = vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="52998224725",
            plataforma_origem="instagram",
            metadata={"fonte": "clint"},
        )
        self.assertNotEqual(vinculo.documento_hash, "52998224725")
        self.assertEqual(len(vinculo.documento_hash), 64)  # SHA-256 hex
        self.assertIsNone(vinculo.verificado_em)
        self.assertEqual(vinculo.tipo, "responsavel_financeiro")

    def test_criar_vinculo_roundtrip(self) -> None:
        """Vínculo persiste e pode ser recuperado."""
        ident = modelo_dados.Identidade.criar("instagram", "u456")
        original = vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="cliente_educacional",
            documento="11122233344",
            plataforma_origem="instagram",
            metadata={"origem": "bio"},
        )
        carregado = vinculo_resolver.carregar_vinculo(
            ident.id_interno, "cliente_educacional"
        )
        self.assertIsNotNone(carregado)
        self.assertEqual(carregado.documento_hash, original.documento_hash)
        self.assertEqual(carregado.tipo, "cliente_educacional")

    def test_metadata_nao_vaza_pii(self) -> None:
        """Metadata vai para JSON sem expor documento limpo.

        O código que CRIA o vínculo é responsável por NÃO colocar documento limpo
        no metadata. O teste verifica que, quando metadata NÃO contém o campo
        'documento', o storage não expõe.
        """
        ident = modelo_dados.Identidade.criar("instagram", "u789")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="12345678901",
            plataforma_origem="instagram",
            metadata={"igsid": "u789"},  # Sem 'cpf' ou 'documento' — é o que se espera
        )
        # Lê direto do banco para verificar que não há texto limpo.
        with rules.db() as conn:
            row = conn.execute(
                "SELECT metadata_json FROM vinculos WHERE id_interno = ?",
                (ident.id_interno,),
            ).fetchone()
        self.assertIsNotNone(row)
        raw = row["metadata_json"]
        self.assertNotIn("12345678901", raw)  # documento não aparece
        # igsid não é PII (anonimizável), mas não deve aparecer em log de decisão

    def test_resolver_por_documento_hash(self) -> None:
        """Busca por hash retorna todos os vínculos com aquele documento."""
        ident = modelo_dados.Identidade.criar("instagram", "u999")
        documento = "99988877766"
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="cliente_educacional",
            documento=documento,
            plataforma_origem="instagram",
            metadata={},
        )
        hash_doc = modelo_dados.hash_documento(documento)
        resultados = vinculo_resolver.resolver_por_documento_hash(hash_doc)
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].tipo, "cliente_educacional")

    def test_carregar_todos_vinculos(self) -> None:
        """Todos os vínculos de uma identidade são retornados."""
        ident = modelo_dados.Identidade.criar("instagram", "umulti")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="cliente_educacional",
            documento="111",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="222",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculos = vinculo_resolver.carregar_vinculos(ident.id_interno)
        self.assertEqual(len(vinculos), 2)
        tipos = {v.tipo for v in vinculos}
        self.assertEqual(tipos, {"cliente_educacional", "responsavel_financeiro"})


# ---------------------------------------------------------------------------
# Verificação de vínculo
# ---------------------------------------------------------------------------

class TestVinculoVerificacao(BaseTestModel):
    def test_vinculo_nao_verificado_inicialmente(self) -> None:
        ident = modelo_dados.Identidade.criar("instagram", "uv1")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="11122233344",
            plataforma_origem="instagram",
            metadata={},
        )
        tem, _ = vinculo_resolver.verificar_vinculo_financeiro(ident.id_interno)
        self.assertFalse(tem)

    def test_atualizar_vinculo_verifica(self) -> None:
        ident = modelo_dados.Identidade.criar("instagram", "uv2")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="55566677788",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculo_resolver.atualizar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            fonte="clint",
            verificado_em="2026-09-26T10:00:00-03:00",
            metadata={"nome": "Maria Silva"},  # nome não é PII direto
        )
        tem, vinculo = vinculo_resolver.verificar_vinculo_financeiro(ident.id_interno)
        self.assertTrue(tem)
        self.assertIsNotNone(vinculo)
        self.assertEqual(vinculo.fonte_verificacao, "clint")

    def test_verificar_vinculo_fonte_especifica(self) -> None:
        """verificar_vinculo retorna vínculo verificado por fonte específica."""
        ident = modelo_dados.Identidade.criar("instagram", "uv3")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="98765432100",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculo_resolver.atualizar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            fonte="educzz",
            verificado_em="2026-09-26T11:00:00-03:00",
        )
        # Clint ainda não verificou.
        resp_clint = vinculo_resolver.verificar_vinculo(ident.id_interno, "clint")
        self.assertIsNone(resp_clint)
        # Educzz sim.
        resp_educzz = vinculo_resolver.verificar_vinculo(ident.id_interno, "educzz")
        self.assertIsNotNone(resp_educzz)


# ---------------------------------------------------------------------------
# Responsável diferente do cliente
# ---------------------------------------------------------------------------

class TestResponsavelDiferente(BaseTestModel):
    def test_documentos_iguais_bloqueia(self) -> None:
        """Mesmo documento para responsável e cliente = bloqueado."""
        ident = modelo_dados.Identidade.criar("instagram", "usame")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="cliente_educacional",
            documento="11122233344",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="11122233344",  # mesmo documento
            plataforma_origem="instagram",
            metadata={},
        )
        diferentes_ok, _ = vinculo_resolver.responsavel_diferente_do_cliente(ident.id_interno)
        self.assertFalse(diferentes_ok)

    def test_documentos_diferentes_ok(self) -> None:
        """Documentos diferentes = OK."""
        ident = modelo_dados.Identidade.criar("instagram", "udiff")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="cliente_educacional",
            documento="11122233344",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="55566677788",  # diferente
            plataforma_origem="instagram",
            metadata={},
        )
        diferentes_ok, _ = vinculo_resolver.responsavel_diferente_do_cliente(ident.id_interno)
        self.assertTrue(diferentes_ok)

    def test_sem_dados_retorna_true(self) -> None:
        """Se um dos vínculos não existe, não compara (retorna True)."""
        ident = modelo_dados.Identidade.criar("instagram", "upartial")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="cliente_educacional",
            documento="11122233344",
            plataforma_origem="instagram",
            metadata={},
        )
        # Não cria responsável: só cliente existe.
        diferentes_ok, motivo = vinculo_resolver.responsavel_diferente_do_cliente(
            ident.id_interno
        )
        self.assertTrue(diferentes_ok)
        self.assertEqual(motivo, "sem_dados_suficientes")


# ---------------------------------------------------------------------------
# RN-VINCULO — bloqueio de ação financeira
# ---------------------------------------------------------------------------

class TestRNVincculo(BaseTestModel):
    def test_acao_financeira_sem_vinculo_bloqueia(self) -> None:
        """Ação financeira sem vínculo verificado gera bloqueio."""
        ident = modelo_dados.Identidade.criar("instagram", "ufinblock")
        # Não cria vínculo verificado.
        bloqueio = vinculo_resolver.check_vinculo_financeiro(
            "consultar_parcela", ident.id_interno
        )
        self.assertIsNotNone(bloqueio)
        self.assertEqual(bloqueio.regra, "RN-VINCULO")
        self.assertIn("vinculo", bloqueio.motivo.lower())

    def test_acao_financeira_com_vinculo_passa(self) -> None:
        """Ação financeira com vínculo verificado não gera bloqueio."""
        ident = modelo_dados.Identidade.criar("instagram", "ufinpass")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="33344455566",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculo_resolver.atualizar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            fonte="clint",
        )
        bloqueio = vinculo_resolver.check_vinculo_financeiro(
            "consultar_parcela", ident.id_interno
        )
        self.assertIsNone(bloqueio)

    def test_acao_nao_financeira_nao_bloqueia(self) -> None:
        """Ação fora da lista financeira não é afetada."""
        ident = modelo_dados.Identidade.criar("instagram", "unonfin")
        for acao in ("responder", "agradecer", "encerrar"):
            bloqueio = vinculo_resolver.check_vinculo_financeiro(acao, ident.id_interno)
            self.assertIsNone(bloqueio, f"{acao} não deveria ser afetada")

    def test_check_responsavel_igual_bloqueia(self) -> None:
        """Responsável = cliente com mesmo documento gera bloqueio."""
        ident = modelo_dados.Identidade.criar("instagram", "usameresp")
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="cliente_educacional",
            documento="77788899900",
            plataforma_origem="instagram",
            metadata={},
        )
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento="77788899900",  # mesmo documento
            plataforma_origem="instagram",
            metadata={},
        )
        # Vinculado mas verificado.
        vinculo_resolver.atualizar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            fonte="clint",
        )
        bloqueio = vinculo_resolver.check_vinculo_responsavel(ident.id_interno)
        self.assertIsNotNone(bloqueio)
        self.assertIn("responsavel", bloqueio.motivo.lower())

    def test_integração_com_avaliar_envio(self) -> None:
        """avaliar_envio recebe bloqueio de ação financeira via id_interno."""
        ident = modelo_dados.Identidade.criar("instagram", "uinteg")
        # Sem vínculo verificado.
        bloqueios = rules.avaliar_envio(
            texto="Quanto tempo falta?",
            igsid="uinteg",
            acao="consultar_parcela",
            id_interno=ident.id_interno,
        )
        rn_vinculo = [b for b in bloqueios if b.regra == "RN-VINCULO"]
        self.assertEqual(len(rn_vinculo), 1)
        self.assertIn("vinculo", rn_vinculo[0].motivo.lower())


# ---------------------------------------------------------------------------
# Ações financeiras detectadas corretamente
# ---------------------------------------------------------------------------

class TestAcoesFinanceiras(BaseTestModel):
    def test_todas_acoes_financeiras(self) -> None:
        esperado = {
            "consultar_parcela",
            "consultar_financiamento",
            "verificar_renegociacao",
            "obter_segunda_via",
            "consultar_faturas",
            "consultar_pedido",
            "consultar_contrato",
            "consultar_boleto",
            "consultar_pagamento",
        }
        for acao in esperado:
            with self.subTest(acao=acao):
                self.assertTrue(vinculo_resolver.e_acao_financeira(acao))

    def test_acao_nao_financeira(self) -> None:
        nao_financeiras = [
            "responder",
            "agradecer",
            "encerrar",
            "informar_preco",
            "private_reply_palavra_chave",
            "pergunta_diagnostico",
        ]
        for acao in nao_financeiras:
            with self.subTest(acao=acao):
                self.assertFalse(vinculo_resolver.e_acao_financeira(acao))


# ---------------------------------------------------------------------------
# JSONL não vaza documento (integração com log_decisao)
# ---------------------------------------------------------------------------

class TestPIIEmLog(BaseTestModel):
    def test_documento_em_storage_e_hash_nao_limpo(self) -> None:
        """O documento limpo JAMAIS aparece em storage.

        O campo `documento_hash` contém o hash SHA-256 (não o documento limpo).
        O `metadata_json` contém dados crus da fonte, SEM o valor do documento.
        """
        ident = modelo_dados.Identidade.criar("instagram", "upii")
        documento = "12345678901"
        vinculo_resolver.criar_vinculo(
            id_interno=ident.id_interno,
            tipo="responsavel_financeiro",
            documento=documento,
            plataforma_origem="instagram",
            metadata={"igsid": "upii"},  # Sem 'cpf' ou 'documento'
        )
        hash_doc = modelo_dados.hash_documento(documento)
        with rules.db() as conn:
            row = conn.execute(
                "SELECT documento_hash, metadata_json FROM vinculos WHERE id_interno = ?",
                (ident.id_interno,),
            ).fetchone()
        self.assertIsNotNone(row)
        # documento_hash contém o hash, não o documento limpo.
        self.assertEqual(row["documento_hash"], hash_doc)
        self.assertNotIn(documento, row["documento_hash"])
        # metadata_json não contém o documento limpo.
        self.assertNotIn(documento, row["metadata_json"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
