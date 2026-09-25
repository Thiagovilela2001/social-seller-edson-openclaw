#!/usr/bin/env python3
"""Testes da espinha dorsal de capacidades e do contrato de ferramentas (v3.0).

O que esta suíte protege, e por que cada bloco importa:

  1. ESCADA      — não existe "ação autorizada" sem "dado consultado". A ordem da
     §02 do mestre é invariante de estrutura, não comentário.
  2. REGISTRO    — toda capacidade que o motor declara aparece aqui (sem fonte de
     verdade paralela), e **nenhuma** está liberada hoje.
  3. RETORNO     — `sucesso` sem fonte, evidência e horário é recusado: afirmação
     exige prova. E falha não pode carregar valor (vazio ≠ ausência).
  4. CONTEXTO    — ferramenta sem entrada vinculada é recusada. O modelo não
     escolhe destinatário.
  5. DINHEIRO    — `float` é recusado. Ponto flutuante não é dinheiro (§08).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "engine" / "instagram_seller"))

import capacidades as cap  # noqa: E402
import integracoes  # noqa: E402


class TestEscada(unittest.TestCase):
    def test_escada_completa_libera(self) -> None:
        c = cap.Capacidade(familia="canal", descricao="x", niveis=frozenset(cap.NIVEIS))
        c.validar()
        self.assertTrue(c.liberada())

    def test_escada_com_buraco_e_recusada(self) -> None:
        # "acao_autorizada" sem "dado_consultado" é exatamente o atalho que a §02 proíbe.
        c = cap.Capacidade(
            familia="canal",
            descricao="x",
            niveis=frozenset({"api_existente", "acesso_concedido", "acao_autorizada"}),
        )
        with self.assertRaises(cap.ContratoInvalido):
            c.validar()

    def test_nivel_desconhecido_e_recusado(self) -> None:
        c = cap.Capacidade(familia="canal", descricao="x", niveis=frozenset({"inventado"}))
        with self.assertRaises(cap.ContratoInvalido):
            c.validar()

    def test_familia_desconhecida_e_recusada(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.Capacidade(familia="marketing", descricao="x").validar()

    def test_descricao_vazia_e_recusada(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.Capacidade(familia="canal", descricao="  ").validar()

    def test_sem_nivel_nao_libera(self) -> None:
        c = cap.Capacidade(familia="canal", descricao="x")
        self.assertFalse(c.liberada())
        self.assertEqual(c.estado()["proximo_nivel"], "api_existente")


class TestRegistro(unittest.TestCase):
    def test_toda_capacidade_do_motor_esta_no_registro(self) -> None:
        """Nada de fonte de verdade paralela: o motor declara, aqui é lido."""
        orfas = set(integracoes.CAPACIDADES) - set(cap.CAPACIDADES)
        self.assertEqual(orfas, set(), f"capacidades do motor fora do registro: {orfas}")

    def test_nenhuma_capacidade_esta_liberada(self) -> None:
        """Nada foi homologado. Se este teste falhar, alguém marcou produção sem prova."""
        liberadas = [n for n, c in cap.CAPACIDADES.items() if c.liberada()]
        self.assertEqual(liberadas, [])

    def test_teto_do_motor_e_ferramenta_implementada(self) -> None:
        """`True` no motor não vira 'dado consultado' nem 'ação autorizada'."""
        for nome, implementada in integracoes.CAPACIDADES.items():
            if implementada:
                self.assertNotIn(
                    "dado_consultado", cap.CAPACIDADES[nome].niveis, nome
                )

    def test_familias_cobertas(self) -> None:
        presentes = {c.familia for c in cap.CAPACIDADES.values()}
        self.assertTrue(presentes <= set(cap.FAMILIAS))
        # As famílias que a v3 de fato usa precisam existir no registro.
        for esperada in ("canal", "conhecimento", "financeiro", "identidade_crm", "controle"):
            self.assertIn(esperada, presentes)

    def test_status_resume_corretamente(self) -> None:
        s = cap.status_integracoes()
        self.assertEqual(s["liberadas"], 0)
        self.assertEqual(s["total"], len(cap.CAPACIDADES))
        self.assertGreater(s["total"], 30)

    def test_credencial_nao_libera(self) -> None:
        """A lição do F03: variável preenchida não é capacidade liberada."""
        import os

        os.environ["IG_ACCESS_TOKEN"] = "valor-de-teste"
        try:
            self.assertTrue(cap.CAPACIDADES["instagram.enviar_dm"].configurada())
            self.assertFalse(cap.CAPACIDADES["instagram.enviar_dm"].liberada())
        finally:
            os.environ.pop("IG_ACCESS_TOKEN", None)


class TestGuarda(unittest.TestCase):
    def test_capacidade_desconhecida_e_recusada(self) -> None:
        with self.assertRaises(cap.CapacidadeIndisponivel):
            cap.exigir_capacidade("nao.existe")

    def test_capacidade_fechada_diz_o_que_falta(self) -> None:
        with self.assertRaises(cap.CapacidadeIndisponivel) as ctx:
            cap.exigir_capacidade("lia.consultar_parcela")
        self.assertIn("falta", str(ctx.exception))


class TestRetorno(unittest.TestCase):
    def test_status_fora_do_contrato_e_recusado(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.Resultado(status="talvez").validar()

    def test_sucesso_sem_prova_e_recusado(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.Resultado(status="sucesso").validar()

    def test_sucesso_com_fonte_evidencia_e_horario_passa(self) -> None:
        r = cap.Resultado(
            status="sucesso",
            fonte="lia",
            evidence_id="ev-1",
            consultado_em="2026-09-24T10:00:00-03:00",
            source_updated_at="2026-09-24T09:58:00-03:00",
        )
        r.validar()
        self.assertTrue(r.pode_afirmar())

    def test_ausencia_nao_afirma(self) -> None:
        r = cap.Resultado(status="ausencia", fonte="assiny")
        r.validar()
        self.assertFalse(r.pode_afirmar())

    def test_falha_com_valor_e_suspeita(self) -> None:
        """Retorno de falha não pode carregar dado: vazio é indistinguível de ausência."""
        r = cap.Resultado(status="indisponivel", valor={"pedido": "123"})
        self.assertTrue(r.recusa_com_dado_vazio())

    def test_resultado_incerto_e_estado_valido(self) -> None:
        r = cap.Resultado(status="resultado_incerto", fonte="lia")
        r.validar()
        self.assertFalse(r.pode_afirmar())


class TestContexto(unittest.TestCase):
    def _ctx(self, **troca) -> cap.ContextoExecucao:
        base = dict(
            execution_id="ex-1",
            conta="edsonburger",
            case_id="caso-1",
            finalidade="atendimento",
            recurso_permitido="lia:bill:123",
            acao_aprovada="consultar_parcela",
            identidade_verificada=True,
        )
        base.update(troca)
        return cap.ContextoExecucao(**base)

    def test_contexto_ausente_e_recusado(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.exigir_contexto(None)

    def test_campo_vazio_e_recusado(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.exigir_contexto(self._ctx(case_id=""))

    def test_identidade_nao_verificada_e_recusada(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.exigir_contexto(self._ctx(identidade_verificada=False))

    def test_contexto_completo_passa(self) -> None:
        ctx = cap.exigir_contexto(self._ctx())
        self.assertEqual(ctx.case_id, "caso-1")


class TestDinheiro(unittest.TestCase):
    def test_inteiro_de_centavos_passa(self) -> None:
        self.assertEqual(cap.centavos(19990), 19990)

    def test_float_e_recusado(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.centavos(199.90)

    def test_bool_e_recusado(self) -> None:
        # bool é subclasse de int em Python — a recusa precisa ser explícita.
        with self.assertRaises(cap.ContratoInvalido):
            cap.centavos(True)

    def test_texto_e_recusado(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.centavos("199,90")


class TestPendencia(unittest.TestCase):
    def test_capacidade_desconhecida_e_recusada(self) -> None:
        with self.assertRaises(cap.CapacidadeIndisponivel):
            cap.registrar_pendencia("nao.existe", "motivo")

    def test_motivo_vazio_e_recusado(self) -> None:
        with self.assertRaises(cap.ContratoInvalido):
            cap.registrar_pendencia("lia.consultar_parcela", "   ")

    def test_pendencia_carrega_estado_da_capacidade(self) -> None:
        p = cap.registrar_pendencia("lia.consultar_parcela", "fonte vencida", case_id="c1")
        self.assertEqual(p["case_id"], "c1")
        self.assertFalse(p["estado"]["liberada"])
        self.assertEqual(p["estado"]["proximo_nivel"], "api_existente")


if __name__ == "__main__":
    unittest.main()
