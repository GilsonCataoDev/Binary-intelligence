# Pesquisa de dados: Forex, ouro e BTC

Verificado em 15 de outubro de 2026.

## Decisão de escopo

O projeto trata `BTCUSDT` e `XAUUSD` como instrumentos de pesquisa separados. BTC/USDT é spot de uma exchange; XAU/USD é uma referência de metal precioso em relação ao dólar. Eles têm liquidez, horários, custos e microestrutura diferentes. Não se compartilha um modelo promovido entre eles.

## Fontes integradas

| Instrumento | Fonte | Integração | Situação | Limitações |
|---|---|---|---|---|
| BTC/USDT | Binance Spot | `GET /api/v3/klines`, M5, sem autenticação | implementada, somente leitura | Dados de uma única exchange; o endpoint tem limites por IP e não representa fill em outra venue. |
| XAU/USD | Twelve Data Forex API | `time_series`, M5, UTC, `TWELVE_DATA_API_KEY` | implementada, depende de chave/plano | Feed composto de referência; o plano define disponibilidade. Spread, swap e execução da conta não estão no candle. |

As duas integrações são exclusivamente de dados. Não há credenciais de trading e nenhum endpoint de ordem no código.

## Como os custos são tratados

O módulo `binary_intelligence_ai.trading` calcula o retorno direcional por unidade de notional:

```text
retorno líquido = retorno direcional bruto
                 − (spread + slippage + comissão + financiamento) / 10.000
```

Cada custo é um valor total estimado de ida e volta em pontos-base. A fórmula evita transformar taxa de acerto em suposto lucro. Custos iguais a zero significam “não foram fornecidos”; não significam que uma operação real não tem custos.

## Regras de pesquisa

1. O backtest usa somente candles encerrados.
2. O baseline de EMA pode ficar `long`, `short` ou `flat`; `flat` não cria posição.
3. O resultado deve ser separado cronologicamente e validado em janela fora da amostra antes de ser comparado.
4. Para ouro, a sessão da fonte e o fuso UTC precisam ser registrados; lacunas não podem ser preenchidas artificialmente.
5. Para BTC, uma mudança de exchange exige reavaliar preço, volume, custos e resultados.
6. Antes de paper trading, registrar spread, comissão, slippage e financiamento da conta e do instrumento efetivamente utilizados.

## Fontes oficiais

- Binance: [Market Data endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market) documenta candles (`klines`) e limites de requisição.
- Twelve Data: [Time Series API](https://twelvedata.com/docs/mcp) documenta séries de candles, intervalos de 1 minuto a 1 mês e uso de `timezone=UTC` para Forex/cripto.
- Twelve Data: [Forex API v2](https://support.twelvedata.com/en/articles/12520817-forex-api-v2) informa cobertura de metais preciosos, candles de 1 minuto a 1 mês e que o acesso depende do plano.

## Próxima etapa responsável

Alimentar o backtest com histórico autorizado de cada fonte, registrar custos reais de uma conta de demonstração e rodar validação walk-forward. Uma eventual integração de execução exige documentação da corretora, aprovação explícita e uma revisão de risco separada.
