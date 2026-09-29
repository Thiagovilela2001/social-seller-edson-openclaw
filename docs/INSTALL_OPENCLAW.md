# Instalacao do OpenClaw — Social Seller Edson (sandbox)

Registro da instalacao feita em 28/09/2026 no sandbox Linux do Thiago.
Este documento e o guia de reprodutibilidade.

---

## O que foi instalado

| Item | Valor |
|---|---|
| Pacote | `openclaw` (npm) |
| Versao | **2026.9.6** (eb377ac) |
| Localizacao | `/home/thiago/.npm-global/bin/openclaw` |
| Node.js | 24.21.0 |

---

## Instalacao (reprodutivel)

### 1. Instalar o runtime

```bash
npm install -g openclaw --allow-scripts=openclaw
```

Ou, para instalacao via script oficial:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

### 2. Verificar

```bash
openclaw --version
# OpenClaw 2026.9.6 (eb377ac)
```

### 3. Configurar variaveis de ambiente

```bash
# Copiar o exemplo e preencher valores
cp .env.example .env

# Carregar no shell (ou adicionar ao ~/.bashrc)
source .env
```

Variaveis obrigatorias (sem elas o gateway nao inicia o MCP):

| Variavel | Valor no fragmento |
|---|---|
| `SOCIAL_SELLER_REPO` | Caminho do repositorio (ex: `/home/thiago/projetos/ClaudeCode/social-seller-edson-openclaw`) |
| `IG_ACCESS_TOKEN` | Token de longa duracao da conta profissional Instagram |
| `IG_USER_ID` | ID da conta profissional Instagram |
| `META_APP_SECRET` | Chave secreta do app Meta |

### 4. Aplicar o fragmento de config do agente

```bash
openclaw config patch --file agent/openclaw.config.json
```

> **Nota de compatibilidade Linux:** o fragmento ja esta corrigido para `python3`.
> Se voce usar uma versao antiga do fragmento com `"command": "python"`,
> corrija antes de aplicar:
> ```bash
> openclaw config set mcp.servers.instagram-seller.command python3
> ```

### 5. Validar

```bash
openclaw mcp list
# -> instagram-seller (ok)

openclaw agents list
# -> main (default)
# -> social-seller (Social Seller Edson)

openclaw mcp doctor instagram-seller --probe
# -> MCP doctor found no errors.
```

---

## Suite de verificacao local (sem credencial)

Todos os verificadores rodam offline, sem rede nem segredo:

```bash
cd social-seller-edson-openclaw
SOCIAL_SELLER_REPO=$(pwd) python3 tools/check_agent_config.py   # 22/22
SOCIAL_SELLER_REPO=$(pwd) python3 tools/check_portability.py    # 6/6
SOCIAL_SELLER_REPO=$(pwd) python3 tools/check_automations.py   # 47/47
SOCIAL_SELLER_REPO=$(pwd) python3 mcp/smoke_test.py            # 7/7
python3 -m unittest discover -s tests                           # 332 testes, 1 falha esperada (D1)
```

---

## Status atual (28/09/2026)

| Componente | Status |
|---|---|
| Runtime OpenClaw | Instalado e funcional |
| Fragmento de config aplicado | OK — 20 atualizacoes |
| Gateway service | **Nao instalado** (sandbox, sem systemd) |
| MCP `instagram-seller` | Probe OK |
| Agente `social-seller` | Registrado |
| Credenciais | Nao preenchidas (aguardando cliente) |
| Gateway em execucao | Nao ativo (sem canal nem modelo configurado) |

---

## Proximos passos para ativar em producao

1. **Gateway:** `openclaw setup` ou `openclaw onboard --install-daemon`
2. **Canal:** `openclaw channels add` (Telegram, WhatsApp, etc.)
3. **Modelo:** configurar provedor em `openclaw configure`
4. **Automations:** apos ter canal + modelo
   ```bash
   openclaw automations enable sse-followup-janela
   openclaw automations enable sse-mineracao-semanal
   openclaw automations enable sse-vigia-fila-humana
   ```
5. **Webhook Meta:** apontar para o ingress sidecar (`ingress/sidecar.py`)

---

## Arquivos criados/modificados nesta instalacao

| Arquivo | Acao |
|---|---|
| `.env.example` | Criado — template de variaveis |
| `agent/openclaw.config.json` | Modificado — `python` -> `python3` (correcao Linux) |
| `~/.openclaw/openclaw.json` | Criado pelo OpenClaw — config merge aplicada |
