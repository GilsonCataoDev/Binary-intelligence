# Baselines e backtesting — Fase 5

## Regra de previsão e liquidação

A decisão é tomada no fechamento confirmado do candle de referência. Para candles M1 e horizonte de cinco passos, o preço de liquidação é o fechamento observado exatamente cinco minutos depois. Os últimos cinco registros não recebem rótulo porque seu resultado ainda não existe no conjunto.

`entry_delay_steps` desloca o preço de entrada e o início do horizonte. `execution_offset_bps` aplica uma diferença assinada entre o feed analisado e o preço de referência. Ambos começam em zero e só devem ser alterados com cenários declarados ou medições. Como os dados atuais são M1, essa latência é grosseira; ticks serão necessários para estimativas abaixo de um minuto.

O resultado é `up`, `down` ou `tie`. A tolerância de empate é configurável e começa em zero. Empate pode ser `push` (retorno zero) ou `loss` (perda de uma unidade), sempre registrado no relatório.

## Separação temporal

O walk-forward usa treino expansivo, teste posterior e `gap` mínimo igual ao horizonte. Assim, todo rótulo usado no treino já estaria liquidado antes da primeira decisão do teste. Normalização, seleção de variáveis e modelos candidatos deverão ser ajustados dentro de cada fold na Fase 6.

## Referências implementadas

- `FrequencyBaseline`: estima a probabilidade de alta apenas pela frequência do treino. Opera somente se a direção superar `1 / (1 + payout)`.
- `TechnicalRuleBaseline`: usa ADX, EMA 12/26 e RSI como regra comparativa. Não declara probabilidade nem calibração.

Os níveis técnicos são referências configuráveis para comparação, não uma estratégia aprovada.

## Métricas

O relatório inclui operações, abstenções, acertos, erros, empates, retorno líquido em unidades, expectativa, drawdown máximo, intervalo de Wilson de 95%, Brier score, log loss, calibração, resultado por hora/regime e sensibilidade a payouts de 0,70, 0,80 e 0,90.

O `BacktestRepository` persiste a configuração, métricas e cada previsão fora da amostra. Isso permite reconstruir o resultado sem misturá-lo com paper trading ou operações reais.

Sem histórico de propostas da plataforma, o payout é **hipotético**. O retorno do backtest não representa paper trading, execução real nem expectativa de lucro futuro. Divergência entre o feed analisado e o preço de liquidação continua sem medição.
