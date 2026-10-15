# Pesquisa de plataformas e dados — Binary Intelligence AI

Verificado em **15/10/2026**. Escopo informado: Forex, cripto e B3; horizonte inicial de **5 minutos**. Esta é uma pesquisa documental, sem conta, credenciais, consulta de mercado ao vivo ou teste de ordem. “Verificada” significa que a capacidade consta em documentação oficial; não significa disponibilidade para a conta, país ou ativo do usuário.

## Correção da pesquisa anterior

A resposta anterior classificou Binance Options e IBKR como prontas para o produto binário de 5 minutos e afirmou payout prévio e conta demo da Binance sem evidência suficiente. Isso fica **revogado**. O rótulo CALL/PUT em opções convencionais não implica contrato de ganho fixo por direção em 5 minutos. Também não foram comprovados latência menor que 50 ms, cobertura B3 pela Massive/Polygon nem adequação do Yahoo Finance à liquidação.

## Plataformas de execução candidatas

| Plataforma | API pública oficial / status para o caso de uso | Histórico / tempo real | Demo / payout antes da compra | Autorização, limites e custo | Pendência |
|---|---|---|---|---|---|
| **Deriv Options** | **Verificada documentalmente**: APIs REST e WebSocket; `contracts_for`, `ticks_history`, `ticks`, `proposal` e `buy` aparecem na documentação [1–5]. | Ticks e candles históricos; granularidades documentadas incluem 60 e 300 s [3]. Stream de ticks [2]. | Conta demo e canal WebSocket demo documentados [1]. `proposal` fornece preço da proposta; a comparação da API mostra `ask_price` e `payout` [4]. É necessário confirmar contrato, ativo, duração e cotação no instante de compra. | App registrado, OAuth2 ou PAT; escopo `trade` para conta/compra, `account_manage` para criar conta; PAT requer `Deriv-App-ID` no REST [1,5]. Limite WS compartilhado de 360/min e 14.400/h para `proposal`/`buy`/`sell`/status; REST 300/min por IP e 80/min por usuário autenticado [6]. Custos e disponibilidade de ativos dependem da conta/contrato; não validados. | Confirmar elegibilidade regional, disponibilidade de CALL/PUT de 5 min por símbolo, regra de empate, preço de liquidação e condições de uso na conta concreta. |
| **Binance Options** | API oficial **verificada**, mas **inadequação ao contrato binário fixo ainda não resolvida**. A documentação descreve símbolo com strike e data de vencimento, livro de ordens, preço e taxas; não comprova payout binário pré-operação para 5 min [7,8]. | Candles de opções de 1 e 5 min, cotações e registros de exercício [7]. | Demo e payout fixo de 5 min: **não verificados** para esse produto. | A API expõe regras e pesos por endpoint [7]; permissão, autenticação, custos e elegibilidade precisariam de análise específica caso o produto mude. | Não selecionar para execução deste desenho sem redefinir payoff, liquidação e horizonte. |
| **Interactive Brokers** | APIs Web/TWS oficiais **verificadas**, mas são de instrumentos negociados em mercado; **não verificado** um contrato binário de payout fixo com vencimento de 5 min [9–11]. | Barras históricas e dados ao vivo mediante permissões/assinaturas; limites de histórico e de linhas de mercado [9–11]. | Conta paper com APIs, com diferenças de execução; não há payout binário pré-ordem documentado para este caso [10]. | Conta elegível, permissões de negociação e assinatura de market data; custos variam por bolsa e produto [10,11]. | Não selecionar para execução binária sem comprovar o produto exato. |
| **IQ Option / Quotex** | **Não verificada**: nesta pesquisa não foi localizada documentação pública oficial suficiente para projetar autenticação, consulta de payout e envio autorizado de ordens. | Não verificado. | Não verificado para integração oficial. | Limites, permissões e custos de API não verificados. | Pedir documentação oficial diretamente à plataforma. Não usar bibliotecas que reproduzem protocolo privado. |

## Provedores independentes de dados

| Fonte | Cobertura e granularidade comprovadas | Preço / limitação para 5 min | Estado |
|---|---|---|---|
| **Deriv** [2,3] | Ticks e candles de 1 e 5 min para símbolos oferecidos no serviço. | Primeira fonte a avaliar para eventual contrato Deriv. Extensão histórica, qualidade e licença de armazenamento ainda exigem teste/termos. | **Verificada documentalmente**. |
| **Massive (antiga Polygon.io)** [12–14] | Forex e cripto; agregados Forex de 1 min vêm de cotações bid/ask, sem candle quando não há atualização. Histórico Forex por REST e arquivos de 1 min. | Página consultada mostra Currencies Starter **US$49/mês** para stream de minuto e arquivos históricos; preço/plano podem mudar. O preço pode divergir do spot de liquidação Deriv. Não comprova B3. | **Verificada documentalmente** para Forex/cripto, sujeita ao plano/licença. |
| **TraderMade** [15] | Forex/cripto; histórico de minuto, tick e WebSocket constam na oferta comercial. | Página consultada mostra oferta business FX & Crypto de **£599/mês**; elegibilidade e limite por plano precisam ser confirmados. Não é preço de liquidação da corretora. | **Verificada documentalmente**, contratação não verificada. |
| **Market Data Cloud / Cedro** [16,17] | B3 via WebSocket; planos anunciam candles de 1 min: dados do dia no Basic, **3 meses** no Pro/Premium. Stream não fornece histórico de trades. | Página consultada lista cotas de 20 mil/100 mil/500 mil requisições REST por mês; preço numérico e licença para treino/armazenamento **não confirmados**. Três meses de M1 podem ser insuficientes para validação robusta. | **Parcialmente verificada**; uso em ML pendente de autorização. |

**B3:** a política da B3 distingue uso interno, uso não exibido e desenvolvimento de produto. O texto restringe uso de dados atrasados/históricos além de gráficos e tabelas sem licença adequada e prevê autorização para desenvolvimento/armazenamento [18,19]. Isso exige confirmação contratual do fornecedor e, quando aplicável, da B3 antes de ingerir B3 em treino ou produto. Esta leitura é um risco contratual identificado, não uma conclusão jurídica sobre a licença individual.

## Dados mínimos para expiração de 5 minutos

1. Fixar **contrato e regra de liquidação reais** por ativo: spot de entrada, instante de início, instante de expiração, fonte do spot, precisão, empate e payout. Não assumir que o fechamento do quinto candle M1 seja a liquidação da plataforma.
2. Guardar timestamps UTC de observação, publicação e ingestão; distinguir candle fechado de candle em formação. Um candle M1 só entra em features depois do fechamento confirmado pela fonte. A análise não precisa ocorrer exatamente no segundo 0, nem há garantia de entrada no segundo 1.
3. Usar M1 para contexto e ticks/quotes próximos de entrada e expiração para avaliar diferença de liquidação. Registrar lacunas, duplicatas, spread quando disponível, relógio, latência observada e mudanças de horário/sessão. Limites de atraso serão definidos empiricamente por fonte e ativo.
4. Obter propostas de payout com timestamp quando for tecnicamente e contratualmente possível. Sem payout histórico observável, backtest de retorno financeiro deve usar **cenários explicitamente hipotéticos**, separados de paper trading; não afirmar vantagem econômica.
5. Fazer estudo de concordância entre feed independente e spot da plataforma para cada ativo, horário e regime. Sem esse estudo, treino pode estimar direção do feed, mas não probabilidade de ganho do contrato. Para B3, verificar se há contrato binário autorizado correspondente; caso contrário, B3 é apenas pesquisa de sinais.

## Arquitetura inicial e decisão

Fluxo previsto: **arquivo histórico autorizado / adaptador simulado → validador e contratos versionados → features apenas com dados fechados → modelo e calibração em Python → decisão determinística com ABSTER-SE por padrão → simulador isolado → API Node/TypeScript → painel**. PostgreSQL guardará metadados, previsões, decisões e trilha de auditoria; grandes séries terão armazenamento/retensão específicos após validação de licença. REST versionado é suficiente para a primeira versão; SSE só quando houver atualização contínua real. O adaptador de execução real fica ausente até a Fase 11 e depende de autorização explícita e controles de risco independentes.

**Decisão da Fase 1:** Deriv é a candidata documentada mais próxima do contrato descrito, ainda sem seleção de conta/ativo. Para a Fase 2, preparar somente estrutura local e simulação. Em vez de prometer cobertura operacional de “todos os ativos”, organizar pesquisa e dados por classe; o produto de execução dependerá do contrato confirmado para cada classe. A próxima decisão do usuário é escolher um **primeiro ativo e plataforma para validação em demo** (sugestão de investigação: EUR/USD na Deriv), após a estrutura local estar pronta.

## Fontes oficiais (consultadas em 15/10/2026)

1. [Deriv — Options API e canais demo/real](https://developers.deriv.com/docs/options/)
2. [Deriv — Market Data](https://developers.deriv.com/docs/data/)
3. [Deriv — Ticks History](https://developers.deriv.com/docs/data/ticks-history/)
4. [Deriv — comparação de `proposal`](https://developers.deriv.com/comparison/proposal/)
5. [Deriv — autenticação e fluxos](https://developers.deriv.com/docs/intro/authentication/)
6. [Deriv — limites](https://developers.deriv.com/docs/limits/)
7. [Binance — dados de opções](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-options/api/rest-api/market-data)
8. [Binance — definições de contratos de opções](https://developers.binance.com/en/docs/products/derivatives-trading-options/common-definition)
9. [IBKR — barras históricas](https://ibkrcampus.com/docs/tws-api/doc/market-data-historical/historical-bars/requesting-historical-bars)
10. [IBKR — conta paper](https://ibkrcampus.com/campus/glossary-terms/paper-trading-account/)
11. [IBKR — negociação via Web API](https://ibkrcampus.com/campus/ibkr-api-page/web-api-trading/)
12. [Massive — agregados Forex de 1 minuto](https://massive.com/docs/websocket/forex/aggregates-per-minute)
13. [Massive — histórico Forex](https://massive.com/docs/flat-files/forex/minute-aggregates)
14. [Massive — cobertura de moedas](https://massive.com/currencies)
15. [TraderMade — planos](https://www.tradermade.com/pricing)
16. [Market Data Cloud — planos](https://www.marketdatacloud.com.br/checkout-planos-gerais/)
17. [Market Data Cloud — WebSocket](https://www.marketdatacloud.com.br/api-streaming-websocket/)
18. [B3 — política de consumo de dados](https://www.b3.com.br/data/files/7F/D0/F8/0C/1541B9105B12E5A9AC094EA8/Market%20Data%20B3%20Consumption%20Policy.pdf)
19. [B3 — política comercial 2026](https://www.b3.com.br/data/files/EF/F6/93/D7/364599100A29E189AC094EA8/Market%20Data%20Commercial%20Policy%202026.pdf)
