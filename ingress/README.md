# Ingress — da Meta até o Gateway

`sidecar.py` é o que transforma o port em agente que **recebe**: ele fica entre o
webhook da Meta e o `/hooks/agent` do OpenClaw.

```
Meta ──HTTPS──> Caddy/nginx ──> sidecar.py ──subprocess──> instagram-intake.py
                                    │                              │
                                    │                        (decisão das regras)
                                    ▼                              │
                            Coalescer (ordena por remetente)  <────┘
                                    │
                                    ▼
                        POST /hooks/agent  (auth bearer + idempotency)
```

---

## Por que um sidecar (G2)

No Hermes, a rota declarava `script: instagram-intake.py` e o **gateway** rodava o
script, trocando o payload pelo stdout dele. O OpenClaw **não tem esse primitivo**:
`hooks.mappings` transforma payload com template ou **módulo JS/TS**.

Reimplementar o intake em JS/TS duplicaria o motor de regras em outra linguagem —
o que o projeto proíbe. Então o intake continua sendo o intake, rodando como
subprocesso aqui, e o sidecar faz a ponte.

## E o proxy de borda do Hermes? Deixou de existir

O Hermes precisava de um proxy separado (`deploy/edge_proxy.py`) porque o adapter
dele **só aceitava POST** e a Meta exige um **GET** de verificação antes de
cadastrar a URL.

Aqui o sidecar responde o GET ele mesmo (`hub.challenge`). Sobra apenas **TLS** na
frente. Ver `Caddyfile.example` — são três linhas.

---

## Rotas

| Rota | O que faz |
|---|---|
| `GET /webhooks/instagram?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…` | Handshake da Meta. Devolve o `hub.challenge` **cru** se o token casar; 403 se não. |
| `POST /webhooks/instagram` | Valida assinatura → roda o intake → ordena → despacha |
| `GET /health` | `{"status":"ok","platform":"instagram-ingress"}` |

## Ordem de decisão no POST

1. **Tamanho do corpo** (≤ 1 MiB) — senão 413.
2. **Assinatura `X-Hub-Signature-256`** contra `META_APP_SECRET` — senão 401.
   Comparação em tempo constante, e **sem segredo nada passa**.
3. **Intake** como subprocesso, com o contrato real: payload no STDIN, STDOUT
   substitui, `[SILENT]` descarta. Ele **falha fechado**.
4. **Ordenação** por remetente (`Coalescer`).
5. **Despacho** para `/hooks/agent` com `Authorization: Bearer` e `Idempotency-Key`
   igual ao `event_id` do intake.

---

## A coalescência é ORDENAÇÃO, não fusão (G1) — e por quê

O Hermes **agrupava** a rajada num único run (`coalesce.key` + janela de 20s). Aqui
isso seria ativamente ruim:

> O intake trata **um** evento por execução e **descarta lote ambíguo** — o comentário
> no código dele diz: *"responder dois webhooks num turno embaralha a janela de 24h"*.

Se eu juntasse N comentários num payload, o intake jogaria **todos** fora. Então:

- no máximo **uma execução em andamento por remetente**;
- o resto entra em **fila** e roda em sequência;
- antes de drenar o próximo, espera a **janela de rajada** (`IG_COALESCE_PAUSA_SEGUNDOS`).

Ganho: nenhum evento perdido, nenhuma execução concorrente para a mesma pessoa, e a
mesma proteção que o Hermes buscava. Ver `TestOrdenacaoPorRemetente` — o teste mede a
concorrência e falha se dois turnos da mesma pessoa se sobrepuserem.

---

## Configuração

| Variável | Obrigatória | Padrão | Para que |
|---|---|---|---|
| `META_APP_SECRET` | **sim** | — | Valida a assinatura do webhook |
| `META_VERIFY_TOKEN` | **sim** | — | Handshake de verificação |
| `OPENCLAW_HOOK_TOKEN` | **sim** | — | Bearer do `/hooks/agent` (o `hooks.token` do Gateway) |
| `OPENCLAW_GATEWAY_URL` | não | `http://127.0.0.1:18789` | Onde está o Gateway |
| `OPENCLAW_HOOK_AGENT_ID` | não | `social-seller` | Agente que recebe o turno |
| `IG_WEBHOOK_HOST` | não | `127.0.0.1` | Escuta só em loopback por padrão |
| `IG_WEBHOOK_PORT` | não | `8080` | Porta do ingress |
| `IG_INTAKE_SCRIPT` | não | `ingress/instagram-intake.py` | Caminho do intake |
| `IG_LOG_DIR` | não | `<repo>/logs` | Log do ingress **e** log de falhas do intake |
| `IG_STATE_DIR` | não | `<repo>/state` | Estado do motor (repassado ao intake) |
| `IG_COALESCE_PAUSA_SEGUNDOS` | não | `3` | Janela de rajada |
| `IG_COALESCE_PARALELO` | não | `4` | Execuções simultâneas (remetentes distintos) |
| `IG_INTAKE_TIMEOUT` / `IG_HOOK_TIMEOUT` | não | `30` / `15` | Timeouts |

**Falha fechado no boot:** sem as três obrigatórias o processo **não sobe**. Subir sem
segredo seria aceitar webhook sem conseguir validar assinatura.

```bash
python ingress/sidecar.py --check     # valida config; nunca imprime valor de segredo
python ingress/sidecar.py             # sobe o ingress
```

---

## Duas decisões que valem explicação

### 200 quando o intake falha

Se o intake quebra, o sidecar responde **200** com `descartado: true`. Parece errado,
mas a alternativa é pior: a Meta **reenviaria o mesmo payload quebrado** em loop, para
sempre. O intake já gravou o payload bruto no log de falhas dele
(`<IG_LOG_DIR>/instagram-intake-falhas.jsonl`), de onde dá para **reprocessar**. Retentar
aqui não conserta formato.

**Por isso monitore esse arquivo.** Um dreno nele significa que eventos estão sendo
descartados. O sidecar registra o motivo em `<IG_LOG_DIR>/ingress.jsonl`.

### `deliver: false` e `sessionMode: isolated`

O envio no Instagram acontece pelas **tools do MCP**, não pelo anúncio do runner — não
faz sentido o runner tentar postar a resposta final num canal. E cada evento é atendido
com sessão própria: a continuidade do lead vive no **estado do motor** (SQLite), não no
histórico de sessão.

⚠️ **Consequência a decidir:** com `isolated`, o agente não lembra do que foi dito na
mensagem anterior *no histórico da sessão*. Ele recebe o evento atual + o estado do lead
(flags, estágio, fila). A alternativa é `sessionMode: "persistent"` com `sessionKey` por
`igsid`, o que exige `hooks.allowRequestSessionKey: true` e
`hooks.allowedSessionKeyPrefixes` no Gateway. **Trade-off entre continuidade e superfície
de injeção de session key** — decisão do dono, não minha.

---

## O que NÃO está pronto

| Falta | Por quê |
|---|---|
| TLS | `Caddyfile.example` é um exemplo; certificado e domínio são do cliente |
| Cadastro do webhook na Meta | Exige app, domínio e App Review — integração |
| `sessionKey` por lead | Decisão de desenho (acima) |
| Fila durável | O `Coalescer` vive em memória. Reinício do processo perde o que estava enfileirado. É o achado **F05** — exige executor com estado de processamento |
| Isolamento por conta/cliente | Achado **F06** — pertence a esta camada, ainda não desenhado |

## Como verificar (sem chave, sem rede externa)

```bash
python -m unittest tests.test_ingress -v      # 22 testes: assinatura, handshake, intake, ordem, HTTP
python ingress/sidecar.py --check             # config completa?
```
