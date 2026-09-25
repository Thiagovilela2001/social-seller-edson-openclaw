# Inventário de capacidades — v3.0

**Base:** `Agente_Social_Seller_Documento_Mestre_v3.0`, 24/09/2026 (§01–§35).
**Nota de escopo:** o anexo recebido está **truncado** no meio da §35, e as referências
`[B1]`, `[B2]`, `[U]`, `[S01–S40]` não vieram. Seções posteriores à 35 não foram vistas.

Este documento é o **inventário de capacidades** que o mestre exige repetidamente (§04, §06,
§10, §17). Ele existe para que a pergunta "isso funciona?" tenha resposta por escrito, item
por item, em vez de virar promessa.

---

## Como ler o estado

Vocabulário do próprio mestre (§02), aplicado literalmente:

| Estado | Significado |
|---|---|
| **decidido** | Requisito solicitado pelo responsável. |
| **documentado** | Existe descrição pública do fornecedor. |
| **proposto** | Solução técnica deste projeto. |
| **condicionado** | Depende de conta, região, escopo, contrato ou política. |
| **homologado** | **Exige evidência de teste real.** Nada aqui está homologado. |

E a escada da §02, que virou estrutura em código (`capacidades.py`):

> API existente ≠ acesso concedido ≠ ferramenta implementada ≠ dado consultado ≠
> ação autorizada ≠ produção liberada

Nenhuma capacidade abaixo passou do nível **ferramenta implementada**. Não há credencial,
não houve consulta, não houve ação em produção.

---

## O que o port OpenClaw já entrega

Isto **não** é estimativa: está tudo verificado por teste neste repositório.

| Frente da v3 | Situação no port |
|---|---|
| "O Social Seller permanece no OpenClaw" (§01) | **Feito** — o port existe, com motor de regras, MCP e ingress |
| "Reaproveitar o motor Python e o adaptador MCP" (§06) | **Feito** — motor byte-idêntico; MCP expõe as 3 tools |
| Regras de negócio em código, não em prompt (§06, §12) | **Feito** — 227 testes; guardrail no caminho do envio |
| Capability registry fail-closed (§10, §20) | **Feito** — `integrácoes.py`, estendido agora |
| Contrato de ferramentas com contexto no servidor (§10) | **Feito** — `capacidades.py` (este incremento) |
| Retorno estruturado com frescor (§09, §10) | **Feito** — `capacidades.py` (este incremento) |
| Serializar mensagens do mesmo caso (§07) | **Feito** — `Coalescer` no ingress |
| Dedupe + idempotência na entrada (§11) | **Feito** — intake + `Idempotency-Key` |
| Parada de emergência única (§11) | **Feito** — kill switch, lido pelo intake, gate e MCP |
| Observabilidade (§31, §32) | **Não começou** — Langfuse |

---

## Mapa por seção do mestre

### §04 · Canais

| Superfície | Estado | Bloqueador real |
|---|---|---|
| Facebook / Instagram | **ferramenta implementada** (comentário, DM, private reply) | App Meta no nome do cliente, App Review, contas autorizadas |
| YouTube: vídeos/Shorts | **proposto** | OAuth + Data API; quota do projeto; métodos nunca exercitados |
| YouTube: lives | **proposto** | Exige live ativa, `liveChatId` e papel de dono/moderador |
| TikTok Shop | **condicionado** | Escopo `seller.customer_service` aprovado para a loja BR |
| WhatsApp | **condicionado** | Transporte + opt-in + templates. **Ver §27 abaixo: cobrança bloqueada** |
| E-mail | **condicionado** | Remetente corporativo, domínio autenticado, política de envio |

### §07 · Identidade, titular e responsável

| Requisito | Estado | Observação |
|---|---|---|
| Identificador interno + IDs externos com namespace | **proposto** | Modelo de dados, não implementado |
| Vínculo verificado antes de dado financeiro | **proposto** | O motor já tem `vinculo_resolver` para comentário; o vínculo **CRM** não existe |
| Desfazer ligação incorreta com auditoria | **proposto** | — |
| Responsável financeiro ≠ comprador/aluno | **proposto** | Depende de Eduzz/LIA |
| Nunca divulgar atraso ao aluno por presunção | **regra** | Cabe no motor de autorização (§25) |

### §08 · Modelo unificado de negócio

Tudo **proposto**. O mestre tem razão no ponto central: o port hoje conhece *lead*, não
*obrigação*. Implementado neste incremento: a regra de dinheiro (§08 — "centavos inteiros,
nunca arredondamento livre"). O resto depende das fontes.

### §09 · Qual fonte responde cada pergunta

| Informação | Fonte | Estado | Bloqueador |
|---|---|---|---|
| Histórico e responsável | Clint | **condicionado** | MCP/API real não inventariado |
| Produto e procedimento | RAG aprovada | **condicionado** | Inventário da RAG existente não feito |
| Pedido Yampi | Yampi | **condicionado** | API + conta |
| Pedido TikTok Shop | TikTok Shop / Bling | **condicionado** | Escopo de loja |
| Parcela LIA | LIA | **condicionado** | Contrato + credencial |
| Recorrência Eduzz | Eduzz | **condicionado** | Contrato + credencial |
| Venda Assiny | BigData interno | **condicionado** | **Provedor, dataset e SLA desconhecidos** (§26) |
| Rastreio | Bling | **condicionado** | Token + leitura não implementada |

`source_updated_at` / `ingested_at` / `consulted_at` — implementado no contrato deste
incremento, e **obrigatório para afirmar sucesso**.

### §10 · Contrato das ferramentas — **implementado neste incremento**

O contrato existe em código: contexto vinculado no servidor, retorno com status fechado,
evidência e frescor obrigatórios para afirmar sucesso. As **operações** (as 24 da tabela)
são nomes propostos; nenhuma tem endpoint confirmado.

### §11 · Eventos, filas e efeitos externos

| Situação | Situação no port |
|---|---|
| Duplicata/replay na entrada | **Feito** — dedupe do intake |
| Idempotência na saída | **Parcial** — `Idempotency-Key` no hook; falta na ação de saída do provedor |
| Fora de ordem | **Proposto** — o contrato carrega horários; a lógica de reconciliação não existe |
| Timeout após envio | **Feito** para Instagram (RN-021, `reconciliacao`); não para os novos canais |
| Reinício com fila persistente | **Não feito** — `Coalescer` é em memória (**F05**) |
| Backoff/Retry-After | **Não feito** na camada de saída |

### §12 · Autorização por ação

A matriz A0–A3 já existe e é imposta no caminho do envio. Novidade da v3: **permissão por
canal e por fornecedor** (ação permitida no e-mail pode ser proibida no WhatsApp) —
**proposto**, não implementado. E a proibição de o modo financeiro herdar ferramentas
administrativas é exatamente o que a política de tools por agente resolve — **a configurar**.

### §13 · Meta

Preservado. O motor já cobre: classificação, crítica legítima não apagada, distinção
público/privado (com prova de rota no teste), vínculo de autoria no servidor, e
`ad_id` nunca por aproximação.

**Pendente:** a regra universal de 24h **não** pode ser transportada para toda superfície
(§13) — hoje ela vale para o Instagram, e o contrato novo precisa dizer onde vale.

### §14–§16 · YouTube

| Item | Estado |
|---|---|
| Métodos de comentário (`commentThreads.list`, `comments.insert`, `setModerationStatus`, `delete`) | **documentado**, não implementado |
| Fluxo com checkpoint e reconciliação | **proposto** |
| Chat de live (`streamList`, `insert`, `delete`, `bans.insert`) | **proposto** |
| Orçamento de quota (50 unidades em escrita) | **requisito de capacidade** — dimensionar antes de planejar volume |
| Retenção de 30 dias / métricas derivadas / 36 meses | **condicionado** ao caso de uso aceito |

Ponto que o mestre marca bem e eu reforço: **não há DM equivalente ao Instagram**. Prometer
DM no YouTube seria inventar capacidade.

### §17–§18 · TikTok Shop

**Condicionado** ao escopo de loja. A regra brasileira (não desviar transação para fora da
plataforma, não pedir dado pessoal, não criar taxa) entra no **motor de autorização**, não
só no texto da skill — coerente com a doutrina do projeto.

### §19 · Clint

**Condicionado.** O mestre acerta o ponto crítico: *"a Clint, o canal nativo, a Evolution e
workflows não podem ser emissores independentes para o mesmo evento"*. Isso é **ownership
por caso**, e sem ele o cliente recebe a mesma mensagem duas vezes. O contrato novo já
carrega o dono do caso; a execução, não.

### §20–§24 · Bling, Yampi, LIA, Eduzz, Assiny

Todos **condicionados** a credencial/contrato, com semântica documentada que o adaptador
precisa respeitar (código ≠ postagem; pedido finished ≠ parcelas pagas; fatura paga ≠
recorrência quitada). Nada disso é implementável sem a fonte — e implementar contra uma API
não vista é o que o mestre proíbe.

### §25 · Regularização — máquina de estados

**Proposto.** Nada implementado. O que já serve de base: o padrão RN-021 (resultado incerto
trava nova tentativa) e o kill switch.

### §26 · Assiny / BigData

**Bloqueado por informação.** O mestre é explícito: provedor, datasets, chaves, frequência e
campos **não são conhecidos**. Não presumir BigQuery nem PostgreSQL. Sem esse contrato,
qualquer código seria adivinhação.

### §27 · WhatsApp — **bloqueio de política, não de código**

O mestre registra que "debt collection" está entre os serviços restritos/proibidos pela
plataforma, e conclui: **cobrança de dívida bloqueada no WhatsApp nesta especificação**.
Isso é decisão de conformidade do dono, não configuração técnica — e trocar o rótulo para
"utility" não muda o enquadramento. **Não implementar até haver regra aplicável documentada.**

### §28 · Coordenação de contatos

**Proposto.** É o que impede cobrança duplicada entre LIA, Eduzz, Yampi e o agente. Sem ele,
o risco é o cliente receber quatro toques da mesma obrigação por quatro sistemas.

### §29 · Recuperação futura

**Fase posterior, por campanha aprovada.** Depende de supressão multiorigem (§29) — que
depende de §09. Não começar por aqui.

### §30 · Exemplos de ponta a ponta

Cinco cenários. Todos dependem de fonte não conectada. Servem como **casos de teste de
aceite** quando as integrações existirem.

### §31–§32 · Langfuse

**Não começou.** Observabilidade não autoriza nada — e o mestre reforça que o Social Seller
não deve receber MCP administrativo para ler todos os traces ou alterar seus próprios
controles. Adotar com mascaramento **antes** da exportação.

### §33 · RAG

**Condicionado** ao inventário da RAG existente. Ponto preservado: sem fine-tuning, e o
agente não completa preço/parcela por memória de conversa antiga.

### §34 · Curadoria semanal

Já existe no port como automation (`sse-mineracao-semanal`). A ampliação (novas origens,
checkpoint por canal, sobreposição de 48h) é **proposta**.

### §35 · Inteligência de público

**Truncado.** Não avalio o que não recebi.

---

## Resumo do que trava a v3

| Bloqueador | Quantas frentes |
|---|---|
| **Credencial/contrato de fornecedor** (Clint, Bling, Yampi, LIA, Eduzz, Meta, WhatsApp, e-mail) | 8 |
| **Escopo de plataforma** (TikTok Shop, YouTube quota, caso de uso de métricas) | 3 |
| **Contrato de dados interno** (BigData/Assiny) | 1 |
| **Decisão de governança** (WhatsApp/cobrança, ownership de canal, quem cobra) | 3 |
| **Só código, sem depender de fora** | **1** — o contrato de capacidades/ferramentas |

É por isso que o primeiro incremento é o último da tabela: é o único que **não** depende de
terceiro, e é o que todos os outros vão usar.

---

## Ordem sugerida

1. **Espinha dorsal** — capacidades + contrato de ferramentas. ✅ *este incremento*
2. **Observabilidade mínima** — instrumentar o que já existe (sem Langfuse primeiro).
3. **Contratos de dados** — pedir o contrato real de cada fonte antes de escrever adaptador.
4. **Um canal por vez**, começando pelo que já funciona (Meta/Instagram) e provando em conta
   de teste — o mestre é explícito: teste simulado não comprova acesso.
