# Indicadores e regimes — Fase 4

## Garantia temporal

Cada linha de features usa somente o candle encerrado daquela linha e candles anteriores. Suporte e resistência aplicam `shift(1)`, portanto o candle atual não define o nível contra o qual ele próprio é comparado. Um teste compara a mesma linha calculada com histórico truncado e completo; os resultados devem ser idênticos.

Durante o aquecimento, features indisponíveis permanecem nulas. Elas não são convertidas em zero, pois zero significaria que a condição foi observada e não ocorreu.

O serviço `analyze_market` valida a série antes de calcular indicadores. Dados abertos, antigos, duplicados, fora de ordem ou com lacunas retornam `should_abstain=true`.

## Features implementadas

- Retorno simples, SMA 5/20, EMA 12/26 e MACD 12/26/9.
- RSI 14, ATR 14 e ADX 14 com suavização exponencial de Wilder.
- Bandas de Bollinger 20 com dois desvios e largura normalizada.
- Suporte, resistência, rompimentos e falsos rompimentos com janela anterior de 20 candles.
- Pullbacks na EMA 12 e estrutura recente de máximas e mínimas.
- Distância aos níveis em unidades de ATR e geometria do candle: corpo, pavios, direção e doji.

## Classificação inicial

O regime usa ADX e posição relativa das EMAs para `trending_up`, `trending_down` ou `ranging`. A volatilidade compara ATR/preço aos percentis móveis 20 e 80 da própria série. A resposta inclui o regime anterior e sinaliza transição no último candle fechado. São regras iniciais explicáveis, não evidência de vantagem e não sinais de entrada.

O limite ADX 25 é configurável e deverá ser validado por classe de ativo na Fase 5. A classificação exige aquecimento suficiente; antes disso retorna `insufficient_data` e exige abstenção.
