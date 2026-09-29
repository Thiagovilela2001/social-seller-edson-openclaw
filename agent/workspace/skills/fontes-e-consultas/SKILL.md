---
name: fontes-e-consultas
description: "Quando usar cada fonte de dados e como interpretar respostas"
version: 1.0.0
author: "Gian — [SUA EMPRESA]"
license: Commercial
---

# Fontes de dados — quando usar cada uma

Conecta cada pergunta da pessoa à fonte certa e interpreta a resposta corretamente.
A parte de conversa está na skill `social-seller-edson`.

## When to Use

- Preciso saber status de pedido/pagamento.
- Preciso saber se a pessoa já é cliente.
- Preciso saber histórico de interações.
- Preciso saber dados de uma venda.
- A pessoa pergunta "onde está meu pedido?" ou "já paguei?".
- Alguém afirma ter comprado e eu preciso verificar.

**Não use para:** decidir oferta, preço ou tom de conversa (skill `social-seller-edson`).

## Prerequisites

- Ferramentas de consulta às fontes configuradas (`integracoes.py`).
- Capacidades registradas em `capacidades.py`.
- Políticas de resposta fail-closed entendidas.

## Procedure — fonte certa para cada pergunta

1. **Identifique o que a pessoa quer saber.**
2. **Selecione a fonte correta** (ver Quick Reference abaixo).
3. **Consulte a fonte.** Nunca invente, nunca estimule.
4. **Interprete o resultado:**
   - Sucesso → usar o dado
   - `FonteIndisponivel` → "Não consigo ver isso daqui. Passo pro time?"
   - Retorno vazio → tratar como "não existe ou não pude ver"
   - Incerteza → nunca afirmar; escalar para humano
5. **Responda com o dado ou encamine.**

Critério de conclusão: toda resposta sobre status tem fonte identificada, e toda
indisponibilidade resulta em encaminhamento — nunca em invenção.

## Quick Reference — mapa de fontes

| O que a pessoa pergunta | Fonte | Como consultar | Se indisponível |
|---|---|---|---|
| Status do pedido | Bling | `bling.consultar_pedido` | "Não consigo ver. Passo pro time?" |
| Rastreio | Bling | `bling.consultar_rastreio` | "Não tenho como rastrear. Passo pro time?" |
| Confirmação de pagamento | Bling | `bling.evidencia_pagamento` | "Não consigo confirmar. Passo pro time?" |
| Sou cliente? | Clint + Bling | `clint.vinculo_do_cliente` | Perguntar como comprou |
| Histórico WhatsApp | Clint | `clint.contexto_do_cliente` | "Não tenho acesso ao histórico." |
| Pedido Yampi | Yampi | `yampi.consultar_pedido` | "Qual o e-mail da compra?" |
| Status pagamento Yampi | Yampi | `yampi.status_pagamento` | "Posso verificar na plataforma." |
| Recorrência Eduzz | Eduzz | `eduzz.consultar_assinatura` | "Você pode ver na área do aluno." |
| Status recorrência | Eduzz | `eduzz.status_recorrencia` | "Posso verificar na plataforma." |
| Fatura LIA | LIA | `lia.consultar_fatura` | "Passo pro time financeiro." |
| Parcelas LIA | LIA | `lia.consultar_parcela` | "Passo pro time financeiro." |
| Venda Assiny | **BLOQUEADO** | — | **Nunca afirmar. Bloqueado por §26 do mestre.** |

## Como interpretar cada resposta

### Bling
- `pedido.status = "finished"` ≠ `parcelas_pagas`. São dois estados diferentes.
- Pedido criado ≠ pago. Só `pagamento_confirmado` significa pagamento.
- Rastreio disponível só depois de envio confirmado.

### Clint
- Histórico de WhatsApp é só **leitura**. Nunca escrever no histórico.
- `vinculo_do_cliente` retorna o vínculo entre conta social e cliente validado.
- Sem vínculo verificado: tratar como pessoa, não como cliente.

### Yampi
- Pedido Yampi criado no checkout ≠ pago.
- `status_pagamento` é a fonte de verdade para confirmação.
- Verificar e-mail do cliente para buscar pedido.

### Eduzz
- Assinatura ativa ≠ última parcela paga.
- `status_recorrencia` diz se está em dia.
- Área do aluno é a referência para o cliente.

### LIA
- Fatura paga ≠ recorrência quitada.
- `consultar_fatura` mostra parcelas individuais.
- Time financeiro responde por negociação de parcelas.

### Assiny (BLOQUEADO)
> **Nunca implemente.** O Documento Mestre v3 §26 é explícito: provedor, dataset,
> chaves e frequência são **desconhecidos**. Qualquer implementação seria adivinhação.

## Fail-closed — nunca fazer

- **Nunca fabricar dado.** "Provavelmente já saiu" é mentira.
- **Nunca estimar prazo.** "Deve chegar em 5 dias" não existe.
- **Nunca projetar pagamento.** "Você deve ter pago" não existe.
- **Nunca assumir.** Perguntar "como você pagou?" abre a fonte certa.

## Semântica por fonte — o que cada uma realmente responde

| Fonte | O que responde | O que NÃO responde |
|---|---|---|
| Bling | Status do pedido, rastreio | Se o cliente está satisfeito |
| Clint | Vínculo, contexto histórico | Detalhes de produtos |
| Yampi | Pedido Yampi, pagamento | Pedidos de outras plataformas |
| Eduzz | Assinatura Eduzz | Assinatura de outras plataformas |
| LIA | Faturas e parcelas | Histórico de compras |
| Assiny | **NADA** | **QUALQUER COISA — BLOQUEADO** |

## Quando escalar para humano

- Fonte indisponível + pessoa em desespero (crise, urgência).
- Informação contraditória (cliente diz que pagou; fonte não confirma).
- Múltiplas fontes possíveis e não sei qual usar.
- Dado que pode indicar fraude ou roubo de identidade.

## Pitfalls

- **Blending de fontes.** "Pedido" no Bling não é "pedido" no Yampi. Cada fonte
  tem seu modelo. Não misture.
- **Credential ≠ capability.** Token no .env não significa que a leitura existe.
  Verifique `CAPACIDADE_IMPLEMENTADA()`.
- **Assiny.** A tentação de "implementar só o básico" é alta. Não ceda. O §26
  do mestre é claro: provedor desconhecido = não implementar.
- **"Não existe" vs "não vi".** A fonte returning vazio significa "não achei
  OU não pude ver". Nunca trate como "não existe".

## Verification

- Toda afirmação sobre status tem fonte identificada?
- Indisponibilidade resulta em encaminhamento, não em invenção?
- Nenhuma afirmação sobre Assiny foi feita?
- A semântica de cada fonte foi respeitada (finished ≠ pago)?
