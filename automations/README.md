# Automations

As três rotinas do Social Seller, em formato que o agendador do OpenClaw aceita.
Cada arquivo é um **job**, pronto para `automations add` — ou para criar pela
página de Automations do Control UI.

> ⚠️ **Os três nascem DESLIGADOS** (`enabled: false`), de propósito. Ver
> *Por que desligado* abaixo.

| Job | Quando | Payload | Por que assim |
|---|---|---|---|
| `sse-followup-janela` | `0 9 * * *` | `agentTurn` | Precisa de modelo: escolhe a jogada e redige o toque |
| `sse-mineracao-semanal` | `0 8 * * 1` | `agentTurn` | Precisa de modelo: interpreta conversas e propõe |
| `sse-vigia-fila-humana` | `*/15 * * * *` | `command` | **Não** precisa de modelo — é script determinístico |

---

## As três decisões que mudam em relação ao Hermes

### 1. `tz` explícito, sempre

O Hermes tinha `"expr": "0 9 * * *"` e confiava na hora do host. Aqui o fuso é
declarado: `"tz": "America/Sao_Paulo"`. O documento do OpenClaw é explícito — o
`expr` é hora de parede no `tz`, e **nunca** se deve pré-converter para UTC nem
depender do fuso do Gateway. Um cliente em VPS UTC rodaria o follow-up às 6h.

### 2. `sessionTarget: "isolated"` nas três

Cada execução ganha sessão nova. Isso importa por um motivo específico: uma
conversa de DM **não pode compartilhar contexto** com a rotina de follow-up. Se
compartilhasse, o que foi dito a um lead vazaria para o raciocínio do job.

### 3. O vigia virou `command` — e o silêncio virou código

Esta é a diferença que vale explicar.

No Hermes, o vigia era um `prompt` que pedia ao **modelo**: *"Se `atrasados`
estiver VAZIO: NÃO envie mensagem nenhuma."* Ou seja, a regra "alerta que sempre
toca deixa de ser alerta" dependia de o modelo lembrar de não falar — a cada 15
minutos, 96 vezes por dia.

O OpenClaw tem uma primitiva melhor, e o Hermes não tinha:

- **payload `command`** roda um script na hora, **sem chamar modelo**;
- o texto entregue vem do **stdout** do processo;
- se o script imprimir **`NO_REPLY`**, o agendador **não posta nada**.

Então a regra saiu do prompt e foi para o código: `ingress/fila-humana-sla.py`
ganhou `--silenciar-vazio`, que imprime `NO_REPLY` quando não há caso fora do SLA.
Resultado: silêncio **garantido**, zero token gasto em fila em dia, e nenhum
modelo podendo errar a instrução.

É exatamente a doutrina do projeto — *regra em código, não em instrução* —
aplicada a uma peça que antes era instrução.

**O que se perde:** nada. O script já ordena por gravidade, já marca P0 e já mostra
quantas vezes o caso foi cobrado. O modelo estava apenas repassando texto.

---

## Por que desligado

É a lição mais cara do pacote Hermes: **cron de distribution instalado ligado é
falha silenciosa**. Lá o instalador não agendava nada e o follow-up simplesmente
nunca rodava, sem aviso.

Aqui o motivo é o mesmo em espírito: um job ligado apontando para um destino que
não existe (Telegram sem plantão definido, banco sem credencial) gera alerta de
falha a cada 15 minutos. Desligado, a falta de habilitação é **visível** em vez de
invisível.

**Para ligar:**
```bash
openclaw automations enable sse-followup-janela
```

---

## O que ainda impede cada job de funcionar

Isto é o mais importante desta pasta. Nenhum dos três está pronto para produzir
efeito hoje:

### `sse-followup-janela`

- **Fonte de dados ausente.** O job lista leads por estágio, toques enviados e
  janela de 24h. No Hermes isso vinha do **Postgres do cliente** (`leads`), que
  não existe no port. O motor tem estado próprio (SQLite: `lead_stage`,
  `toques_proativos`, `inbound`), mas **não** é a mesma coisa. Falta decidir:
  ler do SQLite do motor, ou integrar o CRM (**Pendência 10**).
- **Destino ausente.** `${TELEGRAM_CHAT_ID}` precisa existir, e o plantão precisa
  estar definido — SLA sem gente do outro lado é número decorativo (RN-012).

### `sse-mineracao-semanal`

- **Depende do MCP da Clint** (`CLINT_MCP_URL`), que não existe. Sem ele a rotina
  não tem o que ler. O servidor MCP também precisa ser declarado em `mcp.servers`.
- O job grava propostas em arquivo: precisa de permissão de escrita no workspace.

### `sse-vigia-fila-humana`

- **É o mais próximo de rodar**: só depende do script e do destino do Telegram.
  Não precisa de modelo nem de credencial.
- **Atenção na instalação:** `argv` é executado **sem shell**, então
  `${SOCIAL_SELLER_REPO}` **não é expandido**. Substitua por caminho absoluto
  antes de habilitar. O verificador avisa, e o erro é ruidoso (exit ≠ 0 → run
  `error` → alerta de falha após 2 execuções), não silencioso.

---

## O que NÃO foi feito, e por quê

| Não feito | Motivo |
|---|---|
| `toolsAllow` por job | Os nomes das tools MCP expostas (`ig_send_dm` com ou sem prefixo de servidor) **não foram verificados**. Inventar o nome bloquearia o job em silêncio. Fechar com `openclaw mcp doctor instagram-seller --probe`, que lista o que o servidor publica. |
| `trigger` no vigia | O `command` + `NO_REPLY` já resolve o silêncio de forma determinística. Um `trigger.script` seria uma segunda forma de fazer o mesmo, com API de code-mode que eu **não** validei. Uma implementação boa basta. |
| `pacing` | O Hermes tinha cadência fixa. `pacing` é para polling adaptativo — não é o caso. |
| `failureAlert` explícito | O comportamento padrão (rota de entrega existe → alerta após 2 falhas, cooldown de 1h) já é o desejado. Configurar sem necessidade só cria ruído. |

## Como validar

```bash
python tools/check_automations.py
```

Valida forma: JSON, cron de 5 campos, `tz` explícito e válido, payload com os
campos obrigatórios do seu tipo, arquivo referenciado existindo no disco, job
nascendo desligado, sem segredo literal.

**Limite declarado:** valida **forma**. Não prova que o agendador aceita o job nem
que o efeito acontece. Isso exige Gateway alvo.
