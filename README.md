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
│   ├── schemas.py                 schemas das 3 tools
│   └── __init__.py                registro do plugin HERMES — inerte aqui (legado)
├── mcp/                       ADAPTADOR: servidor MCP (stdio) das 3 tools
├── ingress/                   entrada: intake determinístico + proxy de borda
├── skills/                    3 skills (serão adaptadas p/ metadata.openclaw)
├── automations/               os 3 jobs em formato de automation do OpenClaw
├── agent/                     config do agente OpenClaw (a validar)
├── tests/                     suíte (205 testes) — harness a ajustar
├── reference/                 original Hermes congelado (não editar)
├── docs/                      GAPS e notas de adaptação
└── state/                     estado local (kill switch, SQLite) — gitignored
```

---

## O que já foi feito

- [x] Pasta criada, isolada do Hermes.
- [x] Motor copiado **byte-idêntico** (SHA256 conferido).
- [x] Hermes verificado como **sem alterações** (`git status` limpo).
- [x] git inicializado neste projeto (branch `main`).
- [x] Plano de port documentado em [`PORT-PLAN.md`](PORT-PLAN.md).
- [x] Lacunas sem equivalente em [`docs/GAPS.md`](docs/GAPS.md).

## Próximo passo

Ver [`PORT-PLAN.md`](PORT-PLAN.md) → seção *Ordem de execução*.

---

## Aviso de escopo

Este projeto **não** liga nada em produção, não cadastra webhook na Meta, não configura
credenciais e não envia mensagem alguma. É a camada de software do port.
