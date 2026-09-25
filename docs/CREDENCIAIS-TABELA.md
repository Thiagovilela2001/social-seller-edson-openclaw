<!-- GERADO por tools/checklist_credenciais.py — NAO editar a mao. -->
# Tabela de credenciais

Fonte unica: `capacidades.py`. Regerar com
`python tools/checklist_credenciais.py --write`.

> **Ter a credencial NAO libera a capacidade.** A escada da §02 continua valendo:
> `configurada` e diferente de `liberada`. Falta a leitura implementada e a
> homologacao contra o recurso autorizado.

## Resumo

- capacidades declaradas: **37**
- liberadas: **0**
- variaveis de credencial mapeadas: **15**
- capacidades sem credencial mapeada: **11** (nao dependem de fornecedor externo)

## Variaveis

| Variavel | Familias | O que ela destrava |
|---|---|---|
| `BIGDATA_CONNECTION` | comercio_logistica | `assiny.consultar_venda` |
| `BLING_API_TOKEN` | comercio_logistica, financeiro | `bling.consultar_pedido`, `bling.consultar_rastreio`, `bling.evidencia_pagamento` |
| `CLINT_MCP_URL` | identidade_crm | `clint.contexto_do_cliente`, `clint.vinculo_do_cliente` |
| `EDUZZ_API_KEY` | financeiro | `eduzz.consultar_faturas` |
| `EMAIL_SMTP_URL` | canal | `email.enviar` |
| `IG_ACCESS_TOKEN` | canal | `instagram.enviar_dm`, `instagram.private_reply`, `instagram.responder_comentario` |
| `IG_USER_ID` | canal | `instagram.enviar_dm`, `instagram.private_reply`, `instagram.responder_comentario` |
| `LIA_API_TOKEN` | financeiro | `lia.consultar_financiamento`, `lia.consultar_parcela`, `lia.obter_segunda_via`, `lia.verificar_renegociacao` |
| `TIKTOK_SHOP_ACCESS_TOKEN` | canal, comercio_logistica | `tiktok_shop.consultar_conversa`, `tiktok_shop.consultar_pedido`, `tiktok_shop.responder_chat` |
| `TIKTOK_SHOP_APP_KEY` | canal, comercio_logistica | `tiktok_shop.consultar_conversa`, `tiktok_shop.consultar_pedido`, `tiktok_shop.responder_chat` |
| `WHATSAPP_PHONE_ID` | canal | `whatsapp.enviar` |
| `WHATSAPP_TOKEN` | canal | `whatsapp.enviar` |
| `YAMPI_API_TOKEN` | comercio_logistica | `yampi.consultar_pedido` |
| `YOUTUBE_API_KEY` | canal | `youtube.listar_comentarios` |
| `YOUTUBE_OAUTH_TOKEN` | canal | `youtube.live_enviar`, `youtube.live_moderar`, `youtube.live_receber`, `youtube.moderar_comentario`, `youtube.responder_comentario` |

## Sem credencial mapeada

Nao dependem de fornecedor externo (ou sao do proprio motor):

- `controle.avaliar_elegibilidade`
- `controle.consultar_resultado_acao`
- `controle.registrar_pendencia`
- `controle.reservar_contato`
- `langfuse.exportar`
- `meta.excluir_comentario`
- `meta.ocultar_comentario`
- `meta.reexibir_comentario`
- `rag.buscar`
- `rag.oferta_vigente`
- `rag.registrar_lacuna`
