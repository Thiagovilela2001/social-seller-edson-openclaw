# PORTABILIDADE — o que faz este projeto rodar em qualquer host

Registro do que é **propriedade verificada**, não intenção. Tudo aqui é checado por
`python tools/check_portability.py`, que roda sem rede e sem credencial.

---

## As cinco propriedades

### 1. Zero dependência de terceiro

O motor importa **apenas stdlib** e módulos locais:

```
__future__ argparse contextlib dataclasses datetime hashlib importlib json
logging os pathlib re sqlite3 subprocess sys time traceback typing
unicodedata urllib zoneinfo
```

Nada de `requests`, `psycopg2`, `pydantic`, `httpx`. Sem `pip install`, sem
`requirements.txt`, sem lockfile, sem resolução de dependência no host do cliente.
`urllib` já é stdlib e cobre a Graph API.

**Por que isso importa:** é a diferença entre "clone e rode" e "instale um ambiente".
Em VPS de cliente, cada dependência é um ponto de falha e uma superfície de segurança.

### 2. Nenhuma dependência de runtime

O motor carrega com **`HERMES_HOME` removido** do ambiente. Foi a primeira coisa que a
sonda verifica: se algum caminho dependesse do runtime antigo, ela falharia.

O `engine/` contém **só o motor**. O registro de plugin do Hermes
(`register(ctx)`, `register_tool`, `register_hook`) saiu de lá e vive em
`reference/hermes-plugin-registration/` — é legado, e não deve parecer que o motor é
um plugin Hermes.

### 3. Caminhos resolvidos por ambiente, com fallback derivado de `__file__`

| Variável | O que faz | Padrão |
|---|---|---|
| `IG_STATE_DIR` | pasta de estado | `<repo>/state` |
| `IG_STATE_DB` | banco SQLite do motor | `<IG_STATE_DIR>/instagram-seller.db` |
| `IG_KILL_SWITCH` | arquivo-flag da parada de emergência | `<IG_STATE_DIR>/ig-kill-switch` |

O fallback do motor é derivado de `Path(__file__).resolve().parents[...]` — **não** de
`Path.home()` nem de caminho absoluto fixo. Isso é o que torna o projeto movível: o
bug original do spike do Hermes foi justamente usar `Path.home()`, que no Windows
apontava para o lugar errado.

### 4. Estado gravável em qualquer lugar

A sonda cria e remove um arquivo temporário no diretório de estado. Se o host não
permitir escrita ali, ela falha — melhor descobrir na sonda do que na primeira crise.

### 5. Fim de linha LF

`.gitattributes` com `* text=auto eol=lf`. Script com shebang e CRLF quebra no Linux
com `bad interpreter: /usr/bin/env python3^M`. Foi lição registrada no
`DEVELOPMENT.md` do Hermes; aqui virou regra do repositório, não hábito.

---

## Piso de versão do Python

| Versão | Situação |
|---|---|
| **3.11** | validado — é a versão do CI e dos testes locais (205 testes OK) |
| 3.10 | provável — `X \| None` em assinaturas já coberto por `from __future__ import annotations` |
| 3.9 | provável — é o piso do `zoneinfo` |
| ≤ 3.8 | **não suportado** — `zoneinfo` não existe |

**Honestidade:** só o 3.11 foi *medido*. Os outros são inferência a partir das APIs
usadas, e estão marcados como tal. Quando houver um host alvo definido, medir lá.

---

## Exceção declarada — o nome `hermes_home()`

`rules.py` mantém uma função chamada **`hermes_home()`**. Ela é a única dívida de
nomenclatura do port, e está aqui porque foi uma **decisão**, não um esquecimento.

**O conflito:** renomear exigiria editar `rules.py` — e a decisão **D2** foi manter o
motor byte-idêntico ao Hermes, com *uma implementação só* (doutrina do
`DEVELOPMENT.md`). Renomear faria os dois repositórios divergirem já no primeiro
commit e quebraria a comparação por SHA256 que prova que nada mudou.

**O estado atual:** a função é **funcionalmente portável**. Seu fallback é derivado de
`__file__`, não do runtime antigo. O adaptador sempre define `IG_STATE_DB` e
`IG_KILL_SWITCH`, então o caminho interno dela não é usado em produção. O que resta é
o **nome** sugerindo uma dependência que não existe mais.

**A decisão continua aberta** — e é do dono do projeto, porque mexe no arquivo que
combinamos não tocar. As três saídas estão no `PORT-PLAN.md` (D6).

---

## Como verificar (sem chave, sem rede)

```bash
python tools/check_portability.py      # as 5 propriedades
python mcp/smoke_test.py               # protocolo MCP + gate + kill switch
python -m unittest discover -s tests   # 205 testes
```
