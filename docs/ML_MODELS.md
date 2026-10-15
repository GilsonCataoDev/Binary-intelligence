# Modelos tabulares e calibração — Fase 6

## Candidatos

- Regressão logística: referência interpretável com imputação e padronização ajustadas dentro do treino.
- Random Forest: 80 árvores, profundidade e folhas limitadas para reduzir sobreajuste.
- Histogram Gradient Boosting do Scikit-learn: boosting tabular regularizado, sem dependência adicional de XGBoost ou LightGBM.

Todos usam o conjunto `technical-v1`. Redes neurais não foram incluídas porque ainda não há evidência de volume ou estrutura de dados que justifique sua complexidade.

## Separação e calibração

Em cada fold walk-forward, o período de treino é novamente dividido em treino-base, gap de cinco candles e calibração posterior. Imputação, escala e modelo são ajustados somente no treino-base. Uma regressão logística de Platt calibra as probabilidades no período seguinte. O teste externo permanece intocado até a inferência.

Empates são preservados no backtest e tratados pela regra configurada, mas não entram no ajuste binário de alta/baixa. Nenhum resultado é usado antes de sua liquidação.

## Decisão e promoção

CALL ou PUT somente ocorre quando a probabilidade calibrada da direção supera `1 / (1 + payout)`. Caso contrário, a decisão é `ABSTAIN`.

Um candidato só é aprovado quando cumpre simultaneamente:

1. mínimo de 300 observações fora da amostra;
2. melhora de Brier de pelo menos 0,002 sobre o baseline de frequência;
3. log loss sem regressão;
4. erro esperado de calibração de no máximo 0,08;
5. vitória em pelo menos 60% dos folds;
6. limite inferior do intervalo de 95% da taxa de acerto acima do break-even do payout.

Os critérios são conservadores e versionados no código. Aprovação estatística de um candidato não habilita execução real e não autoriza alteração de risco.

Como comparar vários candidatos no mesmo histórico introduz viés de seleção, `approved` permanece falso até que uma avaliação em holdout intocado seja explicitamente confirmada. O holdout deve ser separado antes de ajustar hiperparâmetros ou escolher o modelo.
