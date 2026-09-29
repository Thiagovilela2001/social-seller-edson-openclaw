# Agente Social Seller | Documento Mestre v3.0
24/09/2026 · Projeto Gian · Especificação para implementação, sem fine-tuning.

## 01. O projeto em uma página
Uma operação de relacionamento, comércio e assistência financeira, com uma identidade de atendimento e controles independentes por canal.

O Social Seller permanece no OpenClaw. Atende, modera e vende; passa a incluir YouTube, TikTok Shop, consultas à LIA e Eduzz, vendas Assiny via BigData e a Yampi já integrada ao Bling. O Langfuse acompanha execuções e qualidade. As integrações declaradas pelo usuário ainda exigem validação no ambiente.

| Responsabilidade | Resultado esperado |
| --- | --- |
| Proteger e interagir | Comentários e conversas tratados conforme contexto, política e recursos do canal. Crítica legítima não é apagada por sentimento. |
| Atender e vender | Cliente identificado, conhecimento aprovado, pedido e pagamento consultados na fonte correta, comunicação registrada. |
| Apoiar regularização | Localizar a fatura ou parcela existente e orientar o responsável autorizado, sem criar dívida, cobrar cartão ou renegociar sozinho. |
| Recuperar vendas, em fase posterior | Retomar oportunidades elegíveis de perpétuo e lançamentos, sem abordar quem já comprou nem confundir abandono com dívida. |
| Medir e evoluir | Rastrear ferramentas e versões no Langfuse; curadoria semanal propõe mudanças na RAG com aprovação e testes. |

O escopo foi ampliado. A autonomia não: cada consulta, envio, moderação e rotina depende de capacidade comprovada e autorização específica.

Este documento consolida a v2 e a expansão solicitada. É uma especificação para desenvolvimento, não uma certificação de que contas, APIs, RAG ou automações já estejam conectadas. Nenhum cliente foi consultado ou contatado nesta revisão.

Base: [B1], [B2] e [U]. Desenho de implementação proposto nesta versão.

## 02. O que muda na versão 3.0
Atualização consolidada de 24/09/2026. O documento mestre v2.0, de 21/09/2026, é preservado como referência histórica.

| Tema | Decisão ou ampliação |
| --- | --- |
| Mantido | OpenClaw; Facebook/Instagram e ads; Clint; Bling; WhatsApp/e-mail; planilha; RAG sem fine-tuning; curadoria e isolamento. |
| Langfuse | Observabilidade e avaliações incluídas. Não substitui CRM, ERP, RAG, banco operacional ou controle de envio. |
| YouTube | Comentários de vídeos/Shorts elegíveis e chat de lives, em adaptadores distintos. Métricas derivadas e retenção têm condições próprias. |
| TikTok Shop | Atendimento de compradores e consulta de pedidos, condicionados a escopos da loja. Não equivale a acesso completo à rede TikTok. |
| Fontes comerciais | Yampi e TikTok Shop ligados ao Bling; LIA por API; Eduzz por API; Assiny via BigData interno informado pelo usuário. |
| Financeiro e recuperação | Assistência sobre parcelas/faturas, lembretes elegíveis e regularização. Recuperação comercial multiorigem fica prevista para fase posterior. |

### Como interpretar o estado de cada item

Decidido: requisito solicitado pelo responsável. Documentado: existe descrição pública do fornecedor. Proposto: solução técnica deste projeto. Condicionado: depende de conta, região, escopo, contrato ou política. Homologado: requer evidência de teste real; não é presumido por este PDF.

O agente técnico e o Hermes permanecem fora do escopo operacional deste mestre. As revisões anteriores de repositório servem como critérios de regressão, não como auditoria do código atual.

API existente ≠ acesso concedido ≠ ferramenta implementada ≠ dado consultado ≠ ação autorizada ≠ produção liberada.

Base: [B1], pp.2–9 e 23–32; [B2]; [U].

## 03. Mapa de leitura
Documento organizado para negócio, desenvolvimento, atendimento e governança. Os títulos e números abaixo são navegáveis no PDF.

A leitura das dependências deve acompanhar cada frente; a ampliação não elimina o escopo anterior.

## 04. Canais: não são todos iguais
A mesma identidade de marca utiliza regras e ferramentas diferentes conforme a superfície em que o cliente está.

| Superfície | Operação prevista | Condição principal |
| --- | --- | --- |
| Facebook / Instagram | Comentários orgânicos e ads; Messenger/Direct; moderação. | Contas autorizadas, permissões, janelas e alvo verificados. |
| YouTube: vídeos e Shorts | Buscar threads e respostas; responder; moderar comentários do canal. | OAuth e métodos da Data API; política de dados e orçamento de quota. |
| YouTube: lives | Receber chat ao vivo; interagir; excluir mensagem ou aplicar sanção permitida. | Live ativa, liveChatId, papel de dono/moderador e API própria. |
| TikTok Shop | Chat de atendimento, pedidos, pós-venda e informações pertinentes. | Escopo de customer service aprovado para a loja e o mercado. |
| WhatsApp | Atendimento, materiais e comunicação elegível nos números habilitados. | Transporte escolhido, opt-in, templates/janelas e elegibilidade da finalidade. |
| E-mail | Orientações e comunicações individualizadas permitidas. | Remetente corporativo, destinatário validado e política de envio. |

API da loja não autoriza automaticamente responder comentários de vídeos do TikTok, moderar lives comuns, usar DMs sociais ou apagar avaliações. Essas superfícies terão uma linha própria no inventário de capacidades e só entram após confirmação de contrato/API.

Comentários e chats públicos nunca recebem dados de pedidos, parcelas, atraso, CPF ou pagamento de uma pessoa. O caso segue por um caminho privado autorizado, quando disponível.

Fontes: [B1]; [S06–S15] YouTube; [S16–S19] TikTok; [S30] WhatsApp. Escopo de contas informado em [U].

## 05. Arquitetura geral
Uma base comum de execução e controle. Adaptadores por canal e por sistema, sem misturar identidades, pagamentos ou permissões.

[Diagrama da arquitetura no PDF.]

### Três processos separados

Atendimento: reativo à interação e ao caso. Eventos financeiros: atualizações frequentes de compras, parcelas e faturas, com cancelamento de mensagens pendentes. Curadoria: análise semanal desidentificada e propostas de conhecimento.

O n8n pode executar recepção, integração e sincronização onde necessário. Não deve concorrer com outra rota que envia o mesmo evento. Langfuse recebe telemetria filtrada em paralelo; a autorização e o histórico obrigatório permanecem nos serviços operacionais.

A aparência para o cliente é uma equipe integrada. Internamente, contexto, filas, credenciais e autorizações são separados por finalidade.

Desenho proposto. Base: [B1], pp.6–10 e 22–29. Integração de observabilidade: [S01–S05].

## 06. OpenClaw: identidade e skills
Expandir capacidades sem transformar o atendimento em um agente com acesso irrestrito a todos os sistemas.

| Módulo | Comportamento e escopo |
| --- | --- |
| Moderação | Classifica abuso e contexto; propõe resposta ou ação. Recursos de ocultação/rejeição/exclusão são específicos por plataforma. |
| Atendimento | Consulta FAQ, cliente e pedidos; resolve situações permitidas e encaminha exceções com evidência. |
| Vendas | Esclarece produto e oferta atual, trata objeções e fornece o próximo passo válido. |
| Assistência financeira | Consulta obrigação e responsável; obtém link ou segunda via existentes; opera em contexto restrito. |
| Recuperação comercial | Ativada em fase posterior, por campanha aprovada e coorte elegível, com controles de supressão e frequência. |

Uma identidade não exige uma sessão global. As skills descrevem procedimentos; a aplicação escolhe quais ferramentas ficam disponíveis para aquela tarefa. O modo financeiro não deve herdar ferramentas administrativas por conveniência.

### Limite real de segurança

O OpenClaw documenta um modelo de confiança por gateway, não isolamento hostil multiusuário automaticamente. Por isso, o projeto exige validação de cliente/caso nas ferramentas e separação entre operação pública, administração e curadoria. A ferramenta genérica de mensagem não pode contornar o serviço de autorização.

Reaproveitar o motor Python e o adaptador MCP quando adequados. Fixar versão do OpenClaw e validar o contrato real de plugins, rotas, sessões e políticas. Não tratar configuração copiada de outro runtime como integração pronta.

Nenhum cliente pode instruir o agente a trocar sua sessão, ampliar permissões ou consultar outro cliente. Texto recuperado e conteúdo de mensagem são dados, não comandos.

Base: [B1], pp.7–10,22,29; [B2], p.9. Documentação: [S04], [S05].

## 07. Identidade, titular e responsável
Unificar a jornada apenas quando houver vínculo demonstrável. Identidade social, comprador, aluno e pagador são papéis distintos.

Criar um identificador interno de cliente e manter os IDs externos com namespace: fonte + conta/loja + identificador original. Nome, apelido e proximidade de horário não bastam para unir registros. E-mail ou telefone isolados não liberam todo histórico financeiro.

| Entidade | Regra do projeto |
| --- | --- |
| Pessoa/cadastro | Vínculo verificado, finalidade, método de confirmação e data. Permitir desfazer ligação incorreta com auditoria. |
| Canal e conversa | Conta da empresa, plataforma, identidade remota e thread/caso. A sessão só recebe os dados pertinentes. |
| Comprador/aluno | A pessoa com acesso ao curso pode não ser quem paga. Não divulgar atraso ao aluno por presunção. |
| Responsável financeiro | Usar a relação autorizada da fonte. A Eduzz documenta customer e financialResponsible separadamente. |
| Pedido/fatura/parcela | Ferramenta confirma que o recurso pertence ao vínculo autorizado e à empresa correta, mesmo se o modelo fornecer outro ID. |

### Troca de canal com verificação

Levar um atendimento do Instagram para WhatsApp/e-mail exige destino e finalidade validados. No YouTube, não prometer DM inexistente no escopo. No TikTok Shop, respeitar o atendimento e as transações dentro da plataforma, sem coletar dados para desvio comercial.

### Regra de concorrência

Serializar mensagens do mesmo caso e permitir paralelo entre casos distintos. O humano assume por registro explícito; o agente fica suspenso naquele atendimento. A memória geral nunca armazena pedido, dívida, dados pessoais ou histórico privado de clientes.

Base: [B1], pp.10,22,29; [S20] Eduzz; [S19] TikTok Shop. Modelo de dados proposto.

## 08. Modelo unificado de negócio
Não reduzir toda a operação a “lead”, “venda” e “pago”. O sistema precisa distinguir os objetos que representam o relacionamento e a obrigação.

| Objeto canônico | Informação essencial |
| --- | --- |
| Cliente e vínculo | customer_id, source_account, external_id, verification_ref, papéis, preferências e finalidades autorizadas. |
| Produto / oferta | product_id, IDs em cada plataforma, tipo físico/digital, offer_version, campanha e vigência. |
| Pedido / oportunidade | Origem, source_order_id, valor/moeda, itens, relação com CRM e referência ERP. |
| Contrato / financiamento | subscription_id ou billing_id, credor/provedor, responsável e relação com compra original. |
| Fatura / parcela | invoice_id ou bill_id, ciclo/número, vencimento efetivo, valor atual, status, obrigação substituída. |
| Pagamento / estorno | ID único, valor, moeda, data, status original, evidência e vínculo à fatura ou pedido. |
| Remessa / volume | Shipment/objeto, transportadora, código, eventos e atualização. Vários volumes por pedido. |
| Caso / ação / contato | Atendimento, objetivo, ação proposta/aprovada, tentativa, destinatário, retorno e pendência. |

Usar centavos inteiros ou decimal exato para dinheiro, nunca arredondamento livre do modelo. Preservar o status original do provedor e a interpretação canônica versionada. Uma condição desconhecida é um estado explícito.

LIA: pedido concluído não significa todas as parcelas pagas. Eduzz: uma fatura paga não quita toda a recorrência. Bling: código de rastreio não comprova entrega.

Modelo proposto. Semântica fundamentada em [S20–S27] e [B1], p.11.

## 09. Qual fonte responde cada pergunta
A autoridade é definida por informação e operação, não por um banco único que substitui todas as plataformas.

| Informação | Fonte prioritária | Conferência |
| --- | --- | --- |
| Histórico e responsável | Clint, no caso autorizado. | Não tratar etapa “ganho” como pagamento. |
| Produto e procedimento | RAG aprovada + catálogo de oferta vigente. | Versão, produto, campanha e permissão. |
| Pedido Yampi e transação | Yampi; ERP como vínculo operacional. | IDs correlacionados e atualização da fonte. |
| Pedido TikTok Shop | TikTok Shop para estado do marketplace; Bling para operação integrada. | Conflitos de logística/pagamento ficam visíveis. |
| Parcela LIA | Bill/billing/payment correspondentes na LIA. | Renegociação, vencimento, valor e liquidação. |
| Recorrência Eduzz | Contrato e faturas na Eduzz. | Pagador correto, ciclo e link aplicável. |
| Venda Assiny | Visão autorizada do BigData informado. | Cobertura e atraso de ingestão obrigatórios. |
| Rastreio | Bling e integração logística disponível. | Fonte do evento e horário; código ≠ postagem. |

Guardar source_updated_at, ingested_at e consulted_at. Consultar agora um dado importado ontem não o torna atual. Havendo conflito, pausar a afirmação ou a abordagem e encaminhar com ambas as evidências.

A mesma compra importada da Yampi ou do TikTok Shop para o Bling conta uma vez. Os espelhos são vínculos, não novas receitas.

Desenho proposto; integrações declaradas em [U]. Referências: [S20–S29], [S33–S35].

## 10. Contrato das ferramentas
O modelo pede uma operação de negócio. O serviço decide o recurso permitido, consulta a fonte e retorna somente o necessário.

| Família lógica | Operações planejadas |
| --- | --- |
| Conhecimento | buscar_conhecimento; consultar_oferta_vigente; registrar_lacuna. |
| Identidade e CRM | resolver_vinculo; consultar_contexto_autorizado; registrar_caso; assumir_humano. |
| Comércio e logística | consultar_pedido; consultar_evidencia_pagamento; consultar_remessas; obter_link_existente. |
| Financeiro restrito | consultar_fatura; consultar_parcela; verificar_renegociacao; obter_segunda_via_existente. |
| Canal | responder_comentario; responder_chat; moderar_alvo; enviar_email; enviar_whatsapp_elegivel. |
| Controle | avaliar_elegibilidade; reservar_contato; consultar_resultado_acao; registrar_pendencia. |

### Entrada vinculada no servidor

execution_id, tenant/account, case_id, identidade verificada, finalidade, recurso permitido e ação aprovada compõem o contexto confiável. Não aceitar que o modelo escolha livremente um destinatário, SQL, URL, credencial ou outro cliente.

### Retorno estruturado

status: sucesso, ausência, ambiguidade, sem permissão, indisponível, desatualizado ou resultado incerto. Incluir referência da fonte, horário, escopo e evidence_id. O texto do agente precisa ser compatível com esse retorno.

Nomes nesta página são contratos propostos, não endpoints confirmados. A implementação deve mapear cada contrato ao schema real da API/MCP.

Para informação financeira, exigir evidência válida daquela fatura/parcela. Token preenchido, health check ou flag de capacidade não substituem consulta ao recurso autorizado.

Base: [B1], pp.9–11; [B2], F03/F04. Desenho de integração desta versão.

## 11. Eventos, filas e efeitos externos
Receber duas vezes é normal em integrações. Enviar duas vezes por causa disso é um defeito a prevenir.

```text
recebido → validado → persistido → enfileirado
→ processando → proposto → autorizado
→ reservado → solicitado ao provedor
→ confirmado / falhou / resultado incerto
```

Validar assinatura no corpo bruto, tamanho e origem autorizada; persistir o evento antes do ACK. Separar lotes em eventos individuais. Um texto inválido vai para quarentena rastreável, não para o modelo sem validação.

| Situação | Tratamento exigido |
| --- | --- |
| Duplicata ou replay | Chave única por provedor/conta/evento. Idempotência também na ação de saída, não só na entrada. |
| Fora de ordem | Preservar datas/versão; consultar estado atual antes de agir. Um evento antigo não desfaz pagamento recente. |
| Timeout após envio | Registrar resultado incerto e reconciliar a ação; não repetir cegamente nem afirmar que foi entregue. |
| Reinício | Retomar fila e outbox persistentes; leases expiram de forma controlada; ações em voo são conciliadas. |
| Planilha/telemetria fora do ar | Atendimento mantém estado no banco. Exportações ficam pendentes, sem novo envio ao cliente. |
| Limite do provedor | Backoff com jitter, Retry-After quando fornecido, limite de tentativas e fila de erro. |

O Bling documenta webhooks sem garantia de ordem, ACK em até 5 segundos e retentativas por até 3 dias. Eduzz e LIA têm contratos próprios de assinatura. Não aplicar um único algoritmo de HMAC por conveniência.

Intake, MCP, workers e parada de emergência precisam usar o mesmo estado/configuração previstos. Testes usam diretórios temporários, nunca removem o kill switch real.

Base: [B1], pp.22,30; [B2], F05/F06. Webhooks: [S22], [S27], [S33].

## 12. Autorização por ação
Leitura, envio, moderação, financeiro e alteração de conhecimento são permissões separadas.

| Classe | Exemplo | Condição de liberação |
| --- | --- | --- |
| Leitura contextual | FAQ, pedido do cliente, fatura autorizada. | Escopo mínimo, identidade e fonte; sem listagem global ao atendimento. |
| Resposta de baixo risco | Agradecimento ou FAQ sustentada. | Canal elegível, regra aprovada, destinatário correto. |
| Efeito de moderação | Ocultar/rejeitar/excluir ou banir. | Método do canal, motivo, autonomia explícita e registro. |
| Comunicação financeira | Segunda via ou lembrete permitido. | Obrigação atual + pagador + canal elegível + cadência + aprovação. |
| Mudança econômica | Renegociar, estornar, emitir fatura, tentar débito. | Fora da autonomia inicial; processo humano separado. |
| Mudança de conhecimento | Publicar prompt, skill ou documento RAG. | Versão exata aprovada, testes e permissão de publicação. |

O tipo de tarefa vem do executor. Um follow-up agendado continua proativo mesmo se o modelo disser o contrário. Campos obrigatórios e enums ajudam, mas não substituem a verificação contextual.

Permissões devem considerar canal e fornecedor. Uma ação permitida no e-mail pode ser proibida no WhatsApp ou no chat do marketplace. A sessão não recebe ferramentas de manutenção de servidor ou consulta irrestrita à base.

Falhar fechado significa impedir o efeito arriscado e registrar a pendência. Não significa perder eventos, silenciar todos os clientes ou impedir ajuda simples.

Base: [B1], pp.8–10,29–31; [B2], F02/F04. Regras propostas; restrições externas [S19], [S30].

## 13. Meta: preservar o escopo original
Facebook e Instagram, orgânico e anúncios, continuam sendo entregas do projeto. A expansão não os transforma em itens opcionais.

Implementar adaptadores para comentários e mensagens das contas autorizadas. Manter diferença explícita entre resposta pública, resposta privada associada ao comentário e conversa no Direct/Messenger. Uma função chamada “privada” precisa provar destino privado no teste integrado.

| Necessidade | Regra de implementação |
| --- | --- |
| Monitoramento | Webhooks e reconciliação conforme API/conta; eventos assinados, IDs originais e cobertura por página/perfil. |
| Comentários de anúncios | Resolver anúncio, criativo, publicação e relações compartilhadas. Não atribuir ad_id por aproximação. |
| Classificação | Positivo, neutro e negativo + subcategoria + intenção + risco. Baixa certeza vai para revisão. |
| Moderação | Crítica legítima é atendida. Abuso, spam e golpe seguem política aprovada; ocultar e excluir não são sinônimos. |
| Privado e janela | Verificar login, versão, escopo e elegibilidade reais. Não transportar uma regra universal de 24 horas para toda superfície. |
| Autoria e destinatário | Vincular conta, comentário, autor e sessão no servidor; bloquear alvo de outro caso. |

### Dados e acompanhamento

Preservar link do anúncio, publicação e comentário quando fornecidos ou verificáveis. A interação é única; múltiplos anúncios podem apontar para ela sem multiplicar receita ou comentários. Conteúdos sem origem conhecida permanecem não atribuíveis.

Exigir prova de instalação e permissões antes de habilitar ações. Documentação e testes simulados não comprovam App Review, acesso à conta ou publicação no destino real. A versão do adaptador fica registrada no Langfuse e no banco.

Ao surgir suporte durante a venda, o atendimento tem prioridade. O agente não usa uma reclamação de entrega como pretexto para insistir em outra oferta.

Requisitos preservados de [B1], pp.5,15–20 e [B2], T02/T03/T11/T12. Homologação Meta permanece específica da conta.

## 14. YouTube: vídeos e comentários
Adicionar um adaptador de comentários de vídeos, incluindo Shorts quando o recurso estiver disponível, sem fingir que existe a mesma interface do Instagram.

| Método documentado | Uso no projeto |
| --- | --- |
| commentThreads.list | Listar threads do canal/vídeo com paginação. Custo documentado: 1 unidade; até 100 resultados por página. |
| comments.list | Completar respostas que não vieram no thread. Reconciliar novas respostas em publicações antigas. |
| comments.insert | Responder ao comentário autorizado usando parentId. Operação de escrita com quota própria. |
| comments.setModerationStatus | published, heldForReview ou rejected, conforme permissão do dono do conteúdo. |
| comments.delete | Exclusão pelo autor do comentário. Não tratar como botão universal para apagar comentário de terceiros. |

Para terceiros no canal, a moderação se apoia no método de status. A rejeição não equivale a um ocultamento reversível genérico: a documentação informa que o mesmo método não restaura um comentário rejeitado para publicado. Banir autor afeta mais que uma mensagem e exige autorização específica.

### Fluxo proposto

Descobrir vídeos autorizados, ler comentários com checkpoint, completar respostas, classificar o que estiver permitido, preparar resposta contextual e executar pelo dono correto. Não responder automaticamente a todo emoji nem repetir CTA em massa.

O mecanismo de push de vídeos documentado não é um webhook universal de comentários. Prever polling e reconciliação com orçamento. Comentários desabilitados ou acesso negado são estados explícitos, não erro para contornar por scraping.

Não foi identificado, nas APIs adotadas para este escopo, um canal de DM de atendimento equivalente ao Instagram. Dados individuais não serão solicitados nos comentários.

Documentação pública: [S06–S10]. Regras de coleta/analítica e conta: [S13–S15].

## 15. YouTube: lives e orçamento de API
Chat ao vivo é um fluxo distinto dos comentários sob o vídeo. Tem IDs, ciclo de vida, permissões e controles de velocidade próprios.

| Recurso | Implementação prevista |
| --- | --- |
| liveChatMessages.streamList | Recepção em streaming quando compatível com a conta, preservando token de continuidade e IDs para deduplicar. |
| Leitura alternativa | Método de listagem com intervalo indicado pelo provedor, quando utilizado. Não consultar mais rápido que o permitido. |
| liveChatMessages.insert | Publicação no chat autorizado, com contexto da live e limite de intervenções. |
| liveChatMessages.delete | Remover mensagem somente com papel permitido de dono/moderador. |
| liveChatBans.insert | Sanção temporária ou permanente, separada de excluir mensagem e sujeita a política de alto impacto. |

Descobrir a live ativa e seu liveChatId; não tentar escrever em chat encerrado. Separar fila de live do restante para que um pico de mensagens não impeça atendimento de pedidos. Priorizar risco, dúvidas recorrentes e informação útil; humano deve poder assumir imediatamente.

### Quota é requisito de capacidade

A documentação descreve orçamento padrão de 10.000 unidades/dia para outros endpoints, além de limites específicos para alguns métodos. Conferir a quota efetiva do projeto. comments.insert e setModerationStatus custam 50 unidades por chamada nas referências consultadas; não planejar milhares de respostas sem dimensionamento.

Exemplo apenas aritmético: 100 chamadas de resposta a 50 unidades consomem 5.000 unidades, antes das leituras e outras ações. Reservar orçamento para moderação e filas pendentes; não espalhar tráfego por projetos para contornar limites.

Ação pública deve agregar valor à live. Atendimento financeiro vai para o caminho privado permitido, sem anunciar atraso, valor ou existência de dívida no chat.

Métodos e quotas: [S07], [S08], [S11–S13]. Desenho de prioridade e filas é proposta do projeto.

## 16. YouTube: dados e métricas condicionadas
A política de dados não pode ser tratada como detalhe posterior à mineração ou ao dashboard.

As políticas adicionais de métricas derivadas permitem casos como análise agregada de sentimento, sob as condições do aditamento e do caso de uso aceito. O guia da plataforma exige aprovação para as possibilidades ampliadas. Não presumimos que a conta do projeto tenha essa autorização.

| Dado ou uso | Regra de ativação |
| --- | --- |
| Moderação e resposta | Usar o acesso e os métodos autorizados para o canal. Registrar somente o necessário à operação. |
| Dashboard de sentimento | Habilitar métricas derivadas de YouTube apenas após validar o caso de uso e os termos aplicáveis. Identificar que são métricas próprias. |
| Texto de comentários e metadados | Aplicar a regra de atualização ou exclusão em 30 dias nas condições dos termos. Não copiar indefinidamente para arquivo ou telemetria. |
| Métricas históricas ampliadas | O aditamento pode permitir certas métricas por até 36 meses para clientes aceitos; isso não amplia automaticamente a guarda de texto. |
| Mineração e RAG | Controlar proveniência, uso permitido e exclusão. RAG permanente com comentários brutos do YouTube não é aprovada por padrão. |

### Consequência arquitetural

Tags de origem e política acompanham o dado no banco, planilha, Langfuse, cache e material de avaliação. Exclusão/atualização precisa alcançar cópias e documentos derivados quando exigido. Não aplicar a retenção geral da Clint a tudo que veio do YouTube.

Manter as 3 categorias de sentimento do projeto nas superfícies autorizadas. No YouTube, separar triagem operacional da publicação de análises agregadas e não inferir características protegidas da audiência.

Até a validação, não liberar um pipeline irrestrito de comentários do YouTube para perfilamento, RAG ou analítica histórica. A equipe pode operar o escopo efetivamente autorizado.

Condições de plataforma: [S14], [S15], [S40]. Recomendações de implementação propostas, não aprovação concedida pelo YouTube.

## 17. TikTok Shop: capacidade por loja
A existência de credencial para pedidos não comprova autorização para atendimento. O escopo deve ser verificado no Partner Center e na loja brasileira.

A documentação pública indexada apresenta o escopo seller.customer_service e recursos de conversas. Também há referência oficial ao envio de mensagens. Algumas páginas completas do portal são dinâmicas/restritas; contratos, webhooks e regras finais devem ser conferidos com o acesso autorizado.

| Capacidade | Estado nesta especificação |
| --- | --- |
| Consultar conversa | Método documentado: GET /customer_service/202601/conversations/{conversation_id}; vincular à loja e ao comprador autorizado. |
| Ler/enviar mensagens | Recurso de atendimento documentado; referência oficial a /customer_service/202309/conversations/{conversation_id}/messages. Homologar método e schema do app. |
| Eventos de mensagens | Configurar assinatura, assinatura do webhook e repetição conforme contrato disponibilizado à conta; não inventar payload universal. |
| Pedidos e pós-venda | Consultar estado do marketplace e correlacionar com Bling. Cliente/ordem são da loja correta. |
| Vídeos, lives, avaliações e DMs sociais | Não presumidos no escopo de Shop. Exigem capacidade separada; atendimento de loja não concede moderação geral do TikTok. |

A versão de um endpoint não é a versão de toda a API. Fixar e testar cada recurso com app_key, token de acesso, assinatura e identificação de loja exigidos. Permissões regionais, acesso de parceiro e configuração da conta podem limitar a implantação.

Antes de assumir o chat da loja: listar permissões reais, receber uma conversa de teste, responder pelo caminho autorizado e confirmar a mensagem no Seller Center.

Referências públicas: [S16–S18]. API disponível e integração existente são relatos do usuário [U], não homologação desta revisão.

## 18. TikTok Shop: atendimento no canal certo
O atendimento pode consultar o Bling internamente, mas a interação comercial do marketplace deve respeitar as regras do próprio TikTok Shop.

A política brasileira de atendimento proíbe desvio para transações fora da plataforma, solicitação indevida de informações pessoais e pagamentos adicionais ligados ao pedido. Essa restrição entra no motor de autorização, não somente no texto de uma skill.

| Situação | Conduta do agente |
| --- | --- |
| “Onde está meu livro?” | Consultar pedido Shop e remessa vinculada no Bling; informar o estado confirmado pelo chat da loja. |
| “Quero comprar outro item” | Orientar pelo catálogo/caminho autorizado no TikTok Shop; não substituir por checkout externo para evitar o marketplace. |
| “Já paguei, estão pedindo taxa” | Não criar taxa nem enviar boleto externo. Verificar a origem e encaminhar conforme processo do marketplace. |
| Reembolso / devolução | Explicar procedimento vigente e encaminhar solicitações nos mecanismos próprios; sem prometer estorno não autorizado. |
| Avaliação negativa | Atender o problema, não manipular avaliações nem prometer exclusão de review de terceiro. |
| Dados de contato | Não extrair comprador para campanhas externas de recuperação. Dados disponíveis ficam limitados à finalidade permitida. |

### Coordenação com o ERP

O Bling documenta importação de pedidos TikTok Shop e envio de informações fiscais/logísticas, conforme configuração. Aproveitar o vínculo já informado pelo usuário; não recriar o pedido, reenviar nota ou movimentar estoque só porque houve atendimento.

Sem seller.customer_service homologado, manter a frente em preparação e atendimento humano no Seller Center. Não substituir a API por automação de navegador para contornar ausência de escopo.

Política brasileira: [S19]. Integração ERP: [S34]. Fluxos e controles propostos.

## 19. Clint: continuidade e operação humana
O CRM continua sendo a referência do relacionamento. Não passa a ser o comprovante universal de pagamento.

Consultar somente cadastro mínimo, contexto pertinente, oportunidade, responsável e preferências necessários ao caso. O MCP/API real deve ser inventariado: leitura de conversas, campos e escrita permitida variam com a integração disponível.

| Fluxo | Contrato esperado |
| --- | --- |
| Identificação | Associar conta/canal/cliente ao contato correto, com verificação proporcional ao dado financeiro ou pessoal. |
| Contexto de atendimento | Buscar resumo e pendências relevantes; não carregar conversas de toda a operação no contexto do modelo. |
| Registro | Salvar resumo, ação, referências de fonte e próxima etapa nos campos autorizados. Evitar automações laterais não aprovadas. |
| Handoff | Criar fila/caso e identificar responsável. Ao humano assumir, pausar respostas automáticas do mesmo atendimento. |
| Outros canais | Registrar referências de YouTube/Shop quando houver capacidade legítima; não prometer que toda conversa aparecerá nativamente na Clint. |
| Mineração | Credencial separada e somente leitura. Acesso analítico a todos os WhatsApps não autoriza responder em todos eles. |

### Uma só resposta para o cliente

A Clint, o canal nativo, a Evolution e workflows não podem ser emissores independentes para o mesmo evento. Definir ownership por número, caso e tipo de comunicação. Eventos de eco retornam ao histórico sem iniciar loops.

Caso a escrita na Clint não exista para um objeto, manter registro no banco e sinalizar sincronização pendente. Não afirmar que o CRM foi atualizado sem retorno confirmado. A equipe precisa ver a pendência e não perder a continuidade.

Objetivo: o humano recebe contexto, consultas e tentativas já feitas. O cliente não precisa explicar tudo de novo para cada ferramenta.

Requisitos preservados: [B1], pp.9–10,17,22,25–29. Capacidades reais da Clint dependem do MCP/API contratado.

## 20. Bling: operação e vínculos de pedidos
Yampi e TikTok Shop já integrados ao Bling, conforme informado. A nova arquitetura deve aproveitar esses caminhos, não duplicá-los.

| Informação | Interpretação correta |
| --- | --- |
| Pedido importado | Registro operacional associado a source_order_id e canal de origem. Não é uma nova venda além da original. |
| Situação do pedido | Status configurado no ERP. Não basta para concluir pagamento, financiamento liquidado ou marketplace repassado. |
| Pagamento | Usar evidência financeira validada e vinculada; reconciliar com a plataforma da transação quando houver divergência. |
| Remessas | Código, transportadora, volumes e eventos retornados. Código emitido, postado, em trânsito e entregue permanecem distintos. |
| Nota e estoque | Somente consulta pertinente. Emissão fiscal, baixa, cancelamento e movimentação ficam fora da autonomia inicial. |
| Desalinhamento | Retornar conflito com fontes e horários. Não escolher o valor/status mais conveniente para responder. |

### Evitar efeitos duplicados

Os conectores existentes podem enviar nota, status e rastreio às plataformas e ao cliente. Antes de adicionar uma notificação, verificar quem já envia. O agente de atendimento consulta o vínculo e usa o retorno; não dispara nova expedição.

### Recepção confiável

Para os recursos de webhook disponíveis no Bling, validar a assinatura do provedor, confirmar recebimento rápido após persistir e reconciliar fora de ordem. A implantação deve mapear quais módulos realmente geram eventos; não assumir webhook de liquidação para qualquer status de pedido.

O serviço de consulta retorna evidência por pedido e cliente. Uma flag “Bling disponível” não autoriza o agente a afirmar que todos os pedidos estão pagos.

Base: [B1], pp.11,14,29. Documentação: [S33–S35]. Integrações em uso informadas em [U].

## 21. Yampi: pedido, pagamento e abandono
Adicionar o conector de comércio para consultar a origem da venda e, em fase posterior, recuperar oportunidades elegíveis.

| Evento/recurso documentado | Uso planejado |
| --- | --- |
| order.created | Registrar pedido iniciado; não classificar como receita recebida. |
| order.paid | Atualizar evidência de pagamento e retirar o pedido de ações pendentes de recuperação. |
| order.status.updated | Reconciliar estado e sincronização, sem substituir a semântica da transação. |
| transaction.payment.refused | Identificar tentativa recusada. Não cobrar novamente o cartão por conta própria. |
| cart.reminder | Candidato de recuperação de carrinho, condicionado à disponibilidade, à oferta e ao contato permitido. |
| Pedido / transações / rastreio | Consulta por API para confirmar estado atual e obter referências válidas do atendimento. |

Distinguir carrinho abandonado, pedido aguardando pagamento e obrigação exigível. A ausência de compra confirmada não significa dívida. Antes de uma retomada, verificar se a compra ocorreu na Yampi ou por outro caminho equivalente.

### Link de retomada e dados privados

Usar somente o link existente autorizado para aquele carrinho/pedido, com verificação de destinatário e validade. Payloads podem conter URLs privadas; não publicar tokens, links autenticados ou dump integral em planilhas ou no Langfuse.

A Yampi possui recursos nativos de comunicação/recuperação. Inventariar o que já está ativo e coordenar o dono de cada toque com Clint, e-mail e agente. Não desligar nem duplicar rotinas automaticamente.

O agente não recebe ferramentas de captura, confirmação manual de pagamento ou estorno. A integração comercial inicial é de leitura, eventos e comunicação permitida.

Fontes oficiais: [S28], [S29], [S35]. Desenho de recuperação condicionado ao escopo futuro [U].

## 22. LIA: atender a parcela correta
A integração será com a LIA utilizada para financiamento dos cursos. A unidade financeira não é somente o pedido original.

```text
pedido (order) → financiamento (billing)
→ parcelas (bills) → pagamentos (payments)
```

| Consulta | Resultado necessário |
| --- | --- |
| Bill/parcela | ID, vencimento efetivo, valor atual, status, referência do financiamento e pagamento disponível. |
| Billing/financiamento | Estado vigente, parcelas associadas e substituições/renegociações. |
| Payment | Meio e evidência de liquidação. Tentativa iniciada e documento gerado não são pagamento. |
| Segunda via existente | Usar o recurso de download do boleto vinculado ao payment, quando aplicável; não gerar um novo financiamento. |
| Link de pagamento | Obter referência existente correspondente à parcela vigente. Não substituir por checkout genérico de nova venda. |

A documentação pública apresenta GET /external_api/v1/bills/:id e download de boleto de payment. Campos de valor usam centavos nas referências consultadas. O adaptador deve mapear datas efetivas e status, sem recalcular juros ou saldo por interpretação da IA.

### Fluxo de assistência

Identificar o responsável no privado, consultar a obrigação, verificar se já está paga, cancelada, renegociada ou contestada e só então disponibilizar documento/link pelo canal permitido. Se faltar vínculo ou retorno confiável, abrir atendimento humano.

Boleto já existente deve ser consultado e reutilizado quando válido. Mandar um novo checkout de venda pode criar duplicidade de contrato, não resolver a parcela atual.

Documentação LIA: [S23–S25]. Uso comercial da LIA relatado pelo usuário [U].

## 23. LIA: renegociação e responsabilidade
O acompanhamento precisa observar billing e bill, não apenas a transição do pedido.

No fluxo de renegociação documentado, nasce um novo billing e o anterior é cancelado com motivo customer_renegotiation. O pedido pode permanecer finished. Logo, observar somente o pedido deixa a rotina sem perceber que as parcelas e os links antigos foram substituídos.

| Evento/situação | Comportamento exigido |
| --- | --- |
| Nova renegociação | Vincular origin_billing_id e novo billing. Suprimir ações das parcelas substituídas e reavaliar a obrigação atual. |
| Parcela paga | Cancelar mensagens pendentes daquela parcela; registrar evidência. Não marcar todo contrato quitado automaticamente. |
| Comprovante enviado | Suspender pressão e confirmar na fonte. Imagem ou texto do cliente não autorizam baixa financeira. |
| Disputa ou erro de identificação | Pausar abordagem e transferir com evidências mínimas. Não insistir enquanto o vínculo estiver ambíguo. |
| Dado atrasado / API indisponível | Sem contato financeiro automático até existir fonte suficientemente atual. |

### Quem conduz a cobrança?

A LIA também oferece serviço próprio de cobrança. Antes de qualquer rotina do agente, definir contratualmente quem é responsável por cada obrigação e canal. A arquitetura deve consumir o estado e coordenar contatos; não competir com a régua do financiador.

Validar webhooks com o contrato de assinatura efetivo da LIA e exemplos assinados do ambiente. Registrar novas parcelas e mudanças de status mesmo sem mudança no order. Campos e algoritmos seguem o fornecedor, não um esquema genérico inventado.

Negociar desconto, reemitir obrigação, alterar vencimento, criar outro financiamento ou assumir compromisso financeiro permanece fora da autonomia inicial.

Renegociação: [S26]. Webhooks: [S27]. Serviço de cobrança: [S36]. Controles propostos para o projeto.

## 24. Eduzz: recorrência por fatura
Contrato ativo, situação de acesso e pagamento de cada ciclo são fatos relacionados, mas diferentes.

| Recurso documentado | Uso no projeto |
| --- | --- |
| myeduzz.contract_updated | Acompanhar mudanças do contrato e seus estados, como upToDate, awaitingPayment, late, canceled, defaulter, suspended, trial, finished e free. |
| myeduzz.invoice_paid | Atualizar a fatura liquidada e retirar suas ações pendentes. Preservar invoice/subscription e evidência original. |
| GET /myeduzz/v1/subscriptions/:id/invoices | Consultar faturas do contrato. Escopo documentado: myeduzz_subscriptions_read. |
| customer / financialResponsible | Distinguir aluno/cliente do responsável financeiro antes de revelar valores, atraso ou instruções de pagamento. |

O produto recorrente informado pelo usuário deve ser identificado por ID, plano e contrato. Filtrar estados de fatura explicitamente; incluir processamento, estorno, negociação e cancelamento na análise antes de chamar algo de inadimplente.

### Atenção ao link de pagamento

A referência de faturas documenta payment.link quando a fatura está aberta. Não presumir que toda fatura vencida ou expirada terá link. Sem referência válida, orientar o caminho oficial de regularização ou encaminhar; não montar URL nem criar uma nova assinatura.

Os webhooks da Eduzz têm verificação de assinatura própria. Usar payload assinado, deduplicar evento, reconciliar por leitura e não depender exclusivamente da ordem de chegada para decidir contato.

Permissão de consultar a recorrência não autoriza tentar débito, cancelar contrato, alterar acesso ao curso ou negociar valores pelo agente.

Documentação Eduzz: [S20–S22]. Recorrência existente informada pelo usuário [U].

## 25. Regularização: uma máquina de estados
O modelo escreve e conversa. O executor financeiro determina se existe uma obrigação elegível e se o contato pode ocorrer.

[Diagrama da arquitetura no PDF.]

| Bloqueio antes do contato | Efeito |
| --- | --- |
| Pago, estornado, substituído ou contestado | Cancelar ou pausar ações conforme a obrigação e o evento. Nunca cobrar por mera ausência em cache. |
| Fonte vencida, incompleta ou fora do ar | Marcar não confirmado e abrir reconciliação. Nenhuma afirmação financeira especulativa. |
| Pagador/destino não verificados | Exigir confirmação segura. Não revelar débito em público ou a aluno/terceiro. |
| Canal ou finalidade proibidos | Não enviar, mesmo com template, credencial ou interesse comercial. |
| Humano/rotina nativa no comando | Respeitar dono do contato, reserva da ação e limite global. |

Antes do envio, revalidar status e versão da obrigação, reservar a ação e verificar novamente eventos supervenientes. Um pagamento recebido cancela pendências ainda não enviadas. Mensagem já entregue não pode ser desfeita; registrar a corrida e impedir novos toques.

Cobrar, neste escopo, não significa executar um débito financeiro. Significa prestar assistência e comunicar regularização apenas quando juridicamente e contratualmente permitida.

Fluxo proposto. Semântica LIA/Eduzz: [S20–S27]. Elegibilidade de canal e cobrança: [S30], [S37], [S38].

## 26. Assiny: consulta pelo BigData interno
Respeitar o caminho informado: as vendas Assiny serão consultadas no BigData da operação, sem presumir uma API transacional disponível.

Dependência não resolvida nesta pesquisa: provedor do BigData, datasets, tabelas, chaves, frequência de atualização, origem da carga e campos de Assiny. Não presumir BigQuery, PostgreSQL ou outro produto. Esse contrato precisa ser disponibilizado pelo time de dados.

| Contrato da visão autorizada | Requisito |
| --- | --- |
| Identificação | Conta, ID original da venda, cliente vinculado, produto/oferta e evento financeiro. Chaves para correlacionar outras plataformas. |
| Estado e tempo | Status original + interpretação; source_updated_at, ingested_at, consulted_at e cobertura consolidada até determinado instante. |
| Pagamento e exceções | Evidências de aprovado, recusado, pendente, estorno, cancelamento e divergências quando a carga realmente incluir essas informações. |
| Acesso | View/API de leitura com parâmetros fechados, filtros por cliente e limite. Não expor console de SQL ou base inteira ao agente. |
| Falta de dado | Separar “registro não encontrado em cobertura completa” de “carga incompleta/desatualizada”. Nenhum deles vira dívida automaticamente. |

### O risco de recuperar quem já comprou

Um pagamento recente pode ainda não ter chegado ao BigData. Por isso, a rotina de recuperação precisa de política de frescor e cobertura, supressão por sinais positivos de compra e pausa quando não for possível confirmar a ausência da compra. Não basta consultar uma tabela e obter zero linhas.

Gerar alertas de ingestão atrasada e interromper automações dependentes. O time define o atraso máximo tolerável por ação a partir da carga real; este documento não inventa um SLA de atualização.

BigData é uma fonte derivada e controlada, não prova automática do estado financeiro atual. A decisão de contato deve carregar a idade e a cobertura da evidência.

Caminho da Assiny definido pelo usuário [U]. Schema e SLA internos não acessados; contrato proposto nesta versão.

## 27. WhatsApp: finalidade antes do envio
A escolha técnica entre Evolution API e canal nativo não substitui a política de comunicação do WhatsApp.

Na política oficial consultada, “debt collection” consta entre os serviços restritos/proibidos. Assim, este mestre não libera cobrança automática de dívidas por WhatsApp. Distinguir, com validação de negócio, jurídica e de plataforma, um lembrete legítimo de serviço de uma atividade proibida; trocar o nome para “utility” não resolve o enquadramento.

| Tipo de uso | Regra de ativação |
| --- | --- |
| Atendimento solicitado | Usar somente dados autorizados e conteúdo permitido; preservar a janela e as opções de escalonamento humano. |
| Lembrete transacional | Exige classificação correta, destinatário e finalidade válidos, além das condições da plataforma. |
| Recuperação de venda | Depende de consentimento, oferta, janela/template e exclusões. Não é autorização para disparar a toda a base. |
| Cobrança de dívida | Bloqueada nesta especificação para WhatsApp. Reavaliar apenas contra regra aplicável documentada, não promessa informal de fornecedor. |

A Platform exige templates aprovados para iniciar conversas e para mensagens fora da janela de atendimento de 24 horas. Opt-in e opt-out continuam relevantes. Aprovar um template não torna permitido um serviço proibido.

### Transporte e coexistência

Inventariar números atuais da Clint. Escolher uma rota de envio por conta: Evolution com transporte identificado ou canal nativo do OpenClaw. “Nativo” não deve ser confundido com Cloud API oficial. Não usar sessão Web ou outro número como forma de contornar política.

A frente financeira pode iniciar com consultas, atendimento supervisionado e canais permitidos, como portal oficial/e-mail quando adequados. Isso não reduz a exigência de dados atuais ou de conformidade.

Política oficial WhatsApp consultada em 24/09/2026: [S30]. Transporte a homologar; decisões preservadas [B1], p.12.

## 28. Comunicação: coordenação de contatos
Uma pessoa não deve receber cobranças ou ofertas duplicadas porque comprou por fontes que espelham dados ou porque vários sistemas estão ativos.

Criar um coordenador de contatos compartilhado pelos executores autorizados. Ele mantém finalidade, obrigação/oportunidade, canal, remetente, sequência, última tentativa, próxima ação e quem é responsável pelo contato. IDs e estados não dependem da memória do modelo.

| Sistema já presente | Coordenação exigida |
| --- | --- |
| LIA | Confirmar responsabilidade contratada do financiador e suas comunicações. Não duplicar a régua nativa. |
| Eduzz | Mapear retentativas/notificações de recorrência e recuperação antes de adicionar contatos do agente. |
| Yampi / Bling | Identificar lembretes de carrinho, confirmação, nota e rastreio já enviados. |
| Clint / n8n / canal | Definir um único executor para cada mensagem e suspender concorrência quando humano assumir. |
| Nova campanha | Consultar supressões e cadência global; não somar toques independentes por produto indiscriminadamente. |

### E-mail corporativo

Definir provedor, remetente, autenticação do domínio, gestão de bounce, opt-out de marketing, anexos e links aprovados. Conteúdo financeiro exige pagador/destinatário verificado e finalidade permitida. Não presumir que a caixa Gmail pessoal da sessão é o remetente do projeto.

Guardar ID do provedor, estado e horário. Aceito, entregue, lido e respondido são estados diferentes. A confirmação de envio deve vir da ferramenta; falhas ficam em outbox/reconciliação sem disparo cego.

Cadência, horários e limites serão aprovados por finalidade e localidade. Nenhum número de toques sugerido deve ser apresentado como limite legal universal.

Base: [B1], pp.12–14 e 22. Serviços/fontes: [S28], [S34–S38]. Coordenação proposta.

## 29. Recuperação futura: 5 jornadas
A expansão prepara o sistema para recuperar vendas de perpétuo e lançamentos, mas a ativação será posterior e por campanha aprovada.

| Jornada | O que significa | Regra de exclusão |
| --- | --- | --- |
| Carrinho abandonado | Interesse sem compra concluída. | Não há dívida por presunção; retirar quem comprou oferta equivalente. |
| Primeiro pagamento recusado | Tentativa de compra falhou. | Sem débito automático; oferecer caminho válido quando houver interesse. |
| Pagamento pendente | Pedido iniciado com meio ainda não liquidado. | Verificar validade, cancelamento e pagamento recente antes de orientar. |
| Recorrência / parcela | Obrigação específica existente. | Regras financeiras próprias; não tratar como simples campanha promocional. |
| Lead inativo / lançamento | Contato anterior elegível para retomada. | Consentimento, oferta vigente, recusa, suporte aberto e frequência global. |

Cada campanha deve declarar público elegível, produto, oferta/versionamento, início/fim, canal permitido, responsáveis, mensagens, critérios de saída e métrica de resultado. Sem oferta atual, não reutilizar preço, bônus ou escassez de lançamento encerrado.

### Supressão multiorigem

Antes de enviar, verificar Yampi, Shop, LIA, Eduzz e Assiny/BigData conforme o produto e o vínculo legítimo. A compra equivalente por outra plataforma suprime a recuperação; não precisa suprimir suporte de outro pedido. Bases incompletas ou atrasadas bloqueiam decisões que dependem delas.

No TikTok Shop, não levar a recuperação para checkout externo ou usar dados de compradores para desvio comercial. Cada jornada respeita a política da fonte e do canal.

Medir venda assistida separadamente de venda incremental. Atribuição causal exige teste/controle adequado; o agente enviar um link antes de um pagamento não prova que causou a venda.

Ampliação futura definida em [U]. Capacidades: [S20–S29]. Política de marketplace/canais: [S19], [S30].

## 30. Exemplos de ponta a ponta
Cenários ilustrativos. Nenhuma mensagem abaixo foi enviada e nenhum status real de cliente foi consultado.

### 1 · YouTube: “Comprei e não recebi”

Registrar comentário e vídeo; não apagar a crítica. Responder sem revelar informações individuais: “Use o canal oficial de atendimento indicado para localizar seu pedido com segurança.” A equipe vincula o atendimento privado após confirmação. Não anunciar que enviou um Direct que a API não oferece.

### 2 · TikTok Shop: “Cadê meu rastreio?”

Identificar conversa e pedido autorizados da loja; consultar Shop e remessa correspondente no Bling. Responder pelo chat Shop com a atualização disponível. Se o código existe, mas não há evento de postagem, informar exatamente essa situação. Não pedir taxa ou pagamento externo.

### 3 · LIA: “Pode mandar meu boleto de novo?”

Validar responsável e financiamento; verificar se a parcela ainda está vigente. Recuperar link/segunda via existente. Se houve renegociação, descartar a parcela substituída. Enviar apenas pelo caminho permitido e registrar resultado. Não criar outro pedido de curso.

### 4 · Eduzz: fatura apontada em atraso

Consultar contrato, faturas e financialResponsible. Se a fatura foi paga antes do envio, cancelar a ação. Se não houver link aplicável, não fabricá-lo; encaminhar para o processo oficial. Atraso nunca é exposto ao aluno ou em comentário público por presunção.

### 5 · Assiny: sem venda encontrada na carga

Conferir cobertura e atraso do BigData. Se a carga está incompleta, não chamar a pessoa de não compradora nem iniciar recuperação dependente desse dado. Registrar bloqueio por frescor e retomar após reconciliação.

Todos os caminhos produzem a mesma trilha: caso → identidade → fonte → decisão autorizada → tentativa → resultado → próxima ação.

Exemplos derivados dos requisitos do projeto. Referências de capacidade: [S06–S29], [B1].

## 31. Langfuse no OpenClaw
Camada de observabilidade e avaliação. Não é o banco de pedidos, a RAG nem o motor que autoriza respostas.

O guia oficial do Langfuse descreve o Langfuse Bridge, integrado aos eventos de diagnóstico do OpenClaw para registrar execuções, modelos, ferramentas e recuperação. A adoção exige revisar procedência, fixar versão e testar compatibilidade com o runtime instalado.

| Camada observada | Instrumentação proposta |
| --- | --- |
| OpenClaw | Execução por turno, modelo, tokens, duração, erro e sessão de atendimento pseudonimizada. |
| MCP e serviços próprios | Propagar contexto do trace; registrar consulta Clint/Bling/LIA/Eduzz/Yampi/BigData e status técnico. |
| RAG | Consulta, filtros, document_id/versão e resultado. Não confundir ausência de conteúdo com falha da busca. |
| Autorização e envio | Motivo de bloqueio, versão da regra, action_id, tentativa e resultado do provedor. |
| Qualidade | Avaliação automática/humana vinculada à execução; casos de regressão e experimentos aprovados. |

O suporte a SDK/OpenTelemetry permite complementar o rastreio das ferramentas Python. Isso não altera o runtime para Agents SDK. O registro externo de uma chamada de ferramenta não mostra sozinho as tentativas internas: essas etapas precisam ser instrumentadas.

### Telemetria em paralelo

Manter fila/exportação assíncrona com limites. A indisponibilidade do Langfuse não pode gerar reenvio ao cliente ou derrubar o atendimento. O banco operacional continua guardando os eventos de auditoria indispensáveis.

OpenRouter Broadcast, quando adotado, observa chamadas do modelo; não substitui a instrumentação de RAG e integrações. Evitar exportar a mesma chamada duas vezes.

Referências Langfuse/OpenClaw: [S01–S05]. Arquitetura de exportação é proposta do projeto.

## 32. Langfuse: qualidade e privacidade
O painel deve explicar o trabalho observável, não expor dados financeiros nem prometer acesso infalível ao pensamento da IA.

| Registro | Conteúdo mínimo |
| --- | --- |
| Correlação | trace_id, run_id, case_id, action_id; cliente pseudonimizado e conta/finalidade autorizadas. |
| Versões | Código, modelo, instrução/skill, regra, RAG e documento utilizados. |
| Consulta | Fonte, evidência opaca, latência, erro e frescor. Evitar payload financeiro integral. |
| Resultado | Proposto, autorizado, solicitado, confirmado ou incerto. Pagamento e envio são eventos distintos. |
| Avaliação | Fidelidade à fonte, resolução, moderação correta, respeito à recusa, encaminhamento e próximo passo adequado. |

Aplicar mascaramento antes da exportação a textos, metadados e erros. Não exportar CPF, endereço, credenciais, documentos, boletos, linhas digitáveis, links autenticados ou dados sensíveis sem necessidade e autorização. Um ID com hash não anonimiza um texto identificável.

### Avaliações não são autorização

Nota do avaliador pode ser incorreta; calibrar com revisão humana. Uma boa taxa de venda não compensa promessa falsa, cobrança indevida ou vazamento. Feedback cria proposta de melhoria, nunca publicação automática de prompt/skill/RAG.

Manter inicialmente as instruções versionadas no Git e registrar a versão no Langfuse. Gestão remota de prompts pode vir depois, com versão/label explicitamente aprovados. O Social Seller não recebe MCP administrativo para ler todos os traces ou alterar seus próprios controles.

Definir hospedagem, região, acesso, retenção e custo antes de dados reais. O orçamento inclui modelo, avaliações e telemetria; custo estimado por tokens não é a fatura total.

Mascaramento e avaliações: [S02], [S03], [S39]. Gestão e implantação propostas, sujeitas à governança [S38].

## 33. RAG preservada, não substituída
Somente conhecimento geral aprovado. Pedidos, dívida e pagamento continuam em ferramentas de dados atuais.

| Material | Destino |
| --- | --- |
| Produtos, FAQ e procedimentos | RAG aprovada, com produto, escopo, fonte, versão e vigência. |
| Ofertas e campanhas | Coleção/documentos com validade; filtros impedem resposta com promoção encerrada. |
| Políticas de moderação e cobrança | Regras críticas no código/instruções; conteúdo explicativo recuperável e versionado. |
| Histórico individual e financeiro | Sistemas operacionais e contexto privado do caso, não corpus geral. |
| Pasta minerada na Clint | Fonte e evidência restritas, análises internas e candidatos após curadoria. |
| Candidatos antigos de treinamento | Sem fine-tuning. Reaproveitar exemplos desidentificados em testes quando permitidos. |
| YouTube e Shop | Usos sujeitos aos termos da fonte; não copiar tudo para a mesma retenção ou público de acesso. |

Auditar índice, embeddings, chunks, ingestão e ferramenta de consulta existentes antes de reconstruir. Integrar no OpenClaw a busca atual quando adequada. No Langfuse, guardar referências de fonte e versão, não uma cópia irrestrita de toda a base.

### Critério de resposta

Filtrar por aprovação, vigência, produto/campanha, finalidade e acesso. Sem fonte suficiente, esclarecer a dúvida ou encaminhar; nunca completar preço, parcela, prazo ou política por memória de uma conversa antiga.

Aprendizado contínuo não é autoalteração irrestrita. O agente atende com a versão aprovada; a curadoria propõe a próxima versão.

Base: [B1], pp.23–28; [B2], p.7. Limitações por origem: [S14], [S15], [S19].

## 34. Curadoria semanal ampliada
A rotina existente continua incremental. Novos canais e telemetria ajudam a descobrir lacunas, respeitando as permissões e políticas de cada origem.

```text
novidades autorizadas + resultados do agente
→ comparação com RAG e histórico
→ dúvida nova / falha de busca / problema operacional
→ proposta com evidência e versão
→ revisão → testes → publicação autorizada
```

| Etapa | Regra preservada ou ampliada |
| --- | --- |
| Cobertura | Inventariar todos os WhatsApps autorizados da Clint; declarar sem novidade, inacessível ou desconectado. |
| Retomada | Checkpoint por canal/objeto; sobreposição inicial de 48h; deduplicar e cobrir semanas perdidas. Não reiniciar a extração inteira. |
| Novas origens | Acrescentar interações permitidas de Shop/YouTube e resultados Langfuse, sem presumir direito de uso permanente. |
| Análise | Separar pergunta inédita, nova formulação, falha de recuperação, informação vencida e erro de integração. |
| Aprovação | Proposta ligada ao hash/versão exata, fonte e responsável. Alteração posterior invalida a aprovação. |
| Publicação | Somente o aprovado e autorizado; atualizar o que mudou, testar e manter reversão. Drafts/rejeitados fora do índice de produção. |

Cada rodada registra cobertura, aprendizados, prioridades, pendências e publicações efetivas. Sem novidade relevante, mantém a base. Agendamento exige tarefa real, próxima execução e acessos persistentes, não apenas um arquivo de prompt.

A mineração é semanal; a atualização de pagamento e a suspensão de cobrança não são. Eventos financeiros e verificações antes do contato precisam ocorrer no ritmo operacional.

Base: [B1], pp.25–28. Novas fontes e observabilidade: [S01–S03], [S14–S22].

## 35. Inteligência de público e operação
Reaproveitar o patrimônio da mineração para melhorar clareza, oferta, atendimento e testes, sem criar perfis invasivos.

Manter as análises de dúvidas, objeções, linguagem, abandono, tempos e resultados comerciais discutidas nos prompts originais. Comparar compradores e não compradores somente com evidência de compra e cobertura declarada.

| Dimensão | Uso e restrição |
| --- | --- |
| Demografia | Idade/gênero só de dados declarados ou fontes autorizadas. Não inferir por nome, foto, voz, escrita ou produto. |
| Geografia | Distinguir cadastro/entrega/declaração de proxy DDD. Não apresentar aproximação como residência atual. |
| Comportamento | Medir por pessoas/conversas únicas, não inflar frequência com templates ou mensagens repetidas da mesma pessoa. |
| Comercial | Separar correlação de causalidade e campanha de sazonalidade. Valor recebido, contrato total e receita incremental são métricas diferentes. |
| Financeiro | Dados restritos à finalidade legítima. Não usar atraso para explorar vulnerabilidade ou forçar nova compra. |
| Plataformas | YouTube e Shop conservam suas restrições. Não enriquecer perfis individuais com dados obtidos fora do uso permitido. |

### Separação do conhecimento público

Relatórios de público, rankings, margens, conflitos e métricas internas não ficam na RAG que responde aos clientes. Podem orientar propostas de conteúdo e procedimentos após revisão.

Candidatos de boas respostas devem ser corretos, autorizados e adequados, não apenas associados a venda. Respostas criadas pelo próprio agente não são evidência independente de verdade.

Percentuais exigem denominador, período e cobertura. Uma parcela da base com idade conhecida não representa automaticamente toda a audiência.

Base: [B1], pp.25–26. Dados e não discriminação: [S14], [S15], [S38].

## 36. Google Sheets e visão gerencial
Preservar as 5 abas originais e acrescentar visões do novo escopo, sem expor a base privada de clientes.

| Visão | Unidade / finalidade |
| --- | --- |
| INTERAÇÕES | Uma interação por ID: canal, links, categoria autorizada, assunto, ação, consulta, resposta e status. |
| RESUMO POR ANÚNCIO | Anúncio/campanha: volume, categorias, moderação, oportunidades e resultados atribuíveis. |
| LEADS E VENDAS | Oportunidade: produto, oferta, origem, checkout, compra confirmada e estado de recuperação. |
| FILA HUMANA | Caso: motivo, prioridade, responsável, prazo, tentativas e resolução. |
| PLAYBOOK / REGRAS | Regra ou resposta aprovada: versão, fonte, vigência, responsável e autonomia. |
| Visões novas de conteúdo | YouTube vídeo/live e TikTok Shop: atendimento por origem, sem forçar todo registro a ad_id. |
| Saúde das integrações | Cobertura, falhas, dados atrasados, reconciliação e links restritos para diagnóstico. |

### Financeiro em acesso separado

Faturas, parcelas e situações de regularização exigem workbook ou painel restrito, com menor exposição e papéis próprios. Esconder uma aba não é controle de acesso. A planilha ampla pode exibir apenas referência do caso e estado operacional necessário.

Atualizar pela chave canônica, não acrescentar nova linha por retentativa. Recebimentos refletem pagamentos únicos; pedido espelhado no Bling não duplica receita. Falha do Sheets deixa sincronização pendente no banco.

Links de comentário, vídeo e anúncio devem ser reais/verificáveis. Links autenticados de boleto, cadastro ou pagamento não entram no painel geral.

Base: [B1], pp.19–21. Ampliação de visões proposta em resposta a [U]; YouTube analítico condicionado a [S15].

## 37. Indicadores que mostram valor real
Qualidade, confiabilidade e receita precisam ser medidas juntas. Mais mensagens ou mais exclusões não significam melhor operação.

| Área | Indicadores e distinções |
| --- | --- |
| Atendimento | Primeira resposta, resolução, reabertura, handoff, pendências, satisfação observada e cobertura de canais. |
| Moderação | Ações por tipo, reversões quando possíveis, falsos positivos e críticas legítimas preservadas. |
| Ferramentas / dados | Consulta autorizada, ausência, conflito, atraso, falha, timeout e reconciliação por provedor. |
| Vendas | Oportunidades, links enviados, compras confirmadas, valor recebido e atribuição assistida sem duplicação. |
| Regularização | Obrigações elegíveis, contatos permitidos, pagamentos confirmados, falsas cobranças evitadas, contestações e cancelamentos de pendência. |
| Recuperação futura | Conversão por coorte e canal, supressões, frequência, opt-out, receita assistida versus incremental em teste. |
| IA e conhecimento | Custo/tempo por caso, uso correto de fonte, lacunas, testes de recuperação, divergência do avaliador e revisão humana. |

O valor total contratado na LIA não se soma à receita de cada parcela como se fossem novas vendas. Na Eduzz, separar número de assinantes, faturas e recebimentos. Repasse líquido do marketplace não é o mesmo que pagamento do comprador.

### Metas para o piloto

Definir baselines com dados autorizados e volume real. Não prometer aumento de conversão ou economia antes do teste. Metas de SLA, custo, cadência e precisão dependem da capacidade do time e dos limites dos provedores.

Zero tolerância para vazamento, cobrança à pessoa errada, promessa financeira sem fonte e duplicação por retentativa. Incidente nesses critérios bloqueia a capacidade afetada.

Requisitos de medição derivados de [B1], p.30; modelos financeiros [S20–S29]. Metas não foram apuradas nesta revisão.

## 38. Segurança, retenção e direitos
Privacidade deve existir no caminho dos dados e nos efeitos externos, não apenas no texto de uma política.

| Controle | Implementação exigida |
| --- | --- |
| Credenciais | Cofre/variáveis restritas por serviço; tokens fora do contexto do modelo, logs e repositório. |
| Autorização | Cliente, conta, recurso e finalidade verificados no servidor. Sem SQL genérico, terminal administrativo ou envio arbitrário. |
| Dados e rastros | Minimização, criptografia aplicável, controle por papel e retenção por origem/finalidade, inclusive Langfuse e backups. |
| Instruções maliciosas | Comentários, anexos e RAG não mudam permissões, não autorizam código e não aprovam políticas. |
| Links / arquivos | Domínios e tipos permitidos, verificação de destinatário, limite de download e proteção de URLs assinadas. |
| Direitos e correções | Fluxo humano para acesso, correção, exclusão e contestação. Manter somente registros necessários segundo política aprovada. |

A LGPD exige finalidade, necessidade e segurança, entre outros princípios. A política de retenção deve ser aprovada pela organização, com restrições adicionais de cada plataforma; pseudonimização não equivale automaticamente a anonimização.

### Cobrança sem constrangimento

O CDC proíbe cobrança com constrangimento ou ameaça. A assistência deve identificar a empresa e a obrigação corretamente, respeitar disputas e não expor informação financeira a terceiros. Regras de horário/cadência precisam considerar lei, contrato e política do canal; revisar com o jurídico antes da ativação.

O agente não decide crédito, negativação, sanção de acesso, desconto, juros ou alteração contratual. Casos sensíveis e exceções seguem para responsável humano.

Base: [B1], p.29; normas oficiais [S37], [S38]. Políticas específicas [S14], [S15], [S19], [S30].

## 39. Aceite: fundação e regressões
Os achados das revisões anteriores viram testes permanentes. Esta versão não declara o estado atual dos repositórios.

| ID | Cenário | Resultado exigido |
| --- | --- | --- |
| T01 | OpenClaw sem runtime Hermes | Agente, ferramentas, identidade e sessão iniciam no ambiente correto. |
| T02 | Público x privado | Endpoint, payload e destino real corretos; nenhuma informação privada publicada. |
| T03 | Opt-out e humano | Todas as rotas registradas respeitam pessoa/caso e suspensões pertinentes. |
| T04 | Ação/proatividade | Omissão ou rótulo incorreto do modelo não contorna a autorização da tarefa. |
| T05 | Token sem consulta | Credencial/flag/health check não autorizam afirmação sem evidência daquele recurso. |
| T06 | Dois clientes simultâneos | Histórico, pedido, pagador, destinatário e respostas separados. |
| T07 | Lote, duplicata e reinício | Fila/outbox retomam sem perda silenciosa ou reenvio cego. |
| T08 | Erros reais de rede | TimeoutError, URLError, HTTP, desconexão e retorno inválido tratados; ação incerta conciliada. |
| T09 | Estado compartilhado correto | Ingress, MCP e workers usam o mesmo perímetro previsto; teste não remove kill switch real. |
| T10 | Prompt injection / permissão | Texto de lead, anexos ou documentos não libera ferramentas nem recursos de outro caso. |

Executar teste unitário, de contrato, integrado e de homologação para cada capacidade. Relatório identifica commit, versão do OpenClaw, configuração, ambiente e evidência. Contagem de testes não substitui jornada real.

Habilitar por capacidade. Falha de segurança bloqueia o efeito afetado; o restante do atendimento pode continuar em modo seguro e supervisionado.

Critérios derivados de [B1], pp.30–31; [B2], F01–F10 e T01–T17. Sem nova auditoria de código nesta atualização.

## 40. Aceite: canais, RAG e observabilidade
Conectar a ferramenta certa não basta: é preciso provar como o agente a utiliza e quais limites respeita.

| ID | Teste | Evidência obrigatória |
| --- | --- | --- |
| T11 | Meta ads e Sheets | IDs/links reais; 3 categorias; interação compartilhada não duplica métrica. |
| T12 | YouTube comentários | Listagem completa conforme quota, respostas de threads antigas e moderação pelo método permitido. |
| T13 | YouTube live | Retomada do stream, chat encerrado, papel de moderador, sanção e limite de intervenção. |
| T14 | YouTube política de dados | Atualização/exclusão e analítica condicionada ao caso de uso; rastros respeitam a origem. |
| T15 | Shop sem scope | Sem seller.customer_service aprovado, não tenta enviar nem contorna via navegador. |
| T16 | Shop atendimento | Conversa/pedido/loja corretos; sem checkout externo, taxa extra ou coleta para desvio. |
| T17 | RAG vigente | Fonte aprovada e permitida; produto correto; ausência não gera resposta inventada. |
| T18 | Mineração semanal | Checkpoint, semana perdida, candidatos isolados, aprovação de hash e publicação versionada. |
| T19 | Langfuse redaction/outage | Sem dados desnecessários; queda da telemetria não duplica nem interrompe envio operacional. |
| T20 | Langfuse correlação | Trace liga RAG, ferramentas e ação sem misturar casos ou contar custo duas vezes. |

Adicionar casos de falso positivo: pergunta comum não deve virar emergência só por conter “processo” ou citar uma profissão. Moderação indevida, informação errada e regressão de tom entram em avaliação humana.

Integração homologada exige prova na conta de teste do canal, além da simulação. Dados e tokens dos testes não podem vazar no relatório compartilhado.

Testes propostos a partir de [S01–S19], [B1] e [B2]. Não executados durante a criação deste PDF.

## 41. Aceite: financeiro e recuperação
Os cenários abaixo impedem que uma automação útil vire cobrança errada, duplicidade ou vazamento.

| ID | Teste | Resultado exigido |
| --- | --- | --- |
| T21 | LIA renegociou sem mudar order | Novo billing reconhecido; ações e links das parcelas substituídas são cancelados. |
| T22 | LIA parcela paga | Só a obrigação correta é liquidada; não quita todas as demais automaticamente. |
| T23 | Eduzz aluno ≠ pagador | Dados financeiros apenas ao responsável autorizado; vínculo ambíguo vira revisão. |
| T24 | Eduzz sem payment.link | Não inventa URL nem cria assinatura; usa caminho oficial/humano. |
| T25 | Pagamento durante a fila | Revalidação antes de enviar; cancelamento imediato de pendências ainda não executadas. |
| T26 | Assiny carga atrasada | Zero linhas não vira não comprador ou devedor; recuperação dependente é pausada. |
| T27 | Compra espelhada no Bling | Uma receita/pedido canônico; não duplica compra, remessa ou régua. |
| T28 | LIA/Eduzz/Yampi/Clint simultâneos | Dono e reserva de contato evitam toques concorrentes da mesma finalidade. |
| T29 | Canal financeiro proibido | Cobrança de dívida não enviada por WhatsApp nem exposta em rede pública. |
| T30 | Disputa, estorno, cancelamento | Suspende contato pertinente e revalida obrigação; sem decisão contratual automática. |
| T31 | Futuro lançamento encerrado | Oferta vencida não é enviada; compra equivalente em outra fonte suprime recuperação. |
| T32 | Consulta até registro | Cliente, fonte, resposta, canal e resultado ligados ao CRM, painel e trace, com dados mínimos. |

Critério financeiro é acerto sobre obrigação, pessoa, valor, validade e canal. Mensagem persuasiva ou venda posterior não compensa erro nesses pontos.

Matriz de teste proposta. Fontes de semântica e políticas: [S19–S30], [S37], [S38].

## 42. Implantar em frentes verificáveis
Não tentar habilitar todos os canais e cobranças ao mesmo tempo. A nova visão é abrangente; a liberação deve ser progressiva.

| Etapa | Entrega | Condição para avançar |
| --- | --- | --- |
| 0 · inventário | Versões, contas, scopes, RAG, fonte BigData e integrações existentes. | Mapa real e preservação do patrimônio já criado. |
| 1 · fundação | OpenClaw, isolamento, inbox/outbox, regras, kill switch e Langfuse mínimo. | Testes T01–T10; execução sem riscos críticos. |
| 2 · atender | RAG + Clint + Bling + Meta/ads + registros e canais autorizados. | Jornada de pedido, dado ausente e falha demonstradas. |
| 3 · ampliar comércio | Yampi e correlação ERP; continuidade do painel. | Pagamento e origem sem duplicação; eventos reconciliados. |
| 4 · ampliar canais | YouTube comentários/lives e Shop, cada um com seu gate. | Scopes, quotas, políticas e testes de cada superfície. |
| 5 · financeiro supervisionado | LIA/Eduzz/BigData, consulta, segunda via e comunicações permitidas. | Sem falsa cobrança; ownership, pagador e elegibilidade comprovados. |
| 6 · recuperação futura | Campanhas por produto e origem, suprimidas por compra e recusa. | Fontes frescas, oferta vigente, cadência e mensuração aprovadas. |

A curadoria semanal pode preparar candidatos durante essas etapas. Publicação permanece controlada. Acesso ao Shop e revisões do YouTube podem avançar em paralelo, mas sua ausência não justifica burlar política.

### Escopo não é cronograma fictício

Estimativas de prazo e custo devem vir do desenvolvedor após inventário. Nada neste documento promete que uma API esteja ativa ou que uma chave resolva uma função não implementada. O responsável libera cada capacidade com evidência.

Meta, anúncios, Google Sheets, Clint/Bling e atendimento completo permanecem no escopo final mesmo se o primeiro piloto cobrir apenas uma conta.

Plano proposto; evolução de [B1], pp.31–32 e [B2], pp.10–11. Novas frentes solicitadas em [U].

## 43. O que o time precisa disponibilizar
Pendências de implantação, não impedimentos para especificar o projeto. Segredos devem ser entregues pelo cofre aprovado, nunca colados no PDF.

| Frente | Informações e decisões necessárias |
| --- | --- |
| OpenClaw / Langfuse | Versão instalada, agente/workspace, ferramentas permitidas, hospedagem/region, retenção e contas de acesso à telemetria. |
| Clint / Bling | Contas, scopes reais, identidade CRM–ERP, mapeamento financeiro/logístico, escrita permitida e notificações existentes. |
| Meta / WhatsApp / e-mail | Contas/páginas/anúncios, números e transportes, política de finalidade, templates e remetente corporativo. |
| YouTube | Canais OAuth, quota, papel em lives, política de retenção e aprovação do caso de uso de analítica quando aplicável. |
| TikTok Shop | Loja/região, app/escopo customer service, documentação acessível, cenários de teste e dono do atendimento. |
| LIA | Ambiente, contratos/billings, webhooks, responsável financeiro e divisão contratual da cobrança com o financiador. |
| Eduzz | Produto recorrente, planos/IDs, acesso leitura, eventos, pagador, faturas e regras nativas já ativas. |
| Assiny / BigData | Provedor, views autorizadas, schema, chaves, status, cobertura, atraso máximo e suporte da carga. |
| Negócio / jurídico | Ofertas, templates, cadência, finalidade, escalonamento, política de disputas e autonomia aprovada. |

O desenvolvedor deve devolver por capacidade: implementado, configurado, testado localmente, homologado e liberado; evidência/commit; dependência externa; responsável e previsão. Não usar esses estados como sinônimos.

Não houve acesso ao ambiente produtivo, leitura de clientes, alteração no repositório nem ativação de cobranças nesta atualização. O PDF é a nova referência de escopo e aceite.

Dependências consolidadas de [B1], p.32 e ampliadas por [U].

## 44. Decisão técnica consolidada
O projeto cresce para uma central de relacionamento e assistência comercial. O que o torna confiável é separar conhecimento, estado e autorização.

| Camada | Decisão |
| --- | --- |
| Execução conversacional | OpenClaw, uma identidade e skills com permissões contextuais. Sem memória privada global. |
| Conhecimento | RAG aprovada existente, sem fine-tuning; curadoria separada com aprovação. |
| Relacionamento / operação | Clint + Bling + banco operacional; canais e comércio com adaptadores próprios. |
| Financeiro | LIA/Eduzz na unidade de obrigação; Yampi/Shop na transação de origem; Assiny por BigData controlado. |
| Observabilidade | Langfuse junto ao OpenClaw e serviços; telemetria mínima, avaliações e versões, sem poder de aprovação. |
| Recuperação | Motor de elegibilidade e contato coordenado, fase posterior para perpétuo/lançamentos. |
| Gestão | Planilhas operacionais, painel financeiro restrito, fila humana e provas de aceite. |

### Alternativas consideradas

Tudo dentro de um prompt: simples de iniciar, insuficiente para identidade, eventos e finanças. Um agente completo independente por plataforma: isola algumas rotas, mas tende a duplicar contexto e regras de contato. Núcleo compartilhado com adaptadores e contextos restritos: desenho recomendado, pois mantém a identidade e centraliza a autorização sem abrir toda a base ao modelo.

O motor e o código úteis devem ser reaproveitados. A mudança não exige refazer a mineração, trocar embeddings ou abandonar a integração ERP existente. Exige contratos explícitos, testes por capacidade e ordem de implantação.

O resultado desejado é um agente que sabe quando responder, de onde obter a informação, quem pode recebê-la e quando precisa parar e chamar uma pessoa.

Síntese de projeto. Fontes e limites de capacidade nas páginas seguintes; todos os recursos seguem sujeitos a homologação.

## Referências
[B1] Documento Mestre v2.0. Agente_Social_Seller_Documento_Mestre_v2.pdf, 21/09/2026, 33 páginas. Lido integralmente. Base de OpenClaw, RAG, ferramentas, moderação, CRM/ERP, planilha, mineração e governança.

[B2] Parecer técnico de adequação. Social_Seller_Parecer_e_Plano_de_Adequacao_OpenClaw.pdf, 22/09/2026, 12 páginas. Base dos critérios de regressão, não auditoria do código atual.

[U] Decisões desta atualização. Solicitação do responsável: Langfuse, YouTube, LIA, Assiny via BigData, Yampi/Bling, TikTok Shop/Bling, recorrência Eduzz e recuperação futura. Não comprova scopes/configurações.

[S01] Langfuse • OpenClaw. Guia do Langfuse Bridge e alternativa de rastreio apenas de LLM. Verificar plugin, versão e conta antes de instalar. https://langfuse.com/integrations/other/openclaw

[S02] Langfuse • OpenTelemetry. Instrumentação e relação entre traces/observações. Serviços próprios exigem propagação e registros adicionais. https://langfuse.com/integrations/native/opentelemetry

[S03] Langfuse • Masking. Mascaramento de dados antes do envio de telemetria. Não substitui finalidade e controle de acesso. https://langfuse.com/docs/observability/features/masking

[S04] OpenClaw • Security. Modelo de confiança do gateway e riscos de ferramentas com acesso amplo. https://docs.openclaw.ai/gateway/security

[S05] OpenClaw • Session management. Configuração e escopo de sessões. Isolamento na ferramenta permanece necessário. https://docs.openclaw.ai/concepts/session

[S06] YouTube • commentThreads.list. Leitura, paginação, escopos e custo de quota. https://developers.google.com/youtube/v3/docs/commentThreads/list

[S07] YouTube • comments.insert. Resposta a comentário com parentId, autorização e quota. https://developers.google.com/youtube/v3/docs/comments/insert

[S08] YouTube • setModerationStatus. Status de moderação, restrições de restauração e sanção de autor. https://developers.google.com/youtube/v3/docs/comments/setModerationStatus

[S09] YouTube • comments. Referência de comentários, listagem de respostas e métodos, incluindo delete. https://developers.google.com/youtube/v3/docs/comments

[S10] YouTube • Push notifications. Notificações de vídeos; não representa webhook universal de comentários. https://developers.google.com/youtube/v3/guides/push_notifications

[S11] YouTube Live • streamList. Streaming de mensagens e continuidade do chat ao vivo. https://developers.google.com/youtube/v3/live/docs/liveChatMessages/streamList

[S12] YouTube Live • mensagens e bans. Referência de liveChatMessages. Complemento: liveChatBans.insert, listado na navegação oficial, controla sanções com autorização própria. https://developers.google.com/youtube/v3/live/docs/liveChatMessages

[S13] YouTube • Quota and compliance audits. Orçamentos padrão e auditorias. Conferir quota efetiva do projeto. https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits

[S14] YouTube • Developer policies. Uso, armazenamento, atualização/exclusão e demais obrigações sobre dados de API. https://developers.google.com/youtube/terms/developer-policies

[S15] YouTube • Derived metrics policy. Aditamento/caso de uso para métricas derivadas, sentimento agregado e retenção. Guia de políticas detalha a aprovação requerida. https://developers.google.com/youtube/terms/derived-metrics-policy

[S16] TikTok Shop • Get Conversation. Recurso customer_service/202601 e escopo seller.customer_service em referência pública indexada. https://partner.tiktokshop.com/docv2/page/get-conversation-202601

[S17] TikTok Shop • Large File Uploads. Referência oficial que menciona o endpoint Send Message customer_service/202309. https://partner.tiktokshop.com/docv2/page/wfi3nz36

[S18] TikTok Shop • Customer Service API. Portal dinâmico: o conteúdo completo não pôde ser validado publicamente nesta revisão. Exigir contrato autenticado do app, eventos, regras e exemplos. https://partner.tiktokshop.com/docv2/page/customer-service-api-overview

[S19] TikTok Shop Brasil • Atendimento. Política de atendimento ao cliente: limites para dados pessoais, pagamentos adicionais e desvio de transações. https://seller-br.tiktok.com/university/essay?knowledge_id=2583022047233809&lang=pt-BR

[S20] Eduzz • Contract updated. Evento myeduzz.contract_updated; estados do contrato e separação de customer e financialResponsible. https://developers.eduzz.com/reference/webhook/myeduzz-contract-updated

[S21] Eduzz • Faturas da assinatura. Consulta subscriptions/:id/invoices; escopo de leitura e disponibilidade de payment.link quando a fatura está aberta. https://developers.eduzz.com/reference/api/get-myeduzz-v1-subscriptions-id-invoices

[S22] Eduzz • Invoice paid e segurança. Evento myeduzz.invoice_paid. Segurança: developers.eduzz.com/docs/webhook/security, com validação x-signature. https://developers.eduzz.com/reference/webhook/myeduzz-invoice-paid

[S23] LIA • Documentação. Hierarquia de objetos e recursos de integração. Validar permissões e ambiente fornecidos à conta. https://docs.lia.com.br/

[S24] LIA • Consultar parcela. Bill, valores, datas, status, checkout e relação com billing/payment. https://docs.lia.com.br/bills/get/

[S25] LIA • Download de boleto. Recurso de obtenção de boleto existente por payment. Não equivale a nova venda. https://docs.lia.com.br/payments/download_boleto/

[S26] LIA • Renegociação. Novo billing, origin_billing_id e cancelamento do anterior; order pode não mudar de status. https://docs.lia.com.br/common-asked-questions/how-renegotiation-works.html

[S27] LIA • Webhooks e assinatura. Eventos e validação específica do fornecedor. Homologar corpo bruto e assinatura com exemplos da conta. https://docs.lia.com.br/webhooks/validation/

[S28] Yampi • Webhooks. Eventos de pedido, pagamento, recusa e carrinho; disponibilidade/configuração devem ser verificadas na loja. https://docs.yampi.com.br/api-reference/webhooks/introduction

[S29] Yampi • Pedidos. Referência de consulta e filtros de pedidos; recursos de transações devem ser mapeados pelo adaptador. https://docs.yampi.com.br/api-reference/pedidos/pedido/listar-pedidos

[S30] WhatsApp Business • Política. Versão consultada atualizada em 23/09/2026. Opt-in, templates, janela e restrição a debt collection. https://whatsappbusiness.com/policy/

[S31] OpenClaw • WhatsApp. Canal e configuração. Registrar transporte real e não presumir equivalência à Cloud API. https://docs.openclaw.ai/channels/whatsapp

[S32] Evolution API • Referência oficial. Repositório do mantenedor: conexões Baileys e Cloud API. A página antiga de documentação não carregou; contrato da versão instalada precisa ser homologado. https://github.com/evolution-foundation/evolution-api

[S33] Bling • Webhooks. Assinatura, ACK, repetição, disponibilidade e ordem dos eventos. https://developer.bling.com.br/webhooks

[S34] Bling • Pedidos TikTok Shop. Importação de pedidos do marketplace; vínculo real depende da configuração da integração. https://ajuda.bling.com.br/hc/pt-br/articles/31322493241623-Pedidos-de-venda-do-TikTok-Shop

[S35] Bling • Notas para Yampi. Integração fiscal/logística, status e rastreamento conforme recursos/configuração. https://ajuda.bling.com.br/hc/pt-br/articles/17567039603607-Envio-das-notas-para-Yampi

[S36] LIA • Cobrança. Serviço do financiador; fundamenta a necessidade de coordenar responsabilidades e contatos já existentes. https://www.lia.com.br/cobranca

[S37] Brasil • Código de Defesa do Consumidor. Lei 8.078/1990 consolidada, especialmente regras sobre cobrança. Revisão jurídica necessária para régua e conteúdo. https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm

[S38] Brasil • LGPD. Lei 13.709/2018 consolidada. Finalidade, necessidade, segurança, direitos e governança. https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm

[S39] Langfuse • Avaliações. Avaliações de produção, datasets, revisão humana e experimentos. Qualidade não autoriza efeito financeiro. https://langfuse.com/docs/evaluation/overview

[S40] YouTube • Guia de políticas. Esclarece condições de analítica ampliada para desenvolvedores auditados/aprovados. https://developers.google.com/youtube/terms/developer-policies-guide
