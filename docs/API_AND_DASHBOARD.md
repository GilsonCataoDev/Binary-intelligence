# API e dashboard — dados de BTC e ouro

A API NestJS usa prefixo `/api`. Todos os endpoints em `/api/v1` exigem `x-api-key`; a chave permanece local e nunca entra no dashboard compilado.

## Mercado

- `GET /api/v1/assets` lista os dois instrumentos aceitos: `BTCUSDT` e `XAUUSD`.
- `GET /api/v1/market/candles/BTCUSDT` consulta os últimos candles M5 públicos da Binance Spot.
- `GET /api/v1/market/candles/XAUUSD` consulta candles M5 UTC da Twelve Data e exige `TWELVE_DATA_API_KEY` apenas no processo da API.
- `POST /api/v1/analysis/:asset` remove o candle em formação, envia somente candles encerrados ao motor local e devolve `ABSTAIN` nesta versão.

As fontes são referências de pesquisa. Elas não são preço garantido de execução, não enviam ordens e não ficam expostas diretamente ao navegador.

## Dashboard

O painel apresenta o estado da pesquisa, qualidade dos candles, regime, fonte utilizada e execução real desabilitada. O campo aceita somente `BTCUSDT` ou `XAUUSD`. Sem uma chave válida da Twelve Data, a análise de ouro falha de forma explícita; o sistema não usa um fallback não verificado.

## Segurança

A API e o motor aceitam somente loopback. `EXECUTION_MODE=simulation` e `REAL_EXECUTION_ENABLED=false` continuam obrigatórios. Os controles do painel mudam somente estado local de simulação; não existe adaptador de execução.
