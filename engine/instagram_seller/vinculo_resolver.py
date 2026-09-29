"""Resolução de vínculo e responsável financeiro.

Referência: §07-§08 do Documento Mestre v3.

Este módulo é o ponto central de resolução de vínculo. Ele depende do `rules.py`
para acesso ao banco de estado. O `rules.py` importa deste módulo para alimentar
`avaliar_envio()` — a importação é unidirecional (este → rules).

Regras de negócio:
  - Ações financeiras exigem vínculo verificado.
  - Responsável financeiro ≠ cliente educacional (são pessoas diferentes).
  - CPF/documento: SEMPRE em hash; jamais em texto limpo.
  - Dados crus da fonte vão para metadata_json, sem PII exposto.
"""

from __future__ import annotations

import json
from typing import Optional

# Importação tardia para evitar ciclo: este módulo é usado pelo rules.py que
# importa este módulo. O import em rules.py é tardio (dentro da função).
import rules


# ---------------------------------------------------------------------------
# Ações que exigem vínculo verificado (RN-VINCULO)
# ---------------------------------------------------------------------------

ACOES_FINANCEIRAS = frozenset({
    "consultar_parcela",
    "consultar_financiamento",
    "verificar_renegociacao",
    "obter_segunda_via",
    "consultar_faturas",
    "consultar_pedido",   # quando envolve dado de compra
    "consultar_contrato",
    "consultar_boleto",
    "consultar_pagamento",
})


def e_acao_financeira(acao: str) -> bool:
    """True se a ação exige vínculo verificado com responsável financeiro."""
    return acao in ACOES_FINANCEIRAS


# ---------------------------------------------------------------------------
# Persistência de identidade
# ---------------------------------------------------------------------------

def salvar_identidade(identidade: "modelo_dados.Identidade") -> None:
    """Insere ou atualiza uma identidade no banco.

    O `id_interno` é a chave — identidade existente é atualizada, não duplicada.
    """
    with rules.db() as conn:
        conn.execute(
            """
            INSERT INTO identidades
                (id_interno, plataforma, id_externo, namespace_id, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_interno) DO UPDATE SET
                plataforma = excluded.plataforma,
                id_externo = excluded.id_externo,
                namespace_id = excluded.namespace_id,
                atualizado_em = excluded.atualizado_em
            """,
            (
                identidade.id_interno,
                identidade.plataforma,
                identidade.id_externo,
                identidade.namespace_id,
                identidade.criado_em,
                identidade.atualizado_em,
            ),
        )


def carregar_identidade(id_interno: str) -> Optional["modelo_dados.Identidade"]:
    """Carrega identidade pelo id_interno (UUID)."""
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        row = conn.execute(
            "SELECT * FROM identidades WHERE id_interno = ?", (id_interno,)
        ).fetchone()
    if not row:
        return None
    return modelo_dados.Identidade.from_dict(dict(row))


def carregar_identidade_por_namespace(namespace_id: str) -> Optional["modelo_dados.Identidade"]:
    """Carrega identidade pelo namespace completo (plataforma:id_externo)."""
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        row = conn.execute(
            "SELECT * FROM identidades WHERE namespace_id = ?", (namespace_id,)
        ).fetchone()
    if not row:
        return None
    return modelo_dados.Identidade.from_dict(dict(row))


def obter_ou_criar_identidade(
    plataforma: str,
    id_externo: str,
) -> tuple["modelo_dados.Identidade", bool]:
    """Retorna (identidade, criada/agora). Se já existe, devolve a existente.

    Retorna tupla para o chamador decidir o que fazer com o fato de ser novo
    ou existente — esta função não assume.
    """
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    existente = carregar_identidade_por_namespace(
        modelo_dados.formatar_namespace(plataforma, id_externo)
    )
    if existente:
        return existente, False

    identidade = modelo_dados.Identidade.criar(plataforma, id_externo)
    salvar_identidade(identidade)
    return identidade, True


# ---------------------------------------------------------------------------
# Persistência de vínculo
# ---------------------------------------------------------------------------

def _serializar_metadata(metadata: dict) -> str:
    """Serializa metadata para JSON, sem nunca incluir documento limpo."""
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True)


def _deserializar_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def criar_vinculo(
    id_interno: str,
    tipo: str,
    documento: str,
    plataforma_origem: str,
    metadata: Optional[dict] = None,
) -> "modelo_dados.Vinculo":
    """Cria vínculo novo — faz hash do documento internamente.

    O documento limpo jamais é guardado. O hash é irreversível (SHA-256).
    """
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    documento_hash = modelo_dados.hash_documento(documento)
    agora = modelo_dados._now_iso()

    vinculo = modelo_dados.Vinculo(
        id_interno=id_interno,
        tipo=tipo,
        documento_hash=documento_hash,
        plataforma_origem=plataforma_origem,
        verificado_em=None,
        fonte_verificacao=None,
        metadata=metadata or {},
    )

    with rules.db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO vinculos
                (id_interno, tipo, documento_hash, plataforma_origem,
                 verificado_em, fonte_verificacao, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vinculo.id_interno,
                vinculo.tipo,
                vinculo.documento_hash,
                vinculo.plataforma_origem,
                vinculo.verificado_em,
                vinculo.fonte_verificacao,
                _serializar_metadata(vinculo.metadata),
            ),
        )

    return vinculo


def carregar_vinculo(id_interno: str, tipo: str) -> Optional["modelo_dados.Vinculo"]:
    """Carrega vínculo específico (id_interno + tipo)."""
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        row = conn.execute(
            "SELECT * FROM vinculos WHERE id_interno = ? AND tipo = ?",
            (id_interno, tipo),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["metadata"] = _deserializar_metadata(data.pop("metadata_json", None))
    return modelo_dados.Vinculo.from_dict(data)


def carregar_vinculos(id_interno: str) -> list["modelo_dados.Vinculo"]:
    """Todos os vínculos de uma identidade."""
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        rows = conn.execute(
            "SELECT * FROM vinculos WHERE id_interno = ?", (id_interno,)
        ).fetchall()
    vinculos = []
    for row in rows:
        data = dict(row)
        data["metadata"] = _deserializar_metadata(data.pop("metadata_json", None))
        vinculos.append(modelo_dados.Vinculo.from_dict(data))
    return vinculos


def resolver_por_documento_hash(documento_hash: str) -> list["modelo_dados.Vinculo"]:
    """Busca vínculos pelo hash do documento (para match em integração)."""
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        rows = conn.execute(
            "SELECT * FROM vinculos WHERE documento_hash = ?", (documento_hash,)
        ).fetchall()
    vinculos = []
    for row in rows:
        data = dict(row)
        data["metadata"] = _deserializar_metadata(data.pop("metadata_json", None))
        vinculos.append(modelo_dados.Vinculo.from_dict(data))
    return vinculos


def verificar_vinculo(id_interno: str, fonte: str) -> Optional["modelo_dados.Vinculo"]:
    """Verifica se existe vínculo já verificado por esta fonte.

    Se já existe vínculo (de qualquer tipo) e ele foi verificado por `fonte`,
    devolve esse vínculo. Útil para saber se uma integração já confirmou.
    """
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        row = conn.execute(
            "SELECT * FROM vinculos WHERE id_interno = ? AND verificado_em IS NOT NULL "
            "AND fonte_verificacao = ?",
            (id_interno, fonte),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["metadata"] = _deserializar_metadata(data.pop("metadata_json", None))
    return modelo_dados.Vinculo.from_dict(data)


def atualizar_vinculo(
    id_interno: str,
    tipo: str,
    fonte: str,
    verificado_em: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Atualiza timestamp de verificação de vínculo existente.

    Se `verificado_em` for omitido, usa o momento atual.
    metadata é mesclado com o existente (nunca sobrescreve).
    """
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    if verificado_em is None:
        verificado_em = modelo_dados._now_iso()

    with rules.db() as conn:
        # Carrega metadata existente para mesclar.
        row = conn.execute(
            "SELECT metadata_json FROM vinculos WHERE id_interno = ? AND tipo = ?",
            (id_interno, tipo),
        ).fetchone()
        existente = _deserializar_metadata(row["metadata_json"] if row else None)
        mesclado = {**existente}
        if metadata:
            mesclado.update(metadata)

        conn.execute(
            """
            UPDATE vinculos
            SET verificado_em = ?, fonte_verificacao = ?, metadata_json = ?
            WHERE id_interno = ? AND tipo = ?
            """,
            (
                verificado_em,
                fonte,
                _serializar_metadata(mesclado),
                id_interno,
                tipo,
            ),
        )


def verificar_vinculo_financeiro(id_interno: str) -> tuple[bool, Optional["modelo_dados.Vinculo"]]:
    """Retorna (tem_vinculo_verificado, vinculo).

    Para ações financeiras, o vínculo de responsável financeiro precisa estar
    verificado por alguma fonte (clint, educzz, lia, etc.).
    """
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        row = conn.execute(
            "SELECT * FROM vinculos WHERE id_interno = ? AND verificado_em IS NOT NULL "
            "AND tipo = 'responsavel_financeiro'",
            (id_interno,),
        ).fetchone()
    if not row:
        return False, None
    data = dict(row)
    data["metadata"] = _deserializar_metadata(data.pop("metadata_json", None))
    return True, modelo_dados.Vinculo.from_dict(data)


def responsavel_diferente_do_cliente(id_interno: str) -> tuple[bool, str]:
    """Verifica que responsável financeiro ≠ cliente educacional.

    Regra: para ações financeiras, o responsável precisa ser pessoa diferente do
    cliente educacional. Isso impede que alguém declare ser responsável por si mesmo.

    Retorna (diferentes_ok, motivo).
    """
    try:
        from . import modelo_dados
    except ImportError:
        import modelo_dados

    with rules.db() as conn:
        rows = conn.execute(
            "SELECT * FROM vinculos WHERE id_interno = ? AND tipo IN "
            "('responsavel_financeiro', 'cliente_educacional')",
            (id_interno,),
        ).fetchall()

    responsavel_hash = None
    cliente_hash = None

    for row in rows:
        data = dict(row)
        if data["tipo"] == "responsavel_financeiro":
            responsavel_hash = data["documento_hash"]
        elif data["tipo"] == "cliente_educacional":
            cliente_hash = data["documento_hash"]

    # Se um dos dois não existe, não dá para comparar.
    if not responsavel_hash or not cliente_hash:
        return True, "sem_dados_suficientes"

    return responsavel_hash != cliente_hash, ""


# ---------------------------------------------------------------------------
# Check para rules.avaliar_envio — falhar fechado em ação financeira
# ---------------------------------------------------------------------------

RN_VINCULO_FINANCEIRO = "RN-VINCULO"


def check_vinculo_financeiro(acao: str, id_interno: str) -> Optional["rules.Bloqueio"]:
    """Retorna Bloqueio se ação financeira sem vínculo verificado, None se OK."""
    if not e_acao_financeira(acao):
        return None

    tem, vinculo = verificar_vinculo_financeiro(id_interno)
    if tem:
        return None

    # Falhou: não tem vínculo verificado.
    return rules.Bloqueio(
        RN_VINCULO_FINANCEIRO,
        "acao_financeira_sem_vinculo_verificado",
        f"Ação '{acao}' exige vínculo de responsável financeiro verificado por fonte "
        "confiável (Clint, Educzz, LIA). Vinculação não encontrada.",
    )


def check_vinculo_responsavel(id_interno: str) -> Optional["rules.Bloqueio"]:
    """Retorna Bloqueio se responsável = cliente (mesmo documento)."""
    diferentes_ok, motivo = responsavel_diferente_do_cliente(id_interno)

    if diferentes_ok:
        return None

    return rules.Bloqueio(
        RN_VINCULO_FINANCEIRO,
        "responsavel_igual_cliente",
        "Responsável financeiro e cliente educacional têm o mesmo documento. "
        "O responsável precisa ser pessoa diferente do cliente.",
    )
