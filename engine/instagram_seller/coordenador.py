"""Coordenador de contatos — ownership por caso para evitar toque simultaneo.

**Problema:** a Clint, o canal nativo, a Evolution e workflows nao podem ser emissores
independentes para o mesmo lead. Sem coordenacao, duas fontes tocam o mesmo lead ao
mesmo tempo — a experiencia do lead e o credito da marca sofrem.

**Solucao:** ownership pessimista com TTL curto (5 minutos). A primeira fonte a tocar
obtem a reserva do canal. Fontes diferentes precisam esperar ou escalar.

Regras:
  - Fail-closed: canal reservado por outra fonte = bloqueio, nao ignorar.
  - Mesma fonte pode estender (refresh do TTL).
  - Canal diferente pode ser reservado em paralelo (ex: Instagram + WhatsApp).
  - `id_interno` (UUID) e a chave — nao `igsid` — porque permite ancorar
    em qualquer plataforma.

Referencia: Documento Mestre v3 §28, RN-025.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    from . import rules
except ImportError:  # pragma: no cover
    import rules  # type: ignore[no-redef]


def _rules_db():
    """Acessa rules.db sempre da versao mais recente em sys.modules.

    Isso evita o problema de import_relative vs import_absoluto em que
    o objeto rules cacheado no modulo nao e atualizado por importlib.reload().
    O modulo rules e sempre obtido de sys.modules no momento da chamada.
    """
    import sys

    # Procura o modulo rules sob qualquer chave possivel em sys.modules.
    # O nome depende de como o modulo foi importado:
    #   - via package: "engine.instagram_seller.rules"
    #   - via sys.path.insert: "rules"
    #   - via pytest: "engine.instagram_seller.rules"
    for key, mod in sys.modules.items():
        if key.endswith(".rules") or key == "rules":
            if hasattr(mod, "db") and hasattr(mod, "state_db_path"):
                return mod.db()

    # Nenhum modulo rules encontrado: usa a referencia importada ao nivel do modulo.
    return rules.db()

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

# TTL da reserva em segundos. Curto o suficiente para permitir nova tentativa
# rapida quando a fonte original falha; longo o suficiente para o agente concluir
# o toque sem ter de fazer refresh a cada passo.
OWNERSHIP_TTL_SECONDS = 5 * 60  # 5 minutos

# Offset fixo: Brasil sem horario de verao desde 2019.
TZ_BRT = timezone(timedelta(hours=-3))


def _now_brt() -> datetime:
    return datetime.now(timezone.utc).astimezone(TZ_BRT)


def _now_iso() -> str:
    return _now_brt().isoformat()


# ---------------------------------------------------------------------------
# Dataclass — registro de ownership
# ---------------------------------------------------------------------------

@dataclass
class Ownership:
    """Registro de quem pode tocar um lead neste momento.

    O `id_interno` e a ancora de referencia — permite rastrear o mesmo lead
    em qualquer plataforma sem depender de igsid, username ou e-mail.
    """

    id_interno: str           # UUID da Identidade (v3 §07)
    fonte: str              # "social-seller", "clint", "educzz", "lia", "yampi"
    canal: str              # "instagram", "whatsapp", "email", "sms"
    reservado_em: str         # ISO datetime BRT
    expira_em: str          # ISO datetime BRT
    estado: str             # "contato_em_andamento" | "resolvido" | "abandonado"
    trace_id: Optional[str]  # execution_id que reservou

    def expirou(self, agora_iso: Optional[str] = None) -> bool:
        momento = agora_iso or _now_iso()
        return momento > self.expira_em

    def to_dict(self) -> dict:
        return {
            "id_interno": self.id_interno,
            "fonte": self.fonte,
            "canal": self.canal,
            "reservado_em": self.reservado_em,
            "expira_em": self.expira_em,
            "estado": self.estado,
            "trace_id": self.trace_id,
        }


# ---------------------------------------------------------------------------
# Helpers de conversao (banco <-> dataclass)
# ---------------------------------------------------------------------------

def _row_to_ownership(row) -> Ownership:
    return Ownership(
        id_interno=str(row["id_interno"]),
        fonte=str(row["fonte"]),
        canal=str(row["canal"]),
        reservado_em=str(row["reservado_em"]),
        expira_em=str(row["expira_em"]),
        estado=str(row["estado"]),
        trace_id=str(row["trace_id"]) if row["trace_id"] is not None else None,
    )


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def reservar_canal(
    id_interno: str,
    fonte: str,
    canal: str,
    trace_id: str = "",
    ttl_seconds: int = OWNERSHIP_TTL_SECONDS,
) -> Optional[Ownership]:
    """Tenta reservar um canal para uma fonte.

    Regras:
      - Mesma fonte: estende o TTL (refresh). Retorna o novo Ownership.
      - Fonte diferente: fail-closed — retorna None.
      - Canal diferente para o mesmo id_interno: pode ser reservado em paralelo
        (ex: Instagram + WhatsApp simultaneamente).

    Args:
        id_interno: UUID da identidade do lead (v3 §07).
        fonte: nome da fonte emissora ("social-seller", "clint", "educzz", etc.).
        canal: canal a ser reservado ("instagram", "whatsapp", "email", etc.).
        trace_id: execution_id que esta fazendo a reserva (para auditoria).
        ttl_seconds: duracao da reserva em segundos. Para teste apenas.

    Returns:
        Ownership se a reserva foi feita (nova ou refresh da mesma fonte).
        None se outra fonte ja reservou este canal.
    """
    if not id_interno or not fonte or not canal:
        return None

    agora = _now_iso()
    expira = _agora_mais(ttl_seconds)

    with _rules_db() as conn:
        row = conn.execute(
            "SELECT * FROM ownership WHERE id_interno = ? AND canal = ?",
            (id_interno, canal),
        ).fetchone()

        if not row:
            # Primeira reserva para este (id_interno, canal).
            conn.execute(
                """
                INSERT INTO ownership
                (id_interno, fonte, canal, reservado_em, expira_em, estado, trace_id)
                VALUES (?, ?, ?, ?, ?, 'contato_em_andamento', ?)
                """,
                (id_interno, fonte, canal, agora, expira, trace_id or None),
            )
            _log.debug(
                "ownership_acquire id_interno=%s canal=%s fonte=%s",
                id_interno, canal, fonte,
            )
            # Devolve o Ownership diretamente sem abrir nova conexao.
            return Ownership(
                id_interno=id_interno,
                fonte=fonte,
                canal=canal,
                reservado_em=agora,
                expira_em=expira,
                estado="contato_em_andamento",
                trace_id=trace_id or None,
            )

        # Ja existe reserva para este canal.
        reserva_existente = _row_to_ownership(row)

        # Fonte igual: estende o TTL (refresh).
        if reserva_existente.fonte == fonte:
            if reserva_existente.expirou(agora):
                # TTL zerou: cria nova reserva no lugar (DELETE + INSERT).
                conn.execute(
                    "DELETE FROM ownership WHERE id_interno = ? AND canal = ?",
                    (id_interno, canal),
                )
                conn.execute(
                    """
                    INSERT INTO ownership
                    (id_interno, fonte, canal, reservado_em, expira_em, estado, trace_id)
                    VALUES (?, ?, ?, ?, ?, 'contato_em_andamento', ?)
                    """,
                    (id_interno, fonte, canal, agora, expira, trace_id or None),
                )
                _log.debug(
                    "ownership_refresh id_interno=%s canal=%s fonte=%s",
                    id_interno, canal, fonte,
                )
            else:
                # TTL ativo: estende.
                conn.execute(
                    "UPDATE ownership SET expira_em = ?, trace_id = ?, "
                    "estado = 'contato_em_andamento' "
                    "WHERE id_interno = ? AND canal = ?",
                    (expira, trace_id or None, id_interno, canal),
                )
                _log.debug(
                    "ownership_extend id_interno=%s canal=%s fonte=%s ate=%s",
                    id_interno, canal, fonte, expira,
                )
            # Devolve o Ownership diretamente da row atualizada.
            updated_row = conn.execute(
                "SELECT * FROM ownership WHERE id_interno = ? AND canal = ?",
                (id_interno, canal),
            ).fetchone()
            return _row_to_ownership(updated_row) if updated_row else None

        # Fonte diferente: fail-closed exceto se TTL expirou.
        if not reserva_existente.expirou(agora):
            _log.debug(
                "ownership_denied id_interno=%s canal=%s fonte=%s por=%s",
                id_interno, canal, fonte, reserva_existente.fonte,
            )
            return None

        # TTL expirou: substitui (DELETE + INSERT para evitar violacao de PK).
        conn.execute(
            "DELETE FROM ownership WHERE id_interno = ? AND canal = ?",
            (id_interno, canal),
        )
        conn.execute(
            """
            INSERT INTO ownership
            (id_interno, fonte, canal, reservado_em, expira_em, estado, trace_id)
            VALUES (?, ?, ?, ?, ?, 'contato_em_andamento', ?)
            """,
            (id_interno, fonte, canal, agora, expira, trace_id or None),
        )
        _log.debug(
            "ownership_replace id_interno=%s canal=%s fonte=%s",
            id_interno, canal, fonte,
        )
        return Ownership(
            id_interno=id_interno,
            fonte=fonte,
            canal=canal,
            reservado_em=agora,
            expira_em=expira,
            estado="contato_em_andamento",
            trace_id=trace_id or None,
        )


def liberar_canal(
    id_interno: str,
    fonte: str,
    canal: str,
    estado: str = "resolvido",
) -> bool:
    """Libera o canal apos resolucao ou abandono.

    Somente a fonte que reservou pode liberar. Se o canal ja expirou ou
    pertence a outra fonte, retorna False.

    Args:
        id_interno: UUID da identidade do lead.
        fonte: fonte que esta liberando (deve ser a mesma que reservou).
        canal: canal a ser liberado.
        estado: "resolvido" (sucesso) ou "abandonado" (timeout/falha).

    Returns:
        True se liberation foi bem-sucedida.
        False se a fonte nao e a dona da reserva ou o canal nao existe.
    """
    if not id_interno or not fonte or not canal:
        return False

    if estado not in ("resolvido", "abandonado"):
        estado = "resolvido"

    with _rules_db() as conn:
        # Só libera se esta fonte for a dona (protege contra releases acidentais).
        afetadas = conn.execute(
            "UPDATE ownership SET estado = ? "
            "WHERE id_interno = ? AND canal = ? AND fonte = ?",
            (estado, id_interno, canal, fonte),
        ).rowcount
    return afetadas > 0


def verificar_canal(id_interno: str, canal: str) -> Optional[Ownership]:
    """Verifica se ha reserva ativa para um canal.

    Returns:
        Ownership se existe reserva ativa e nao expirou.
        None se nao ha reserva ou se ja expirou.
    """
    if not id_interno or not canal:
        return None

    agora = _now_iso()
    with _rules_db() as conn:
        row = conn.execute(
            "SELECT * FROM ownership WHERE id_interno = ? AND canal = ?",
            (id_interno, canal),
        ).fetchone()

    if not row:
        return None

    ownership = _row_to_ownership(row)
    # Exclui estados terminais (resolvido/abandonado) independentemente da expiracao.
    if ownership.estado in ("resolvido", "abandonado"):
        return None
    if ownership.expirou(agora):
        return None
    return ownership


def limpar_expirados() -> int:
    """Remove reservas expiradas.

    Pode ser chamada periodicamente (ex: tarefa agendada ou maintenance loop).
    As reservas expiradas sao automaticamente ignoradas por `verificar_canal`
    e `reservar_canal` — esta funcao faz a limpeza assincrona do banco.

    Returns:
        Quantidade de registros removidos.
    """
    agora = _now_iso()
    with _rules_db() as conn:
        cur = conn.execute(
            "DELETE FROM ownership WHERE expira_em < ? AND estado = 'contato_em_andamento'",
            (agora,),
        )
    count = cur.rowcount
    if count:
        _log.info("ownership_cleanup removed=%d", count)
    return count


def ownership_atual(id_interno: str, canal: str) -> Optional[Ownership]:
    """Alias legivel para `verificar_canal`. Preferir `verificar_canal`."""
    return verificar_canal(id_interno, canal)


# ---------------------------------------------------------------------------
# Integracao com regras de negocio (RN-025)
# ---------------------------------------------------------------------------

def bloqueio_coordenacao(
    id_interno: str,
    fonte: str,
    canal: str,
) -> Optional[rules.Bloqueio]:
    """Verifica se o canal esta reservado por outra fonte (RN-025).

    Chamado por `avaliar_envio` antes de qualquer envio.

    Args:
        id_interno: UUID da identidade do lead.
        fonte: fonte que esta tentando enviar.
        canal: canal que a fonte quer usar.

    Returns:
        `rules.Bloqueio` se outra fonte ja reservou (bloqueio).
        None se pode prosseguir.
    """
    if not id_interno or not canal:
        return None

    reserva = verificar_canal(id_interno, canal)
    if reserva is None:
        return None

    # Mesma fonte: pode continuar (refresh automatico em reservar_canal).
    if reserva.fonte == fonte:
        return None

    # Fonte diferente: fail-closed.
    return rules.Bloqueio(
        regra=rules.RN_COORDENACAO_CONTATOS,
        motivo="canal_reservado_por_outra_fonte",
        detalhe=(
            f"Canal '{canal}' reservado por '{reserva.fonte}' desde "
            f"{reserva.reservado_em}. "
            f"Outro toque simultaneouso esta bloqueado. "
            f"Tente novamente apos {reserva.expira_em} ou use canal diferente."
        ),
    )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _agora_mais(seconds: int) -> str:
    """ISO datetime daqui a `seconds` segundos em BRT."""
    futuro = datetime.now(timezone.utc).astimezone(TZ_BRT) + timedelta(seconds=seconds)
    return futuro.isoformat()
