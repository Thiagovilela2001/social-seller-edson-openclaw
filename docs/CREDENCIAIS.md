# Credenciais — o que buscar, e em que ordem

A tabela completa, gerada do código, está em
[`CREDENCIAIS-TABELA.md`](CREDENCIAIS-TABELA.md). Este documento é o guia humano:
o que pedir, a quem, e o que **não** dá para pedir ainda.

> **Regra de segurança, sem exceção:** credencial nunca em chat e nunca no
> repositório. Vai no `.env` da máquina (que o `.gitignore` cobre) ou no cofre de
> segredos do Gateway. O repositório é **público**.

---

## Antes de pedir qualquer coisa: o que o port NÃO precisa mais

Isto encurta a lista em relação ao Hermes:

| Credencial do Hermes | Situação no port |
|---|---|
| `WEBHOOK_SECRET` | **Não existe mais.** Era o secret global do adapter de webhook do Hermes. O sidecar usa `META_APP_SECRET` (assinatura da Meta) + `OPENCLAW_HOOK_TOKEN` (bearer do Gateway). |
| `HERMES_HOME` | **Removido.** Estado resolvido por `IG_STATE_DIR`. |
| `DATABASE_URL` | **O código do port não usa Postgres.** O motor tem estado próprio em SQLite. Postgres volta só se o produto tiver banco de leads próprio (**Pendência 10**). |

Ou seja: das 10 variáveis do pacote Hermes, **três são dispensáveis** aqui.

---

## Bloco 1 — o mínimo para o Instagram deixar de ser teórico

Estas sete destravam o caminho inteiro. As **três primeiras** são o que o ingress
exige para sequer subir (`sidecar.py --check` recusa sem elas):

| Variável | Onde obter | O que pedir |
|---|---|---|
| `META_APP_SECRET` | App Meta → Configurações → Básico | Chave secreta do app — **do app no nome do cliente**, não de um app de teste |
| `META_VERIFY_TOKEN` | **você inventa** | Frase longa aleatória; usada no handshake de verificação |
| `OPENCLAW_HOOK_TOKEN` | **você inventa** | Frase longa aleatória; vai também no `hooks.token` do Gateway |
| `IG_ACCESS_TOKEN` | App Meta → Instagram | Token de longa duração da conta profissional |
| `IG_USER_ID` | App Meta → Instagram | ID da conta profissional |
| `TELEGRAM_BOT_TOKEN` | Telegram → **@BotFather** → `/newbot` | Token do bot do time |
| `TELEGRAM_CHAT_ID` | Depois de convidar o bot no grupo | ID do chat do plantão |

> `IG_POLITICA_CONSUMIDOR` e `IG_DIVULGAR_AUTOMACAO` não estão aqui de propósito: a
> segunda **já está decidida** (`sob_pergunta`), e a primeira não é credencial — é
> uma linha de política que só o Edson escreve.

---

## Bloco 2 — o que não é credencial e destrava tanto quanto

Custa **zero** e trava mais frentes do que qualquer token:

| Pendência | Por que não depende de fornecedor |
|---|---|
| **Política de garantia/devolução/frete** (RN-011) | Uma linha escrita libera o agente para afirmar. Hoje ele não pode afirmar nada — nem o que é direito legal. |
| **Quem é o plantão** (RN-012) | SLA sem gente do outro lado é número decorativo. É a diferença entre a fila funcionar e existir. |
| **Lista oficial de produtos, preços e links** | O agente não calcula preço: recebe do banco. Sem catálogo, não há venda. |
| **Owner do caso por canal** (§19/§28) | Sem isso, Clint + canal nativo + n8n podem emitir a **mesma** mensagem para a mesma pessoa. Não é credencial: é regra de quem é dono do caso. |
| **Decisão §27 — WhatsApp e cobrança** | Ver abaixo. |

---

## Bloco 3 — por fornecedor (contrato antes de token)

Aqui a regra muda: **pedir o contrato primeiro, o token depois**. Pedir token de
uma API cujo payload se desconhece é como o port já aprendeu a não fazer.

| Variável | Fornecedor | O que pedir | Armadilha |
|---|---|---|---|
| `CLINT_MCP_URL` | Clint (CRM) | Endpoint MCP **somente leitura** + credencial | §19: Clint não pode ser emissor independente. Precisa de ownership por caso **antes** de ligar. |
| `BLING_API_TOKEN` | Bling (ERP) | Token de leitura de pedidos, rastreio e financeiro | O motor **já tem a interface** e a leitura está indisponível: o token é condição necessária, não suficiente. |
| `YAMPI_API_TOKEN` | Yampi | Token de leitura de pedidos | Confirmar semântica de "pedido pago" vs. transação |
| `LIA_API_TOKEN` | LIA (financiamento) | Leitura de parcelas/fatura + segunda via | **Dado financeiro**: exige vínculo verificado (§07). Sem isso, é consulta sem titular. |
| `EDUZZ_API_KEY` | Eduzz | Leitura de faturas do contrato | Fatura paga ≠ recorrência quitada |
| `TIKTOK_SHOP_APP_KEY` + `…_ACCESS_TOKEN` | TikTok Shop Partner | App com escopo **`seller.customer_service` aprovado para a loja BR** | Sem escopo aprovado, os métodos existem e não respondem |
| `YOUTUBE_API_KEY` / `YOUTUBE_OAUTH_TOKEN` | Google Cloud | Projeto com YouTube Data API v3 + OAuth do canal | **Quota**: `comments.insert` custa ~50 unidades. Dimensionar antes de planejar volume. |
| `EMAIL_SMTP_URL` | Remetente corporativo | Domínio autenticado (SPF/DKIM/DMARC) | Sem autenticação de domínio, o e-mail cai em spam |
| `BIGDATA_CONNECTION` | BigData interno (Assiny) | **Não é "a credencial".** §26 diz que provedor, datasets, chaves, frequência e SLA são **desconhecidos** | Sem esse contrato, qualquer código é adivinhação |
| `WHATSAPP_TOKEN` + `…_PHONE_ID` | — | **Não pedir ainda.** Ver §27 | Ver abaixo |

### §27 — por que WhatsApp não entra na fila agora

O próprio documento registra que "debt collection" está entre os serviços
restritos/proibidos pela plataforma, e conclui: **cobrança de dívida bloqueada no
WhatsApp**. Renomear o caso para "utility" **não muda o enquadramento**.

Isso não é configuração técnica — é decisão de conformidade do dono. Pedir a
credencial antes dessa decisão só cria a tentação de usar.

---

## Ordem recomendada

1. **Bloco 1** — o Instagram para de ser teórico. São duas frases que você inventa
   e cinco valores que já existem no app.
2. **Bloco 2** — custa zero e destrava mais do que credencial.
3. **Bloco 3, um fornecedor por vez** — contrato antes de token.
4. **WhatsApp por último**, e só depois da decisão da §27.

---

## Quando as credenciais chegarem

1. **Nunca colar em chat.** No Gateway, entram por entrada mascarada ou no `.env`.
2. Depois de configurar, o drill é:
   ```bash
   python ingress/sidecar.py --check                     # config completa?
   python tools/checklist_credenciais.py --check          # tabela em dia com o código?
   openclaw mcp doctor instagram-seller --probe           # o servidor MCP responde?
   ```
3. **Ter a credencial não libera capacidade.** A escada da §02 continua valendo:
   falta a leitura implementada e a homologação contra o recurso autorizado. É por
   isso que `capacidades.py` mostra `0 liberadas` e continuará mostrando até haver
   evidência de teste real.
