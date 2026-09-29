"""Modelos de dados para identidade e vínculo do Social Seller.

Este módulo define o esquema de dados para identidade unificada (namespace de plataforma)
e vínculo com responsável financeiro — com privacidade por design:
- CPF/documento: SEMPRE em hash, nunca em texto limpo
- IGSID: não entra em log, só em storage
- Namespace: evita colisão entre plataformas (IG, YouTube, etc.)

Referência: §07-§08 do Documento Mestre v3.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Offset fixo: Brasil sem horário de verão desde 2019.
TZ_BRT = timezone(timedelta(hours=-3))


def _now_brt() -> datetime:
    """Datetime atual em BRT."""
    return datetime.now(timezone.utc).astimezone(TZ_BRT)


def _now_iso() -> str:
    """Datetime ISO atual em BRT."""
    return _now_brt().isoformat()


# ---------------------------------------------------------------------------
# Namespaces de plataforma
# ---------------------------------------------------------------------------

NAMESPACES_VALIDOS = frozenset({
    "ig",      # Instagram
    "yt",      # YouTube
    "fb",      # Facebook
    "wa",      # WhatsApp
    "tiktok",  # TikTok
    "email",   # e-mail
    "phone",   # telefone
    "web",     # origem web
})


# Mapeamento plataforma -> abreviação de namespace.
_PLATAFORMA_PARA_NAMESPACE: dict[str, str] = {
    "instagram": "ig",
    "youtube": "yt",
    "facebook": "fb",
    "fb": "fb",
    "whatsapp": "wa",
    "wa": "wa",
    "tiktok": "tiktok",
    "email": "email",
    "phone": "phone",
    "web": "web",
}


def formatar_namespace(plataforma: str, id_externo: str) -> str:
    """Formata o identificador completo com namespace.

    Exemplo: "ig:48291039252", "yt:UCx123456"
    Evita colisão entre plataformas: o mesmo id_externo em plataformas diferentes
    recebe namespaces diferentes.
    """
    ns = _PLATAFORMA_PARA_NAMESPACE.get(plataforma.lower().strip(), plataforma.lower().strip())
    return f"{ns}:{id_externo}"


def parsear_namespace(namespace_id: str) -> tuple[str, str]:
    """Separa namespace e id_externo. Devolve (plataforma, id_externo)."""
    if ":" in namespace_id:
        parts = namespace_id.split(":", 1)
        return parts[0], parts[1]
    # Sem namespace: assume Instagram por convenção.
    return "ig", namespace_id


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Identidade:
    """Identificador único interno + IDs externos com namespace.

    O `id_interno` (UUID v4) é o ponto de ancoragem para todo o restante
    do modelo — estável enquanto o lead existir. `id_externo` pode mudar
    (conta nova, plataforma diferente); `id_interno` não.

    CPF, e-mail, telefone etc. NÃO são campos deste modelo: são metadados
    no vínculo, nunca expostos sem o hash.
    """

    id_interno: str          # UUID v4 — estável por vida do lead
    plataforma: str          # "instagram", "youtube", etc.
    id_externo: str          # IGSID do comentário/DM/etc.
    namespace_id: str        # namespace do externo (evita colisão entre plataformas)
    criado_em: str           # ISO datetime BRT
    atualizado_em: str       # ISO datetime BRT

    @classmethod
    def criar(
        cls,
        plataforma: str,
        id_externo: str,
    ) -> "Identidade":
        """Factory: cria identidade nova com UUID e timestamp."""
        agora = _now_iso()
        return cls(
            id_interno=str(uuid.uuid4()),
            plataforma=plataforma,
            id_externo=id_externo,
            namespace_id=formatar_namespace(plataforma, id_externo),
            criado_em=agora,
            atualizado_em=agora,
        )

    def to_dict(self) -> dict[str, str]:
        """Serialização para armazenamento (nunca expõe dado cru em log)."""
        return {
            "id_interno": self.id_interno,
            "plataforma": self.plataforma,
            "id_externo": self.id_externo,
            "namespace_id": self.namespace_id,
            "criado_em": self.criado_em,
            "atualizado_em": self.atualizado_em,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Identidade":
        """Desserialização a partir de registro do banco."""
        return cls(
            id_interno=str(data["id_interno"]),
            plataforma=str(data["plataforma"]),
            id_externo=str(data["id_externo"]),
            namespace_id=str(data["namespace_id"]),
            criado_em=str(data["criado_em"]),
            atualizado_em=str(data["atualizado_em"]),
        )


@dataclass
class Vinculo:
    """Vínculo entre identidade e responsável financeiro.

    O `documento` é guardado como SHA-256 do valor original — o hash é irreversível
    e permite deduplicação sem expor o documento limpo. Em nenhum lugar do código
    ou log o CPF aparece em texto.

    Tipos de vínculo:
      - cliente_educacional     → pessoa que consome o conteúdo/curso
      - responsavel_financeiro  → pessoa que financia a compra
      - responsavel_legal       → responsável por menor de idade
    """

    id_interno: str              # ref para Identidade.id_interno
    tipo: str                     # "cliente_educacional", "responsavel_financeiro", etc.
    documento_hash: str           # SHA-256 do documento (nunca o documento limpo)
    plataforma_origem: str        # de onde veio a identificação ("instagram", "blu")
    verificado_em: Optional[str]  # ISO datetime — None se não verificado
    fonte_verificacao: Optional[str]  # "clint", "educzz", "lia", etc.
    metadata: dict[str, Any]      # dados crus da fonte (SEM PII exposto)

    def verificado(self) -> bool:
        """O vínculo foi verificado por alguma fonte?"""
        return bool(self.verificado_em)

    def to_dict(self) -> dict[str, Any]:
        """Serialização para armazenamento (nunca expõe documento)."""
        return {
            "id_interno": self.id_interno,
            "tipo": self.tipo,
            "documento_hash": self.documento_hash,
            "plataforma_origem": self.plataforma_origem,
            "verificado_em": self.verificado_em,
            "fonte_verificacao": self.fonte_verificacao,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Vinculo":
        """Desserialização a partir de registro do banco."""
        return cls(
            id_interno=str(data["id_interno"]),
            tipo=str(data["tipo"]),
            documento_hash=str(data["documento_hash"]),
            plataforma_origem=str(data["plataforma_origem"]),
            verificado_em=str(data["verificado_em"]) if data.get("verificado_em") else None,
            fonte_verificacao=str(data["fonte_verificacao"]) if data.get("fonte_verificacao") else None,
            metadata=data.get("metadata") or {},
        )


# ---------------------------------------------------------------------------
# Utilitários de hash (nunca expostos como API pública)
# ---------------------------------------------------------------------------

def hash_documento(documento: str) -> str:
    """Gera hash SHA-256 irreversível de um documento (CPF, CNPJ, etc.).

    Uso interno: este hash é o ÚNICO formato em que o documento existe no banco.
    O documento limpo jamais aparece em storage, log ou resposta de API.
    """
    return hashlib.sha256(documento.strip().encode("utf-8")).hexdigest()


def verificar_documento(documento: str, hash_esperado: str) -> bool:
    """Verifica se um documento limpo corresponde a um hash armazenado.

    Usado para CONFIRMAR vínculo existente — nunca para buscar.
    """
    return hashlib.sha256(documento.strip().encode("utf-8")).hexdigest() == hash_esperado
