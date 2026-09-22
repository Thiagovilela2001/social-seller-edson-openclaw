# PORT-PLAN — Hermes → OpenClaw

Mapa `componente → destino → estado → evidência`. Acompanha `docs/GAPS.md`.

Legenda de estado (vocabulário do Parecer OpenClaw, seção 10):

| Estado | Significado |
|---|---|
| **portado** | Já existe no novo projeto, funcionando e verificado localmente. |
| **adaptado** | Existe, mas com contrato diferente do Hermes — verificado localmente. |
| **a portar** | Identificado, ainda não escrito. |
| **não tem equivalente** | Não há primitiva no OpenClaw; exige desenho próprio. Ver `GAPS.md`. |
| **congelado** | Fica só em `reference/`, como referência. |

---

## 1. Motor (o miolo — não muda)

| Componente | Destino | Estado | Evidência |
|---|---|---|---|
| `rules.py` (RN-001..021, estado SQLite) | `engine/instagram_seller/rules.py` | **portado** | SHA256 idêntico ao Hermes |
| `instagram_api.py` (gate de envio) | `engine/instagram_seller/instagram_api.py` | **portado** | SHA256 idêntico |
| `integracoes.py` (fail-closed) | `engine/instagram_seller/integracoes.py` | **portado** | SHA256 idêntico |
| `schemas.py` (3 schemas) | `engine/instagram_seller/schemas.py` | **portado** | SHA256 idêntico |
| `__init__.py` (registro Hermes `register(ctx)`) | `engine/instagram_seller/__init__.py` | **congelado** | inerte no OpenClaw |
| `tests/` (205 testes) | `tests/` | **adaptado** | roda; harness de contrato a ajustar |

**Decisão de arquitetura:** o motor é importado como biblioteca, nunca duplicado nem
reescrito. Uma regra muda em `rules.py` e vale para os dois runtimes.

---

## 2. Casca (o que é contrato de runtime — muda)

| Componente Hermes | Equivalente OpenClaw | Estado |
|---|---|---|
| `distribution.yaml` (profile install/update, `distribution_owned`) | Config de agente (`agents.entries`) + workspace + allowlist de skills | **adaptado** |
| `plugin.yaml` + `register(ctx)` (plugin Python) | Servidor **MCP** (stdio) expondo as 3 tools | **adaptado** |
| Hook `pre_tool_call` (JSON stdin/stdout, allowlist de shell) | Hook de plugin / tool policy do OpenClaw | **a portar** |
| `config.yaml` → `plugins.enabled` | `plugins.entries` / registro do MCP | **a portar** |
| `config.yaml` → `platforms.webhook.routes.instagram` (`script:`, `prompt:`, `coalesce:`, `deliver:`) | `hooks.mappings` + `/hooks/agent` (transform JS/TS) | **não tem equivalente** (parcial) |
| `cron/jobs.json` (3 jobs) | `automations` (cron + agentTurn + delivery) | **a portar** |
| `deliver: telegram` (escalada A0) | Canal `telegram` + `message`/`conversations_send` | **a portar** |
| `HERMES_HOME` / `ig-kill-switch` | `IG_KILL_SWITCH` + `IG_STATE_DB` apontando para `state/` | **adaptado** |
| Frontmatter `metadata.hermes` das skills | removido — sem gating; `os` não restringe nada | **portado** |

### Como o estado é reapontado (sem tocar no motor)

`rules.py` resolve caminhos nesta ordem, e por isso **não precisa ser editado**:

```python
state_db_path()     ->  os.getenv("IG_STATE_DB")    or hermes_home()/"instagram-seller.db"
kill_switch_path()  ->  os.getenv("IG_KILL_SWITCH") or hermes_home()/"ig-kill-switch"
```

O adaptador MCP define os dois para `<este repo>/state/` quando não estão no ambiente.
Resultado: o motor roda igual, gravando no novo perímetro.

---

## 3. Ordem de execução

1. **Motor + estado** — feito.
2. **Adaptador MCP** (`ig_send_dm`, `ig_private_reply`, `ig_reply_comment`) — feito, com
   smoke test do protocolo e do gate.
3. **Skills** — frontmatter `metadata.hermes` → `metadata.openclaw`; corpo preservado.
4. **SOUL.md** — portar para `agent/workspace/` e resolver o achado **F08** (política única de
   identidade × modo `sob_pergunta`).
5. **Ingress** — intake determinístico adaptado ao contrato de entrada do OpenClaw + proxy de
   borda (GET de verificação da Meta).
6. **Automations** — os 3 jobs.
7. **Testes** — ajustar harness (`test_intake`, `test_gate`) ao novo contrato.
8. **Docs** — README/HANDOVER/DEVELOPMENT em termos de `openclaw`.
9. **Validação** — rodar a suíte inteira; provar gate e kill switch de ponta a ponta.

---

## 4. Decisões tomadas

| # | Decisão | Motivo |
|---|---|---|
| D1 | **MCP** para expor as tools, não plugin TS | OpenClaw não roda plugin Python; MCP preserva o `rules.py` como fonte única e evita reimplementar regra em TS |
| D2 | Motor **vendorizado** e byte-idêntico | Projeto novo precisa ser auto-contido; Hermes congela como referência |
| D3 | Estado em `state/`, via env | Não edita o motor e mantém o novo perímetro |
| D4 | Cópia em vez de symlink para o Hermes | Portabilidade (Windows/git) e independência do repo antigo |

## 5. Em aberto

- **Canal nativo do Instagram:** o OpenClaw não tem um. A entrada continua pelo webhook; a
  saída continua no nosso `instagram_api.py`. Confirmar desenho do ingress.
- **`coalesce` por remetente:** sem primitiva equivalente. Ver `GAPS.md`.
- **Versão instalada do OpenClaw:** o schema de `hooks.mappings` / `plugins.entries` precisa ser
  validado contra ela — o Parecer já avisa que "não basta renomear arquivos".
