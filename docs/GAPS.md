# GAPS — o que o OpenClaw não tem equivalente

Cada item aqui é uma **ausência de primitiva**, não um bug. A regra do projeto é: **documentar,
não inventar.** Nada foi improvisado para tapar buraco.

---

## G1 · `coalesce` por remetente (agrupar rajada de comentários)

**Hermes:** `platforms.webhook.routes.instagram.coalesce` agrupa rajada do mesmo autor
(`key: "{entry.0.messaging.0.sender.id}"`, `window_seconds: 20`) num único run.

**OpenClaw:** `hooks.mappings` tem `forEach` (fan-out de array) mas **não** tem janela de
agrupamento por chave. Não há primitiva equivalente.

**Consequência:** post viral gera N runs em vez de 1. Precisa de buffer próprio (ingress) ou
serviço externo.

**Correlato:** é o achado **F06** do Parecer, já registrado como *não implementado*.

**RESOLVIDO (etapa 5)** — e resolvido de forma **diferente**, com motivo: o intake trata
**um** evento por execução e **descarta lote ambíguo**. Fundir N comentários num payload
faria o intake jogar todos fora. Então a coalescência virou **ordenação**: no máximo uma
execução por remetente, o resto em fila, com janela de rajada antes de drenar o próximo.
Nenhum evento perdido, nenhuma execução concorrente da mesma pessoa. Ver
`ingress/sidecar.py` (classe `Coalescer`) e `tests/test_ingress.py`.

---

## G2 · "Script de rota substitui o payload" (intake determinístico antes do LLM)

**Hermes:** a rota declara `script: instagram-intake.py`. O gateway invoca por subprocess,
payload no STDIN, e o **STDOUT substitui** o payload do agente. `[SILENT]` descarta. Falha
fechado.

**OpenClaw:** `hooks.mappings` transforma payload em `wake`/`agent` por **template ou transform
JS/TS confiável**. Não há "rodar este script e ele decide o payload".

**Consequência:** o intake determinístico (Python, 1.000+ linhas de decisão, fail-closed) não
roda como script de rota. Opções:

- **A (recomendada):** ingress é um **sidecar local** — recebe o POST da Meta (via proxy),
  roda o intake Python, e chama `/hooks/agent` do OpenClaw com o payload já enriquecido
  (briefing + diretiva + proibições + estado). Preserva o intake e o fail-closed.
- **B:** reescrever o intake como transform JS/TS. **Rejeitada:** duplicaria o motor de regras em
  outra linguagem — exatamente o que o projeto proíbe.

**RESOLVIDO (etapa 5)** — opção **A**: `ingress/sidecar.py` recebe o webhook, roda o intake
como subprocesso (contrato idêntico ao do Hermes: stdin → stdout, `[SILENT]` descarta) e
entrega o payload enriquecido ao `/hooks/agent`. O intake **não** foi reescrito.

**Ganho colateral:** como o sidecar responde o GET de verificação da Meta, o proxy de
borda do Hermes (`deploy/edge_proxy.py`) **deixou de existir** — ele só existia porque o
adapter do Hermes aceitava apenas POST. Sobrou TLS. Ver `ingress/Caddyfile.example`.

---

## G3 · Ciclo de vida de *Distribution* (`profile install/update/purge-identity`)

**Hermes:** manifesto (`distribution.yaml`), `distribution_owned`, exclusão dura no instalador,
update in-place sem tocar em `.env`/memória/sessão.

**OpenClaw:** não existe instalador de distribution de profile. O análogo é o repositório + a
config de agente + workspace.

**Consequência:** o versionamento passa a ser git + config explícita. Perde-se o "preserva `.env`
e memória no update" automático; ganha-se clareza. **Nada a implementar como código.**

---

## G4 · Gate de carregamento do plugin por env (`requires_env`)

**Hermes:** `plugin.yaml.requires_env` — sem token, o plugin nem liga.

**OpenClaw:** não há gate de carga de plugin por env. O análogo mais próximo é o **gating de
skill** (`metadata.openclaw.requires.env` / `requires.config`).

**Decisão:** o MCP deve falhar explícito quando faltar credencial (o motor já devolve erro claro),
e o gating de skill cobre a visibilidade. **A portar** junto das skills.

---

## G5 · Hook de shell com allowlist e fail-OPEN

**Hermes:** hook `pre_tool_call` em shell exige `shell-hooks-allowlist.json`; sem consentimento
**não registra e falha ABERTO** (issue #100942).

**OpenClaw:** tem hooks de plugin e tool policy — modelo diferente.

**Contexto que reduz a urgência:** o próprio projeto Hermes já decidiu que o hook é *defesa em
profundidade*, e que **a barreira real é o gate no caminho do envio** (`instagram_api._autorizar`).
Esse gate **viaja no motor** e vale igual no OpenClaw.

**Decisão:** replicar o hook só se a versão instalada oferecer hook de tool confiável; a
proteção real não depende dele.

---

## G6 · Canal nativo do Instagram

**OpenClaw:** não há canal Instagram entre os suportados. A comunicação com a Meta Graph
permanece **no nosso código** (`instagram_api.py`), e a entrada chega por webhook.

**Consequência:** nenhuma surpresa; confirmar no desenho do ingress que não se espera canal nativo.

---

## G7 · Integrações prometidas (Bling, Clint, WhatsApp)

**Igual nos dois runtimes:** `integracoes.py` é **fail-closed** e `CAPACIDADES` é `False`.
Continua valendo a **RN-019** — sem fonte consultada, o agente não afirma status de pedido.

**O que falta é o mesmo dos dois lados:** credencial + leitura. Não é gap de port.
Ver *Pendência 10*.

---

## G8 · Filas recuperáveis e isolamento por cliente/caso

Achado **F05/F06**: exige um executor com estado de processamento
(`recebido → validado → enfileirado → processando → confirmado → concluído`). Pertence à
**camada de recepção**, que é justamente o que o port está montando.

**Estado:** a desenhar no ingress. Não implementado.

---

## Resumo

| Gap | Tem solução? | Onde |
|---|---|---|
| G1 coalesce | Desenho próprio | ingress |
| G2 script de rota | Sidecar (opção A) | ingress |
| G3 distribution lifecycle | Não aplicável | — |
| G4 gate de plugin por env | Gating de skill + erro explícito | skills / MCP |
| G5 hook de shell | Opcional; gate real já viaja | mcp / engine |
| G6 canal Instagram | Código próprio (já existe) | engine / ingress |
| G7 integrações | Falta credencial (igual nos dois) | pendência de cliente |
| G8 fila recuperável | Desenho próprio | ingress |
