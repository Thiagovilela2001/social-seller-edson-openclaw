---
name: modelo-dados
description: "Entidades do sistema: pessoa, cliente, vínculo, pedido, fatura"
version: 1.0.0
author: "Gian — [SUA EMPRESA]"
license: Commercial
---

# Modelo de dados — as entidades do sistema

Traduz o mundo real em entidades que o sistema conhece. Quem eu falo é uma `pessoa`.
Quem pagou é um `cliente`. Quem interage no Instagram é um `vínculo`. Quem comprou
tem um `pedido`. A parte de venda e conversa está na skill `social-seller-edson`.

## When to Use

- Preciso entender com quem estou falando (pessoa vs cliente).
- Preciso saber se posso afirmar algo sobre essa pessoa.
- Preciso distinguir interações de transações.
- A pessoa pergunta algo que depende de dados do sistema.

**Não use para:** decidir oferta, tom ou follow-up (skill `social-seller-edson`).

## Modelo de dados simplificado

```
pessoa
├── id (canal:identificador — ex: instagram:123456789)
├── username (mutável — atributo, NÃO chave)
├── etapa (curioso → interessado → lead_quente → cliente)
└── flags (crise, menor, opt_out, sensible)

vínculo
├── pessoa_id
├── fonte (instagram, youtube, tiktok, whatsapp, email)
├── identificador_externo (igsid, canal_id, etc.)
├── verificado_em (timestamp)
└── método (comentário, DM, botão_whatsapp, email)

cliente
├── pessoa_id
├── vínculo_verificado (bool — conta social ligada a titular?)
├── data_primeira_compra
├── fonte_pagamento (yampi, eduzz, lIA, tiktok)
└── status (ativo, cancelado, inadimplente, пробlen)

pedido
├── cliente_id
├── fonte (bling, yampi, eduzz, tiktok)
├── external_id (ID no sistema da fonte)
├── status (criado, pago, enviado, entregue, cancelado)
├── data_criacao
└── valor_total

fatura (LIA)
├── cliente_id
├── external_id
├── status (pendente, paga, vencida, cancelada)
├── data_vencimento
├── valor_original
├── valor_pago
└── parcelas (lista de parcelas)

pagamento
├── pedido_id
├── fonte (yampi, eduzz, lIA, tiktok)
├── status (pendente, confirmado, estornado, falhado)
├── metodo (cartão, pix, boleto)
├── data_pagamento
└── valor
```

## pessoa ≠ cliente — a distinção central

| Conceito | Significado | O que NÃO significa |
|---|---|---|
| **pessoa** | Alguma vez interagiu comigo | Que comprou |
| **cliente** | Pagou E vínculo verificado | Que só interagiu |
| **lead** | Pessoa em qualificação | Não é tipo de dados, é etapa |

**Exemplo:** Uma pessoa que comentou 50 vezes mas nunca comprou continua sendo `pessoa`.
Uma pessoa que comprou mas não tem vínculo verificado é `cliente` sem `vínculo_verificado`.

## Etapas do funil

```
curioso (0–24 pontos)
    ↓ 2+ sinais fortes
interessado (25–54 pontos)
    ↓ 2+ sinais fortes
lead_quente (55–79 pontos)
    ↓ pagamento confirmado
cliente (80–100 pontos)
```

### Sinais fortes (+25 a +40)
- Clicou no checkout (+40)
- Abandonou checkout (+35)
- Pediu o link (+30)
- Perguntou preço (+25)
- Comenta palavra-chave de compra (+25)

### Sinais médios (+10 a +20)
- Descreveu dor concreta (+20)
- Indicou prazo (+20)
- Perguntou de pagamento (+15)
- Voltou a falar sozinho (+15)

### Sinais fracos (+5)
- Segue a conta
- Reagiu com emoji
- Engajamento repetido

### Sinais negativos
- "Vou pensar" 2× (−15)
- 3 toques sem resposta (−30)
- "Não tenho interesse" (−50)

## Vínculo — a entidade mais importante

O vínculo conecta uma conta social a uma pessoa real validada.

```
Sem vínculo: pessoa interage, mas não sei se é cliente.
Com vínculo: pessoa interage E comprovou ser o titular.
```

### Quando o vínculo existe
- Resposta de story com e-mail verificado
- Compra confirmada com dados que casam
- Botão WhatsApp clicado (consentimento)
- DM com dados que validam identidade

### Quando o vínculo NÃO existe
- Comentário anônimo
- Primeiro DM sem dados verificáveis
- Interação sem confirmação de titularidade

### Por que o vínculo importa
- **Sem vínculo:** não posso afirmar que é cliente.
- **Com vínculo:** posso consultar o histórico do cliente.
- **Vínculo fraco:** posso ajudar, mas não afirmo dados financeiros.

## Pedido — estados e semântica

| Status | Significado | O que NÃO significa |
|---|---|---|
| `criado` | Checkout iniciado | Que pagou |
| `pago` | Pagamento confirmado | Que enviou |
| `enviado` | Remessa criada | Que entregou |
| `entregue` | Rastreio confirma entrega | Que está satisfeito |
| `cancelado` | Pedido cancelado | Que não comprou mais |

### Fontes de pedido
- **Bling:** pedidos de e-commerce e remessas
- **Yampi:** checkout e pagamento da plataforma
- **Eduzz:** assinaturas e cursos
- **TikTok Shop:** vendas da loja

Cada fonte tem seus próprios status. Não confunda.

## Fatura (LIA) — parcelas e pagamento

```
fatura
├── status: pendente
│   ├── valor_original: R$ 1.200
│   ├── parcelas: [
│   │   ├── {n: 1, valor: R$ 200, vencimento: 10/10, status: paga},
│   │   ├── {n: 2, valor: R$ 200, vencimento: 10/11, status: pendente},
│   │   └── {n: 3, valor: R$ 200, vencimento: 10/12, status: pendente}
```

**Regras:**
- Fatura `paga` ≠ todas as parcelas pagas.
- Uma parcela `vencida` ≠ fatura cancelada.
- Cliente inadimplente pode ter acesso suspenso, mas pedido continua ativo.

## Como usar este modelo na prática

### "A pessoa pergunta se já é cliente"
1. Verificar se existe `cliente` com `vínculo_verificado: true`
2. Se não existe → "Posso verificar, me conta como você comprou?"
3. Se existe → consultar fonte do pagamento

### "A pessoa pergunta sobre pedido"
1. Identificar a fonte mais provável (perguntar se não sabe)
2. Consultar `pedido` na fonte correta
3. Retornar status correto (não inventar prazo)

### "A pessoa pergunta sobre parcelas"
1. Consultar `fatura` na LIA
2. Retornar status de cada parcela
3. Encaminhar para time financeiro se inadimplência

## Pitfalls

- **Confundir etapa com tipo.** "Lead quente" é etapa, não tipo de dados. O tipo
  é `pessoa` ou `cliente`.
- **Assumir vínculo.** Comentou muito ≠ é cliente. Comprou uma vez ≠ vínculo.
- **Blendar status.** "Pago" no Bling ≠ "pago" no Yampi. Cada fonte tem seu modelo.
- **Ignorar fonte.** Não inferir dados de uma fonte em outra.

## Verification

- Consigo distinguir pessoa de cliente em qualquer contexto?
- Sei explicar por que não posso afirmar algo (sem vínculo, sem fonte)?
- Os status de pedido estão corretos para cada fonte?
- Nenhum dado foi fabricado por proximidade ou suposição?
