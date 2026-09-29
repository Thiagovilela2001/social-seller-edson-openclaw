# Social Seller do Edson — adaptação OpenClaw

Port do agente **Social Seller** (hoje uma *Profile Distribution* do Hermes) para o
**OpenClaw**, preservando o motor de regras, as regras de negócio e a personalidade já
validados.

> **Este diretório é novo e isolado.** Nenhum arquivo do agente Hermes foi lido-para-escrita,
> movido ou sobrescrito. O repositório Hermes (`../social-seller-edson`) fica **congelado como
> referência** e continua intocado.

---

## Princípio do port

Três regras guiam a adaptação:

1. **Não reescrever o que já funciona.** O motor determinístico (`rules.py`), o gate de envio
   (`instagram_api.py`), os adaptadores fail-closed (`integracoes.py`) e a suíte de testes são
   stdlib puro e runtime-agnósticos. Eles **viajam byte-idênticos** e continuam sendo a única
   implementação das regras.
2. **Adaptar a casca, não o miolo.** O que muda é o que é contrato de runtime: manifesto,
   registro de plugin, rota de webhook, cron, resolução de estado, hooks.
3. **Nada é apagado.** O que não é portado fica em `reference/`, para consulta e auditoria.

---

## Estrutura

```
social-seller-edson-openclaw/
├── engine/instagram_seller/   MOTOR verbatim (byte-idêntico ao Hermes)
│   ├── rules.py                   regras de negócio RN-001..RN-021 + estado (SQLite)
│   ├── instagram_api.py           gate de envio — última barreira antes da rede
│   ├── integracoes.py             Bling/Clint/WhatsApp — fail-closed (RN-019)
│   └── schemas.py                 schemas das 3 tools
├── mcp/                       ADAPTADOR: servidor MCP (stdio) das 3 tools
├── ingress/                   entrada: intake determinístico + vigia de SLA
├── agent/                     CONFIG do agente OpenClaw
│   ├── openclaw.config.json       fragmento (merclar, não substituir)
│   └── workspace/
│       ├── SOUL.md                personalidade (F08 resolvido pela RN-008)
│       └── skills/                as 3 skills (o OpenClaw carrega daqui)
├── automations/               os 3 jobs em formato de automation do OpenClaw
├── tools/                     verificadores: portabilidade, skills, config
├── tests/                     suíte (205 testes)
├── reference/                 original Hermes congelado (não editar)
├── docs/                      GAPS, PORTABILITY e notas de adaptação
└── state/                     estado local (kill switch, SQLite) — gitignored
```

---

## O que já foi feito

- [x] Pasta criada, isolada do Hermes.
- [x] Motor copiado **byte-idêntico** (SHA256 conferido).
- [x] Hermes verificado como **sem alterações** (`git status` limpo).
- [x] Repositório **próprio** no GitHub (independente, `isFork: false`).
- [x] Adaptador **MCP** com as 3 tools — `python mcp/smoke_test.py` (7/7).
- [x] **Portabilidade** verificada — `python tools/check_portability.py` (6/6).
- [x] **Skills** convertidas para o formato do OpenClaw — `python tools/check_skills.py` (19/19).
- [x] **`SOUL.md`** no workspace, com o achado **F08** resolvido conforme a RN-008.
- [x] **Config do agente** — `agent/openclaw.config.json` + `python tools/check_agent_config.py` (22/22).
- [x] **Automations** — as 3 rotinas em `automations/` + `python tools/check_automations.py` (47/47).
- [x] **Ingress** — `ingress/sidecar.py` + `python -m unittest tests.test_ingress` (22/22).
- [x] **Espinha dorsal v3** — `capacidades.py` (escada da §02 + contrato de ferramentas) + `tests/test_capacidades.py` (31/31).
- [x] Suíte herdada rodando: **205 testes** (agora **258**, com ingress e capacidades).
- [x] Plano em [`PORT-PLAN.md`](PORT-PLAN.md), lacunas em [`docs/GAPS.md`](docs/GAPS.md)
      e inventário da v3 em [`docs/V3-INVENTARIO.md`](docs/V3-INVENTARIO.md).

## Próximo passo

O que a v3 exige está mapeado em [`docs/V3-INVENTARIO.md`](docs/V3-INVENTARIO.md).
**Quase tudo depende de credencial, contrato de fornecedor ou decisão de governança** — não de
código. O que não depende já está feito (a espinha dorsal).

Falta ainda: a decisão sobre `sessionKey` por lead, **D6** (`hermes_home()`), **LICENSE** e a
política do `reference/`.

---

## Aviso de escopo

Este projeto **não** liga nada em produção, não cadastra webhook na Meta, não configura
credenciais e não envia mensagem alguma. É a camada de software do port.
