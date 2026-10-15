# Avaliação da integração oficial Deriv — Fase 11

**Consulta:** 15/10/2026  
**Escopo:** documentação, termos e endpoints oficiais da Deriv. Nenhuma biblioteca não oficial, engenharia reversa ou ordem foi utilizada.

## Decisão

| Uso | Decisão | Motivo |
|---|---|---|
| Dados públicos e propostas transitórias | **GO condicionado** | A API oficial oferece WebSocket público, cotações, histórico, metadados de contratos e propostas sem autenticação. |
| Negociação em conta demo | **GO condicionado** | Existe conta demo, autenticação oficial e canal WebSocket demo. Exige cadastro de aplicativo, credencial própria, confirmação da região e aceitação dos termos. |
| Execução com dinheiro real | **NO-GO nesta fase** | Ainda faltam validação autenticada da conta/região, reconciliação, testes de desconexão e revisão de segurança da Fase 12. |
| Histórico persistente ou treino com feed Deriv | **NO-GO sem autorização escrita** | Os termos da API proíbem armazenar conteúdo originado no site/API e permitem cache por somente 24 horas. Isso conflita com o dataset histórico, auditoria e treinamento persistente do projeto. |

O caminho seguro é um adaptador **demo-only**, com execução real desabilitada, dados Deriv tratados como cache transitório e nenhuma ingestão no dataset de ML até a Deriv autorizar o uso de armazenamento necessário.

## API oficial e transporte

A Deriv documenta uma API REST para contas/obtenção de OTP e WebSocket para dados e negociação. Os endpoints atuais são:

- REST: `https://api.derivws.com`.
- WebSocket público: `wss://api.derivws.com/trading/v1/options/ws/public`.
- WebSocket demo/real: a URL pronta é devolvida por `POST /trading/v1/options/accounts/{accountId}/otp`.
- O OTP vale 120 segundos e só pode ser usado uma vez.

Fontes: [visão geral da API](https://developers.deriv.com/docs/intro/api-overview/), [Options Setup](https://developers.deriv.com/docs/options/) e [autenticação WebSocket por OTP](https://developers.deriv.com/docs/options/websocket/).

### Autenticação, App ID e permissões

A plataforma aceita dois tipos de aplicativo:

1. **OAuth 2.0:** Authorization Code com PKCE. Requer `client_id`/App ID, `redirect_uri` exata, `state`, `code_challenge` S256 e troca do código no backend. O escopo `trade` cobre negociação e OTP; `account_manage` cobre criação de conta.
2. **PAT:** o usuário cria e insere um Personal Access Token. Pedidos REST usam `Authorization: Bearer ...` e também exigem `Deriv-App-ID`.

Um aplicativo deve ser registrado em `developers.deriv.com`; a documentação informa que App IDs legados não funcionam nas novas APIs. Para este sistema local e de um único operador, PAT é o fluxo inicial mais simples. OAuth é indicado se o produto passar a integrar contas de terceiros. Tokens ficam somente no backend e fora de logs, navegador, banco e Git.

Fontes: [autenticação](https://developers.deriv.com/docs/intro/authentication/), [OAuth 2.0 com PKCE](https://developers.deriv.com/docs/intro/oauth/) e [fluxos completos](https://developers.deriv.com/docs/workflows/).

## Dados de mercado e contratos

As mensagens abaixo são WebSocket e estão documentadas como públicas:

| Mensagem | Uso no projeto | Requisição mínima recomendada |
|---|---|---|
| `active_symbols` | descobrir ativos ativos e filtrar tipos de contrato | `{"active_symbols":"brief","contract_type":["CALL","PUT"]}` |
| `contracts_for` | consultar contratos e durações realmente disponíveis para um símbolo | `{"contracts_for":"frxEURUSD"}` |
| `ticks` | assinar preço em tempo real | `{"ticks":"frxEURUSD","subscribe":1}` |
| `ticks_history` | consultar ticks ou candles | `{"ticks_history":"frxEURUSD","end":"latest","style":"candles","granularity":300,"count":1000}` |

Na API atual, `active_symbols` devolve `underlying_symbol`, `underlying_symbol_name` e `pip_size`. O histórico suporta ticks e candles OHLC; 300 segundos é uma granularidade oficial. O adaptador deve usar `req_id`, guardar IDs de assinatura, cancelar com `forget`, enviar `ping` a cada 30–60 segundos e reconectar com backoff exponencial.

Fontes: [Market Data](https://developers.deriv.com/docs/data/), [Active Symbols](https://developers.deriv.com/comparison/active-symbols/), [Contracts For](https://developers.deriv.com/docs/data/contracts-for/), [Ticks](https://developers.deriv.com/docs/data/ticks/), [Ticks History](https://developers.deriv.com/docs/data/ticks-history/), [Ping](https://developers.deriv.com/docs/system/ping/) e [boas práticas](https://developers.deriv.com/docs/best-practices/).

### Proposta e compra

`proposal` é público e retorna uma cotação antes da ordem. Para o horizonte do projeto:

```json
{
  "proposal": 1,
  "amount": 1,
  "basis": "stake",
  "contract_type": "CALL",
  "currency": "USD",
  "duration": 5,
  "duration_unit": "m",
  "underlying_symbol": "SYMBOL_FROM_ACTIVE_SYMBOLS",
  "req_id": 101
}
```

A resposta inclui o `id` da proposta, `ask_price` e `payout`, permitindo calcular o ganho líquido observado antes da compra. `buy` exige WebSocket autenticado; recebe o ID da proposta e o preço máximo:

```json
{"buy":"PROPOSAL_ID","price":1,"req_id":102}
```

O sistema deve obter uma proposta nova imediatamente antes de cada entrada, aplicar seus limites ao payout efetivo e recusar respostas vencidas ou duplicadas. A documentação consultada não apresenta chave de idempotência para `buy`; portanto, reconciliação por resposta/contrato e bloqueio local de duplicidade são obrigatórios antes de qualquer piloto real.

Fontes: [Price Proposal](https://developers.deriv.com/docs/trading/proposal/), [Buy Contract](https://developers.deriv.com/docs/trading/buy/) e [operações de negociação](https://developers.deriv.com/docs/trading/).

## Contratos de cinco minutos

**Confirmado, mas não para todos os ativos.** A documentação oficial aceita `duration: 5` com `duration_unit: "m"` e lista `CALL`, `PUT`, `HIGHER` e `LOWER`. Materiais oficiais também mostram Rise/Fall de cinco minutos em Forex e ouro, e Higher/Lower de cinco minutos em índices sintéticos.

Uma consulta sem autenticação ao endpoint público oficial em 15/10/2026 encontrou:

- 71 símbolos ativos para `CALL`, `PUT`, `HIGHER` ou `LOWER`.
- `1HZ50V` aceitou proposta `CALL` de 5 minutos; a resposta trouxe ID, preço, payout e spot, mas nenhuma compra foi enviada.
- `frxXAUUSD` e `frxXAGUSD` anunciaram mínimo de 5 minutos para `CALL`/`PUT` intraday.
- `frxEURUSD` anunciou mínimo de 15 minutos para `CALL`/`PUT` intraday naquele momento, e uma proposta de 5 minutos foi rejeitada com `ContractBuyValidationError` / `Trading is not offered for this duration.`

`CALL`/`PUT` representam a direção Rise/Fall nos metadados atuais (`sentiment: up/down`). `HIGHER`/`LOWER` usam uma barreira e não são equivalentes a Rise/Fall. A disponibilidade depende do símbolo, horário, conta e residência; `contracts_for` e `proposal` devem ser a autoridade em tempo de execução.

Fontes: [schema oficial de proposta](https://developers.deriv.com/docs/trading/proposal/), [guia oficial de Forex com Rise/Fall de cinco minutos](https://docs.deriv.com/marketing/2025/ebook-forex-en-hq.pdf), [guia oficial de commodities com Rise/Fall de cinco minutos](https://docs.deriv.com/marketing/2025/ebook-commodities-en-hq.pdf) e [guia oficial de índices sintéticos com Higher/Lower de cinco minutos](https://docs.deriv.com/marketing/2025/ebook-synthetics-en-hq.pdf).

## Demo, região e elegibilidade

O cadastro fornece uma conta demo padrão. A API também documenta criação de conta Options demo, WebSocket demo e restauração do saldo virtual. A conta real exige verificação e fundos.

A lista legada oficial da API inclui o Brasil, mas isso não comprova que cada produto ou contrato esteja disponível. Os termos atuais exigem idade mínima de 18 anos, residência aceita e conformidade com a lei local; entidade, produtos e mercados variam conforme a residência e podem mudar. A elegibilidade final deve ser confirmada pelo cadastro/KYC e pelas respostas autenticadas da conta. Não foi localizada uma lista atual e definitiva de todas as jurisdições bloqueadas para Options.

Fontes: [Options Setup](https://developers.deriv.com/docs/options/), [criação de conta](https://developers.deriv.com/docs/options/create-account/), [termos gerais](https://deriv.com/terms-and-conditions/general-terms-of-use), [mercados por país](https://deriv.com/help-centre-question/markets-on-deriv-trader) e [lista legada oficial de países](https://legacy-docs.deriv.com/docs/country-list).

## Limites oficiais atuais

| Grupo | Por minuto | Por hora |
|---|---:|---:|
| WebSocket: `proposal`, `proposal_open_contract`, `buy`, `sell` | 360 | 14.400 |
| WebSocket: `balance`, `statement` | 100 | 2.000 |
| WebSocket: `portfolio`, `profit_table` | 30 | 1.500 |
| Demais mensagens WebSocket | 220 | 14.400 |

REST permite 300 requisições/minuto e 1.000/10 minutos por IP; usuário autenticado tem 80/minuto. `ping` fica fora desses grupos e aceita até 10/s por conexão. Orçamentos WebSocket são compartilhados entre as mensagens de cada linha. A Deriv reserva o direito de mudar os limites; o cliente deve assinar em vez de consultar repetidamente, limitar rajadas e recuar após rejeição.

Fonte: [limites da Deriv API](https://developers.deriv.com/docs/limits/).

## Termos e riscos de conformidade

Os [termos para usuários da API](https://deriv.com/terms-and-conditions/api-users) concedem uma licença limitada e revogável para desenvolver e testar aplicações. Pontos que afetam diretamente esta arquitetura:

- Conteúdo originado no site ou acessado pela API, inclusive feed, não pode ser armazenado; cache é permitido por até 24 horas.
- Limites podem mudar, e abuso ou excesso consistente pode bloquear o acesso.
- A API pode mudar ou ser descontinuada, sem garantia de compatibilidade retroativa.
- O operador é responsável por segurança, transações, comunicações e perdas.

Os [termos de negociação](https://deriv.com/terms-and-conditions/trading-terms) permitem que a Deriv imponha e altere restrições e regras. Os [termos gerais](https://deriv.com/terms-and-conditions/general-terms-of-use) tornam o serviço dependente de residência e lei local. Esta avaliação técnica não substitui confirmação contratual ou jurídica.

## Pendências obrigatórias

1. Obter confirmação escrita da Deriv sobre armazenamento, uso para ML, retenção de auditoria e eventual licença de dados; sem isso, manter somente cache de 24 horas.
2. Registrar um aplicativo PAT, criar credencial com o menor escopo necessário e validar conta demo, região, moeda e contratos autenticados. Nenhuma credencial deve entrar no repositório.
3. Implementar primeiro um adaptador demo com `REAL_EXECUTION_ENABLED=false`, allowlist de conta demo e bloqueio independente contra URL `.../ws/real`.
4. Testar perda de conexão antes/depois de `buy`, proposta vencida, duplicidade, rate limit, reconciliação, payout alterado e parada de emergência.
5. Submeter o adaptador e os segredos à revisão de segurança da Fase 12 antes de reconsiderar execução real.

## Limitações desta avaliação

- Não foi usada uma conta autenticada; disponibilidade por conta, payout e elegibilidade regional ainda não estão validados.
- A proposta pública muda em tempo real e não demonstra qualidade de execução, slippage, rentabilidade ou disponibilidade futura.
- A documentação atual e materiais oficiais mostram contratos de cinco minutos, mas não garantem esse prazo em todo ativo.
- A restrição de armazenamento impede considerar a Deriv fonte histórica do pipeline atual sem permissão adicional.
