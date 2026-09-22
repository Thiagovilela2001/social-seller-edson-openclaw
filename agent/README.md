# Config do agente OpenClaw

`openclaw.config.json` é um **fragmento para mesclar** na config do Gateway —
**nunca** um arquivo para substituir a config inteira. Ele descreve o agente
Social Seller: o servidor MCP com as três tools e a entrada do agente.

> ⚠️ **Este fragmento não foi aplicado em Gateway nenhum.** Ele é entregável, não
> execução. Aplicar é decisão do operador, e exige validar o que está na seção
> *o que ainda não foi provado*.

---

## Por que JSON estrito e não JSON5

A config do OpenClaw aceita JSON5 (com comentários). Aqui o arquivo é **JSON
estrito** de propósito: assim ele é parseável pelo Python da stdlib, e
`tools/check_agent_config.py` valida de verdade em vez de torcer. JSON é um
subconjunto válido de JSON5, então mescla sem conversão. A explicação de cada
bloco vive aqui, não em comentários no arquivo.

---

## O que cada bloco faz

### `mcp.servers.instagram-seller`

Conecta o nosso servidor MCP (`mcp/instagram_seller_mcp.py`) por stdio. É o
caminho que o OpenClaw oferece para uma tool de outro processo — e é o que
permite **não reescrever o motor** (decisão D1).

- `toolFilter.include` limita a superfície às **três** tools de envio. O servidor
  publica exatamente essas três; o filtro é o cinto além do suspensório.
- `env` leva o estado e as credenciais. **Nenhum valor literal**: só
  `${VAR}`. Credencial colada em config é o erro que este verificador barra.
- `IG_STATE_DIR` aponta o estado para `<repo>/state` — é o reapontamento por
  ambiente que evita editar `rules.py` (decisão D3).

### `agents.entries.social-seller`

A entrada do agente. Três campos foram escolhidos por **mapear regra que já
existe**, e não por estética:

| Campo | Regra que ele implementa |
|---|---|
| `humanDelay.mode: "natural"` | `SOUL.md`, regra 10: *"Nunca respondo em menos de 1 segundo — não é humano"* |
| `typingMode: "message"` | O agente "digita" antes de responder, em vez de aparecer pronto |
| `skills: [...]` | Allowlist fechada: só as três instruções do Social Seller |

**Sem pin de modelo**, deliberadamente: o Hermes também deixava sem pin
(*"quem instala escolhe"*), e o modelo muda a personalidade mesmo com o mesmo
prompt. É decisão do cliente, revalidada no go-live.

---

## O que NÃO está aqui, e por quê

| Ausente | Motivo |
|---|---|
| `hooks` | Endpoint de entrada. Armar isso sem o ingress e sem token é expor superfície. **Etapa 5.** |
| `bindings` | O Instagram **não é canal nativo** do OpenClaw. Não há canal para ligar; a entrada chega por webhook. |
| `model` | Decisão do cliente (acima). |
| `tools.deny` | **Item de revisão.** O agente fala com o público; o perfil de tools mínimo deve ser decidido com o dono, não por mim. |

---

## O que ainda NÃO foi provado

Honestidade obrigatória — nada aqui foi exercitado contra um Gateway com este
config aplicado:

1. **Substituição de `${VAR}`** em `workspace`, `args` e `env`. A documentação
   cita substituição de ambiente em outros pontos; **não verifiquei que ela vale
   nestes campos**. Se não valer, trocar por caminho absoluto e usar o
   mecanismo de segredo do host para as credenciais.
2. **`command: "python"`** — no Windows é `python`; em Linux/macOS
   normalmente é `python3`. Ajustar por host. É um ponto de quebra silenciosa.
3. **O servidor MCP responde?** Salvar a definição não prova alcançabilidade:
   ```bash
   openclaw mcp doctor instagram-seller --probe
   ```
4. **O Gateway aceita o fragmento?**
   ```bash
   openclaw config validate
   ```
5. **Identidade.** `identity.name` ("Time do Edson") e o emoji são proposta;
   branding é decisão do dono.

## Como validar o que dá para validar hoje (sem chave, sem rede)

```bash
python tools/check_agent_config.py
```

22 checagens: JSON válido, chaves conhecidas, script MCP existente no disco,
`toolFilter` citando só tool publicada, allowlist de skills existindo de fato,
`workspace` existindo, zero segredo literal, `hooks` não armado.

**Limite declarado:** valida **forma e presença de arquivo**. Não valida
comportamento do Gateway.
