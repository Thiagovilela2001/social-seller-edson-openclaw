#!/usr/bin/env python3
"""Espinha dorsal de capacidades e contrato de ferramentas — Documento Mestre v3.0.

POR QUE ESTE ARQUIVO EXISTE
    O mestre repete uma escada que e a diferenca entre um projeto honesto e um
    projeto que promete:

        API existente != acesso concedido != ferramenta implementada
        != dado consultado != acao autorizada != producao liberada

    Texto assim vira promessa se nao virar estrutura. Aqui ele vira estrutura: o
    nivel de cada capacidade e declarado item por item, e **nada e liberado por
    omissao**. Capacidade sem nivel declarado nao esta liberada.

    E o mesmo padrao que o motor ja usa em `integracoes.py` (fail-closed) — mas
    com a escada explicita, porque o mestre exige distinguir "tem token" de
    "consultei o recurso".

O QUE ESTE ARQUIVO NAO E
    Nao e adaptador. Nao conhece endpoint, payload nem credencial de fornecedor.
    As operacoes declaradas aqui sao **contratos propostos** — nenhuma tem
    endpoint confirmado, e o mestre proibe inventar um. Quem implementar um
    adaptador preenche niveis; nao inventa nome de campo.

    Tambem nao e fonte de verdade paralela: as capacidades que o motor ja declara
    sao LIDAS de `engine/instagram_seller/integracoes.py`, nao copiadas.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENGINE = RAIZ / "engine" / "instagram_seller"


class ContratoInvalido(ValueError):
    """Retorno ou contexto fora do contrato. Levantado antes de qualquer efeito."""


class CapacidadeIndisponivel(PermissionError):
    """A capacidade nao esta liberada. Levantada em vez de devolver dado vazio.

    Devolver vazio seria indistinguivel de "nao existe" — e o agente diria ao
    cliente que o pedido dele nao existe. Mesma licao do `FonteIndisponivel` do
    motor.
    """


# ---------------------------------------------------------------------------
# A escada da §02 — ordem importa
# ---------------------------------------------------------------------------

NIVEIS: tuple[str, ...] = (
    "api_existente",
    "acesso_concedido",
    "ferramenta_implementada",
    "dado_consultado",
    "acao_autorizada",
    "producao_liberada",
)

# Familias logicas do contrato de ferramentas (§10).
FAMILIAS: tuple[str, ...] = (
    "conhecimento",
    "identidade_crm",
    "comercio_logistica",
    "financeiro",
    "canal",
    "controle",
    "observabilidade",
)


@dataclass(frozen=True)
class Capacidade:
    familia: str
    descricao: str
    niveis: frozenset[str] = frozenset()
    variaveis: tuple[str, ...] = ()

    def validar(self) -> None:
        """A escada e cumulativa: nao se autoriza acao sem antes ter consultado."""
        if self.familia not in FAMILIAS:
            raise ContratoInvalido(f"familia desconhecida: {self.familia!r}")
        if not self.descricao.strip():
            raise ContratoInvalido("capacidade sem descricao")
        desconhecidos = self.niveis - set(NIVEIS)
        if desconhecidos:
            raise ContratoInvalido(f"nivel desconhecido: {sorted(desconhecidos)}")
        if self.niveis:
            atingidos = [i for i, n in enumerate(NIVEIS) if n in self.niveis]
            # Sem buraco: se "acao_autorizada" esta marcada, todos os anteriores tambem.
            if atingidos != list(range(len(atingidos))):
                raise ContratoInvalido(
                    "escada com buraco: "
                    f"{sorted(self.niveis)} — niveis anteriores obrigatorios"
                )

    def configurada(self) -> bool:
        """A credencial existe no ambiente? Isso NAO libera nada (licao do F03)."""
        return any((os.getenv(v) or "").strip() for v in self.variaveis)

    def liberada(self) -> bool:
        return self.niveis == set(NIVEIS)

    def estado(self) -> dict:
        return {
            "familia": self.familia,
            "niveis": [n for n in NIVEIS if n in self.niveis],
            "proximo_nivel": next((n for n in NIVEIS if n not in self.niveis), None),
            "configurada": self.configurada(),
            "liberada": self.liberada(),
        }


# ---------------------------------------------------------------------------
# Capacidades que o motor JA declara — lidas, nunca copiadas
# ---------------------------------------------------------------------------

def _capacidades_do_motor() -> dict[str, bool]:
    """Le o registro do motor. Nao copia: fonte unica para as chaves que ja existem."""
    if str(ENGINE) not in sys.path:
        sys.path.insert(0, str(ENGINE))
    import integracoes  # noqa: PLC0415

    return dict(integracoes.CAPACIDADES)


def _da_motor(nome: str, implementada: bool, familia: str, descricao: str) -> Capacidade:
    """Traduz o booleano do motor para a escada.

    `True` no motor significa "existe leitura implementada" — nao significa que a
    fonte foi consultada nem que a acao foi autorizada. Por isso o teto aqui e
    `ferramenta_implementada`.
    """
    niveis = frozenset(NIVEIS[:3]) if implementada else frozenset()
    return Capacidade(familia=familia, descricao=descricao, niveis=niveis)


def _registro() -> dict[str, Capacidade]:
    do_motor = _capacidades_do_motor()
    descricoes_motor = {
        "bling.consultar_pedido": ("comercio_logistica", "Pedidos do cliente validado (ERP)"),
        "bling.consultar_rastreio": ("comercio_logistica", "Rastreio de remessa"),
        "bling.evidencia_pagamento": ("financeiro", "Evidencia de pagamento vinculada"),
        "clint.vinculo_do_cliente": ("identidade_crm", "Vinculo autorizado conta social/cliente"),
        "clint.contexto_do_cliente": ("identidade_crm", "Contexto pertinente do cliente"),
        "whatsapp.enviar": ("canal", "Envio por WhatsApp elegivel"),
        "email.enviar": ("canal", "Envio por e-mail permitido"),
        "meta.ocultar_comentario": ("canal", "Ocultar comentario (moderacao)"),
        "meta.excluir_comentario": ("canal", "Excluir comentario (moderacao)"),
        "meta.reexibir_comentario": ("canal", "Reexibir comentario (reversao)"),
    }

    registro: dict[str, Capacidade] = {}

    # 1. O que o motor ja declara.
    for nome, implementada in do_motor.items():
        familia, descricao = descricoes_motor.get(nome, ("controle", "capacidade do motor"))
        registro[nome] = _da_motor(nome, implementada, familia, descricao)

    # 2. O que a v3 acrescenta — tudo PROPOSTO, nada implementado, nada liberado.
    novas = {
        # --- canal: Instagram (o unico com ferramenta de verdade) -------------
        "instagram.responder_comentario": ("canal", "Resposta publica a comentario"),
        "instagram.enviar_dm": ("canal", "DM dentro da janela permitida"),
        "instagram.private_reply": ("canal", "Resposta privada a comentario, cota unica"),
        # --- canal: YouTube ---------------------------------------------------
        "youtube.listar_comentarios": ("canal", "Listar threads de comentarios (Data API)"),
        "youtube.responder_comentario": ("canal", "Responder comentario autorizado"),
        "youtube.moderar_comentario": ("canal", "Aplicar status de moderacao"),
        "youtube.live_receber": ("canal", "Receber chat ao vivo"),
        "youtube.live_enviar": ("canal", "Publicar no chat da live"),
        "youtube.live_moderar": ("canal", "Remover mensagem ou aplicar sançao"),
        # --- canal: TikTok Shop ----------------------------------------------
        "tiktok_shop.consultar_conversa": ("canal", "Conversa de atendimento da loja"),
        "tiktok_shop.responder_chat": ("canal", "Resposta no chat da loja"),
        "tiktok_shop.consultar_pedido": ("comercio_logistica", "Estado do pedido no marketplace"),
        # --- conhecimento ----------------------------------------------------
        "rag.buscar": ("conhecimento", "Busca na RAG aprovada"),
        "rag.oferta_vigente": ("conhecimento", "Oferta vigente por produto/campanha"),
        "rag.registrar_lacuna": ("conhecimento", "Registrar pergunta sem resposta na base"),
        # --- financeiro restrito ---------------------------------------------
        "lia.consultar_parcela": ("financeiro", "Parcela/fatura do financiamento"),
        "lia.consultar_financiamento": ("financeiro", "Estado do contrato de financiamento"),
        "lia.verificar_renegociacao": ("financeiro", "Substituicao/renegociacao de parcelas"),
        "lia.obter_segunda_via": ("financeiro", "Segunda via existente da parcela vigente"),
        "eduzz.consultar_faturas": ("financeiro", "Faturas do contrato recorrente"),
        "yampi.consultar_pedido": ("comercio_logistica", "Pedido e transacoes na origem"),
        "assiny.consultar_venda": ("comercio_logistica", "Venda Assiny na visao do BigData"),
        # --- controle ---------------------------------------------------------
        "controle.avaliar_elegibilidade": ("controle", "Elegibilidade de contato por finalidade"),
        "controle.reservar_contato": ("controle", "Reserva do toque antes do envio"),
        "controle.consultar_resultado_acao": ("controle", "Desfecho de uma acao proposta"),
        "controle.registrar_pendencia": ("controle", "Pendencia rastreavel para reconciliacao"),
        # --- observabilidade --------------------------------------------------
        "langfuse.exportar": ("observabilidade", "Telemetria filtrada (nao autoriza nada)"),
    }
    for nome, (familia, descricao) in novas.items():
        registro[nome] = Capacidade(familia=familia, descricao=descricao)

    # Variaveis que CONFIGURAM cada familia — separadas da escada de proposito.
    substituicoes = {
        "bling.consultar_pedido": ("BLING_API_TOKEN",),
        "bling.consultar_rastreio": ("BLING_API_TOKEN",),
        "bling.evidencia_pagamento": ("BLING_API_TOKEN",),
        "clint.vinculo_do_cliente": ("CLINT_MCP_URL",),
        "clint.contexto_do_cliente": ("CLINT_MCP_URL",),
        "whatsapp.enviar": ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID"),
        "email.enviar": ("EMAIL_SMTP_URL",),
        "instagram.enviar_dm": ("IG_ACCESS_TOKEN", "IG_USER_ID"),
        "instagram.responder_comentario": ("IG_ACCESS_TOKEN", "IG_USER_ID"),
        "instagram.private_reply": ("IG_ACCESS_TOKEN", "IG_USER_ID"),
        "youtube.listar_comentarios": ("YOUTUBE_API_KEY",),
        "youtube.responder_comentario": ("YOUTUBE_OAUTH_TOKEN",),
        "youtube.moderar_comentario": ("YOUTUBE_OAUTH_TOKEN",),
        "youtube.live_receber": ("YOUTUBE_OAUTH_TOKEN",),
        "youtube.live_enviar": ("YOUTUBE_OAUTH_TOKEN",),
        "youtube.live_moderar": ("YOUTUBE_OAUTH_TOKEN",),
        "tiktok_shop.consultar_conversa": ("TIKTOK_SHOP_APP_KEY", "TIKTOK_SHOP_ACCESS_TOKEN"),
        "tiktok_shop.responder_chat": ("TIKTOK_SHOP_APP_KEY", "TIKTOK_SHOP_ACCESS_TOKEN"),
        "tiktok_shop.consultar_pedido": ("TIKTOK_SHOP_APP_KEY", "TIKTOK_SHOP_ACCESS_TOKEN"),
        "lia.consultar_parcela": ("LIA_API_TOKEN",),
        "lia.consultar_financiamento": ("LIA_API_TOKEN",),
        "lia.verificar_renegociacao": ("LIA_API_TOKEN",),
        "lia.obter_segunda_via": ("LIA_API_TOKEN",),
        "eduzz.consultar_faturas": ("EDUZZ_API_KEY",),
        "yampi.consultar_pedido": ("YAMPI_API_TOKEN",),
        "assiny.consultar_venda": ("BIGDATA_CONNECTION",),
    }
    for nome, variaveis in substituicoes.items():
        if nome in registro:
            base = registro[nome]
            registro[nome] = Capacidade(
                familia=base.familia,
                descricao=base.descricao,
                niveis=base.niveis,
                variaveis=variaveis,
            )

    for cap in registro.values():
        cap.validar()

    return registro


CAPACIDADES: dict[str, Capacidade] = _registro()


# ---------------------------------------------------------------------------
# Guarda de uso
# ---------------------------------------------------------------------------

def exigir_capacidade(nome: str) -> Capacidade:
    """Levanta se a capacidade nao estiver no topo da escada."""
    cap = CAPACIDADES.get(nome)
    if cap is None:
        raise CapacidadeIndisponivel(f"capacidade desconhecida: {nome!r}")
    if not cap.liberada():
        faltam = [n for n in NIVEIS if n not in cap.niveis]
        raise CapacidadeIndisponivel(
            f"{nome} nao liberada — falta: {', '.join(faltam)}"
        )
    return cap


def status_integracoes() -> dict:
    """Retrato honesto para o briefing e para o handover. Nada aqui e permissao."""
    return {
        "total": len(CAPACIDADES),
        "liberadas": sum(1 for c in CAPACIDADES.values() if c.liberada()),
        "configuradas_sem_liberacao": sum(
            1 for c in CAPACIDADES.values() if c.configurada() and not c.liberada()
        ),
        "por_familia": {
            fam: sum(1 for c in CAPACIDADES.values() if c.familia == fam) for fam in FAMILIAS
        },
    }


# ---------------------------------------------------------------------------
# Contrato de retorno (§10) — status fechado, evidencia e frescor obrigatorios
# ---------------------------------------------------------------------------

STATUS: tuple[str, ...] = (
    "sucesso",
    "ausencia",
    "ambiguidade",
    "sem_permissao",
    "indisponivel",
    "desatualizado",
    "resultado_incerto",
)

# Os unicos status em que o agente pode afirmar algo ao cliente.
STATUS_COM_AFIRMACAO = frozenset({"sucesso"})

# §09: "Consultar agora um dado importado ontem nao o torna atual."
CAMPOS_OBRIGATORIOS_NO_SUCESSO = ("fonte", "evidence_id", "consultado_em", "source_updated_at")


@dataclass(frozen=True)
class Resultado:
    status: str
    fonte: str = ""
    evidence_id: str = ""
    escopo: str = ""
    consultado_em: str = ""
    source_updated_at: str = ""
    ingested_at: str = ""
    valor: dict | None = None

    def validar(self) -> None:
        if self.status not in STATUS:
            raise ContratoInvalido(
                f"status fora do contrato: {self.status!r}. Validos: {list(STATUS)}"
            )
        if self.status in STATUS_COM_AFIRMACAO:
            faltando = [c for c in CAMPOS_OBRIGATORIOS_NO_SUCESSO if not getattr(self, c)]
            if faltando:
                raise ContratoInvalido(
                    f"status 'sucesso' sem {', '.join(faltando)} — "
                    "afirmacao exige fonte, evidencia e horario"
                )

    def pode_afirmar(self) -> bool:
        self.validar()
        return self.status in STATUS_COM_AFIRMACAO

    def recusa_com_dado_vazio(self) -> bool:
        """Retorno de falha NAO pode carregar valor — vazio e indistinguivel de ausencia."""
        self.validar()
        return self.status not in STATUS_COM_AFIRMACAO and self.valor is not None


# ---------------------------------------------------------------------------
# Contexto vinculado no servidor (§10) — o modelo nao escolhe destinatario
# ---------------------------------------------------------------------------

CAMPOS_DO_CONTEXTO = (
    "execution_id",
    "conta",
    "case_id",
    "finalidade",
    "recurso_permitido",
    "acao_aprovada",
)


@dataclass(frozen=True)
class ContextoExecucao:
    execution_id: str
    conta: str
    case_id: str
    finalidade: str
    recurso_permitido: str
    acao_aprovada: str
    identidade_verificada: bool = False

    def validar(self) -> None:
        faltando = [c for c in CAMPOS_DO_CONTEXTO if not str(getattr(self, c)).strip()]
        if faltando:
            raise ContratoInvalido(
                f"contexto incompleto: {', '.join(faltando)} — "
                "o servidor vincula, o modelo nao escolhe"
            )
        if not self.identidade_verificada:
            raise ContratoInvalido(
                "identidade nao verificada: nenhuma acao vinculada a pessoa sem vinculo"
            )


def exigir_contexto(ctx: ContextoExecucao | None) -> ContextoExecucao:
    if ctx is None:
        raise ContratoInvalido("contexto ausente: a ferramenta exige entrada vinculada")
    ctx.validar()
    return ctx


# ---------------------------------------------------------------------------
# Dinheiro (§08) — centavos inteiros, nunca ponto flutuante
# ---------------------------------------------------------------------------

def centavos(valor: object) -> int:
    """Valida dinheiro como inteiro de centavos.

    §08: "Usar centavos inteiros ou decimal exato para dinheiro, nunca
    arredondamento livre do modelo." `float` e recusado de proposito: 0.1 + 0.2
    nao e 0.3, e dinheiro nao aceita esse tipo de surpresa.
    """
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ContratoInvalido(
            f"dinheiro deve ser inteiro de centavos, recebido {type(valor).__name__}"
        )
    return valor


def registrar_pendencia(capacidade: str, motivo: str, *, case_id: str = "") -> dict:
    """Pendencia rastreavel — 'falhar fechado' nao pode virar perder evento.

    §12: "Falhar fechado significa impedir o efeito arriscado e registrar a
    pendencia. Nao significa perder eventos, silenciar todos os clientes ou
    impedir ajuda simples."
    """
    if capacidade not in CAPACIDADES:
        raise CapacidadeIndisponivel(f"capacidade desconhecida: {capacidade!r}")
    if not motivo.strip():
        raise ContratoInvalido("pendencia sem motivo")
    return {
        "capacidade": capacidade,
        "motivo": motivo.strip(),
        "case_id": case_id,
        "estado": CAPACIDADES[capacidade].estado(),
    }


if __name__ == "__main__":  # pragma: no cover - inspeção manual
    import json

    print(json.dumps(status_integracoes(), ensure_ascii=False, indent=2))
    for nome, cap in sorted(CAPACIDADES.items()):
        marca = "LIBERADA" if cap.liberada() else "fechada"
        print(f"  {nome:<40} {cap.familia:<20} {marca}")
