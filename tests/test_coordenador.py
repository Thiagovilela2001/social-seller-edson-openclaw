"""Testes do coordenador de contatos (RN-025).

Rodar:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine" / "instagram_seller"))

import rules  # noqa: E402
import coordenador  # noqa: E402


# ---------------------------------------------------------------------------
# Base — banco temporario para cada teste
# ---------------------------------------------------------------------------

class BaseCoordenador(unittest.TestCase):
    """Cada teste roda contra um banco novo e vazio."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "estado.db"
        os.environ["IG_STATE_DB"] = str(self.db_path)
        # Recarrega os módulos para usar o banco temporário.
        importlib_reload(rules)
        importlib_reload(coordenador)

    def tearDown(self) -> None:
        os.environ.pop("IG_STATE_DB", None)
        self._tmp.cleanup()


def importlib_reload(module):
    """Reload para forcar re-inicializacao com banco temporario."""
    import importlib
    return importlib.reload(module)


# ---------------------------------------------------------------------------
# reserva_canal — mesmo id_interno, mesmo canal
# ---------------------------------------------------------------------------

class TestReservaCanalMesmaFonte(BaseCoordenador):
    """Mesma fonte pode estender; fonte diferente e fail-closed."""

    def test_primeira_reserva_retorna_ownership(self) -> None:
        resultado = coordenador.reservar_canal(
            id_interno="uuid-123",
            fonte="social-seller",
            canal="instagram",
            trace_id="ss-exec-1",
        )
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.id_interno, "uuid-123")
        self.assertEqual(resultado.fonte, "social-seller")
        self.assertEqual(resultado.canal, "instagram")
        self.assertEqual(resultado.estado, "contato_em_andamento")
        self.assertEqual(resultado.trace_id, "ss-exec-1")

    def test_mesma_fonte_estende_reserva(self) -> None:
        """A mesma fonte obtém refresh e retorna Ownership."""
        primeiro = coordenador.reservar_canal(
            id_interno="uuid-456",
            fonte="clint",
            canal="whatsapp",
            trace_id="clint-exec-1",
        )
        self.assertIsNotNone(primeiro)

        segundo = coordenador.reservar_canal(
            id_interno="uuid-456",
            fonte="clint",
            canal="whatsapp",
            trace_id="clint-exec-2",
        )
        self.assertIsNotNone(segundo)
        self.assertEqual(segundo.fonte, "clint")
        # expira_em deve ter sido atualizado.
        self.assertGreaterEqual(segundo.expira_em, primeiro.expira_em)

    def test_fonte_diferente_bloqueia_se_nao_expirou(self) -> None:
        """Fonte diferente e reserva ativa: fail-closed, retorna None."""
        # Social-seller reserva.
        coordenador.reservar_canal(
            id_interno="uuid-789",
            fonte="social-seller",
            canal="instagram",
            trace_id="ss-exec-x",
        )
        # Clint tenta o mesmo canal: bloqueado.
        resultado = coordenador.reservar_canal(
            id_interno="uuid-789",
            fonte="clint",
            canal="instagram",
            trace_id="clint-exec-y",
        )
        self.assertIsNone(resultado)

    def test_fonte_diferente_sucessede_se_expirou(self) -> None:
        """Fonte diferente mas reserva expirou: substitui."""
        # Reserva com TTL de 1 segundo.
        coordenador.reservar_canal(
            id_interno="uuid-exp",
            fonte="social-seller",
            canal="instagram",
            trace_id="ss-exec-1",
            ttl_seconds=5,
        )
        # Espera expirar.
        time.sleep(5.2)
        # Outra fonte consegue.
        resultado = coordenador.reservar_canal(
            id_interno="uuid-exp",
            fonte="clint",
            canal="instagram",
            trace_id="clint-exec-2",
        )
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.fonte, "clint")

    def test_sem_id_interno_retorna_none(self) -> None:
        self.assertIsNone(coordenador.reservar_canal("", "social-seller", "instagram"))
        self.assertIsNone(coordenador.reservar_canal("uuid-abc", "", "instagram"))
        self.assertIsNone(coordenador.reservar_canal("uuid-abc", "social-seller", ""))


# ---------------------------------------------------------------------------
# canal diferente — reservas paralelas
# ---------------------------------------------------------------------------

class TestCanaisParalelos(BaseCoordenador):
    """Canais diferentes para o mesmo id_interno podem ser reservados em paralelo."""

    def test_instagram_mais_whatsapp_simultaneo(self) -> None:
        """Instagram e WhatsApp para o mesmo lead: ambos funcionam."""
        r_ig = coordenador.reservar_canal(
            id_interno="uuid-abc",
            fonte="social-seller",
            canal="instagram",
            trace_id="ss-ig",
        )
        self.assertIsNotNone(r_ig)

        r_wa = coordenador.reservar_canal(
            id_interno="uuid-abc",
            fonte="clint",
            canal="whatsapp",
            trace_id="clint-wa",
        )
        self.assertIsNotNone(r_wa)

        self.assertEqual(r_ig.canal, "instagram")
        self.assertEqual(r_wa.canal, "whatsapp")

    def test_tres_canais_paralelos(self) -> None:
        """Instagram + WhatsApp + email para o mesmo lead: todos funcionam."""
        ig = coordenador.reservar_canal("uuid-3c", "social-seller", "instagram")
        wa = coordenador.reservar_canal("uuid-3c", "clint", "whatsapp")
        em = coordenador.reservar_canal("uuid-3c", "educzz", "email")

        self.assertIsNotNone(ig)
        self.assertIsNotNone(wa)
        self.assertIsNotNone(em)


# ---------------------------------------------------------------------------
# expiracao
# ---------------------------------------------------------------------------

class TestExpiracao(BaseCoordenador):
    """Reserva expira e liberta o canal para nova tentativa."""

    def test_reserva_expira_e_outra_fonte_consegue(self) -> None:
        """Apos expiracao, fonte diferente obtem a reserva."""
        # TTL curto: 2 segundos.
        r1 = coordenador.reservar_canal(
            "uuid-exp", "social-seller", "instagram", ttl_seconds=5
        )
        self.assertIsNotNone(r1)

        time.sleep(5.2)
        r2 = coordenador.reservar_canal(
            "uuid-exp", "clint", "instagram"
        )
        self.assertIsNotNone(r2)
        self.assertEqual(r2.fonte, "clint")

    def test_verificar_canal_retorna_none_apos_expirar(self) -> None:
        r = coordenador.reservar_canal("uuid-v", "ss", "instagram", ttl_seconds=5)
        self.assertIsNotNone(r)
        time.sleep(5.2)
        verificado = coordenador.verificar_canal("uuid-v", "instagram")
        self.assertIsNone(verificado)


# ---------------------------------------------------------------------------
# liberar_canal
# ---------------------------------------------------------------------------

class TestLiberarCanal(BaseCoordenador):
    """So a fonte que reservou pode liberar."""

    def test_fonte_correta_libera(self) -> None:
        coordenador.reservar_canal("uuid-l", "social-seller", "instagram")
        resultado = coordenador.liberar_canal("uuid-l", "social-seller", "instagram", "resolvido")
        self.assertTrue(resultado)

    def test_fonte_diferente_nao_libera(self) -> None:
        """Socio tenta liberar o que social-seller reservou: ignora."""
        coordenador.reservar_canal("uuid-l2", "social-seller", "instagram")
        resultado = coordenador.liberar_canal("uuid-l2", "clint", "instagram", "resolvido")
        self.assertFalse(resultado)

    def test_libera_marca_estado_resolvido(self) -> None:
        coordenador.reservar_canal("uuid-l3", "ss", "instagram")
        coordenador.liberar_canal("uuid-l3", "ss", "instagram", "resolvido")
        # Verificar que o registro mudou de estado.
        with rules.db() as conn:
            row = conn.execute(
                "SELECT estado FROM ownership WHERE id_interno = ? AND canal = ?",
                ("uuid-l3", "instagram"),
            ).fetchone()
        self.assertEqual(row["estado"], "resolvido")


# ---------------------------------------------------------------------------
# limpar_expirados
# ---------------------------------------------------------------------------

class TestLimparExpirados(BaseCoordenador):
    """Remove reservas expiradas do banco."""

    def test_limpa_expirados_remove_registros(self) -> None:
        """Registros expirados sao removidos."""
        # Cria duas reservas: uma vai expirar, outra nao.
        coordenador.reservar_canal("uuid-c1", "ss", "instagram", ttl_seconds=5)
        coordenador.reservar_canal("uuid-c2", "clint", "whatsapp", ttl_seconds=3600)

        time.sleep(5.2)
        count = coordenador.limpar_expirados()
        self.assertEqual(count, 1)

        # O que nao expirou permanece.
        verificado = coordenador.verificar_canal("uuid-c2", "whatsapp")
        self.assertIsNotNone(verificado)

    def test_limpar_retorna_zero_quando_nada_expirou(self) -> None:
        coordenador.reservar_canal("uuid-limp", "ss", "instagram", ttl_seconds=3600)
        count = coordenador.limpar_expirados()
        self.assertEqual(count, 0)

    def test_limpa_reserva_vencida_em_estado_final(self) -> None:
        """D3: sem o filtro por `estado`, reserva vencida em `resolvido`/
        `abandonado` é linha morta segurando a PK `(id_interno, canal)`."""
        coordenador.reservar_canal("uuid-c2", "ss", "whatsapp", ttl_seconds=5)
        with rules.db() as conn:
            conn.execute(
                "UPDATE ownership SET estado = 'resolvido' WHERE id_interno = 'uuid-c2'"
            )
        time.sleep(5.2)
        self.assertEqual(coordenador.limpar_expirados(), 1)
        with rules.db() as conn:
            restantes = conn.execute(
                "SELECT COUNT(*) AS n FROM ownership WHERE id_interno = 'uuid-c2'"
            ).fetchone()["n"]
        self.assertEqual(restantes, 0)


class TestLimparExpiradosNoExpurgoDiario(BaseCoordenador):
    """D3: `limpar_expirados()` não tinha chamador em runtime. Ligada ao expurgo
    de 24h em 29/09/2026 (Documento Mestre v4 §45 D3)."""

    def test_expurgo_de_24h_remove_ownership_vencida(self) -> None:
        import time as _t

        coordenador.reservar_canal("uuid-d3", "ss", "instagram", ttl_seconds=1)
        with rules.db() as conn:
            conn.execute(
                "UPDATE ownership SET expira_em = ? WHERE id_interno = 'uuid-d3'",
                ("2000-01-01T00:00:00-03:00",),
            )
        # Expurgo forcado: sem o registro de `manutencao` a primeira chamada roda.
        agora = _t.time()
        apagados = rules.expurgar_se_preciso(intervalo_horas=0, now=agora)
        self.assertIn("ownership", apagados)
        self.assertEqual(apagados["ownership"], 1)
        with rules.db() as conn:
            restantes = conn.execute(
                "SELECT COUNT(*) AS n FROM ownership WHERE id_interno = 'uuid-d3'"
            ).fetchone()["n"]
        self.assertEqual(restantes, 0, "a reserva vencida ficou no banco apos o expurgo")

    def test_expurgo_mantem_ownership_vigente(self) -> None:
        coordenador.reservar_canal("uuid-d3-ok", "ss", "instagram", ttl_seconds=3600)
        apagados = rules.expurgar_se_preciso(intervalo_horas=0)
        self.assertEqual(apagados.get("ownership", 0), 0)
        self.assertIsNotNone(coordenador.verificar_canal("uuid-d3-ok", "instagram"))


# ---------------------------------------------------------------------------
# integracao com avaliar_envio (RN-025)
# ---------------------------------------------------------------------------

class TestIntegracaoAvaliarEnvio(BaseCoordenador):
    """A verificacao RN-025 bloqueia envio quando canal esta reservado por outra fonte."""

    def test_reserva_existente_bloqueia_envio(self) -> None:
        """Social-seller reserva Instagram; avaliar_envio bloqueia Clint."""
        # Social-seller obtem a reserva.
        r = coordenador.reservar_canal(
            id_interno="uuid-i1",
            fonte="social-seller",
            canal="instagram",
            trace_id="ss-exec-a",
        )
        self.assertIsNotNone(r)

        # Clint tenta enviar: bloqueado por RN-025.
        bloqueios = rules.avaliar_envio(
            texto="Oi, tudo bem?",
            canal="instagram",
            execution_id="clint-exec-b",
            id_interno="uuid-i1",
        )
        bloqueio_coord = [b for b in bloqueios if b.regra == rules.RN_COORDENACAO_CONTATOS]
        self.assertEqual(len(bloqueio_coord), 1)
        self.assertEqual(bloqueio_coord[0].motivo, "canal_reservado_por_outra_fonte")

    def test_mesma_fonte_nao_e_bloqueada(self) -> None:
        """Social-seller ja tem a reserva; pode continuar (RN-025 nao bloqueia)."""
        coordenador.reservar_canal(
            id_interno="uuid-i2",
            fonte="social-seller",
            canal="instagram",
            trace_id="ss-exec-c",
        )
        bloqueios = rules.avaliar_envio(
            texto="Seguinte mensagem...",
            canal="instagram",
            execution_id="ss-exec-d",
            id_interno="uuid-i2",
        )
        bloqueio_coord = [b for b in bloqueios if b.regra == rules.RN_COORDENACAO_CONTATOS]
        self.assertEqual(len(bloqueio_coord), 0)

    def test_sem_id_interno_nao_ativa_coordenacao(self) -> None:
        """Quando id_interno e vazio, a checagem RN-025 e pulada (compatibilidade)."""
        bloqueios = rules.avaliar_envio(
            texto="Oi",
            canal="instagram",
            execution_id="ss-exec-e",
            # sem id_interno
        )
        bloqueio_coord = [b for b in bloqueios if b.regra == rules.RN_COORDENACAO_CONTATOS]
        self.assertEqual(len(bloqueio_coord), 0)

    def test_execution_id_informa_fonte(self) -> None:
        """execution_id com prefixo e usado para inferir a fonte."""
        # Reserva para clint.
        coordenador.reservar_canal(
            id_interno="uuid-i3",
            fonte="clint",
            canal="whatsapp",
            trace_id="clint-exec-x",
        )
        # Social-seller tenta o mesmo canal: bloqueado.
        bloqueios = rules.avaliar_envio(
            canal="whatsapp",
            execution_id="ss-exec-y",
            id_interno="uuid-i3",
        )
        bloqueio_coord = [b for b in bloqueios if b.regra == rules.RN_COORDENACAO_CONTATOS]
        self.assertEqual(len(bloqueio_coord), 1)

    def test_libera_canal_remove_bloqueio(self) -> None:
        """Apos liberar, outra fonte consegue enviar."""
        coordenador.reservar_canal(
            id_interno="uuid-i4",
            fonte="social-seller",
            canal="instagram",
        )
        # Resolve.
        coordenador.liberar_canal("uuid-i4", "social-seller", "instagram", "resolvido")
        # Clint agora consegue.
        bloqueios = rules.avaliar_envio(
            canal="instagram",
            execution_id="clint-exec-z",
            id_interno="uuid-i4",
        )
        bloqueio_coord = [b for b in bloqueios if b.regra == rules.RN_COORDENACAO_CONTATOS]
        self.assertEqual(len(bloqueio_coord), 0)


# ---------------------------------------------------------------------------
# estado da reserva
# ---------------------------------------------------------------------------

class TestEstadosDaReserva(BaseCoordenador):
    """Estados possiveis da reserva: contato_em_andamento, resolvido, abandonado."""

    def test_reserva_criada_com_estado_andamento(self) -> None:
        r = coordenador.reservar_canal("uuid-est", "ss", "instagram")
        self.assertEqual(r.estado, "contato_em_andamento")

    def test_liberar_com_estado_resolvido(self) -> None:
        coordenador.reservar_canal("uuid-est2", "ss", "instagram")
        coordenador.liberar_canal("uuid-est2", "ss", "instagram", "resolvido")
        with rules.db() as conn:
            row = conn.execute(
                "SELECT estado FROM ownership WHERE id_interno = ?",
                ("uuid-est2",),
            ).fetchone()
        self.assertEqual(row["estado"], "resolvido")

    def test_liberar_com_estado_abandonado(self) -> None:
        coordenador.reservar_canal("uuid-est3", "ss", "instagram")
        coordenador.liberar_canal("uuid-est3", "ss", "instagram", "abandonado")
        with rules.db() as conn:
            row = conn.execute(
                "SELECT estado FROM ownership WHERE id_interno = ?",
                ("uuid-est3",),
            ).fetchone()
        self.assertEqual(row["estado"], "abandonado")


if __name__ == "__main__":
    unittest.main(verbosity=2)
