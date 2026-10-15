# Modelos tabulares, holdout e promoção — Fases 6 e 10

## Candidatos

- Regressão logística: referência interpretável com imputação e padronização ajustadas dentro do treino.
- Random Forest: 80 árvores, profundidade e folhas limitadas para reduzir sobreajuste.
- Histogram Gradient Boosting do Scikit-learn: boosting tabular regularizado, sem dependência adicional de XGBoost ou LightGBM.

Todos usam o conjunto `technical-v1`. Redes neurais não foram incluídas porque ainda não há evidência de volume ou estrutura de dados que justifique sua complexidade.

## Separação e calibração

Em cada fold walk-forward, o período de treino é novamente dividido em treino-base, gap igual ao horizonte mais o atraso de entrada e calibração posterior. Imputação, escala e modelo são ajustados somente no treino-base. Uma regressão logística de Platt calibra as probabilidades no período seguinte. O teste externo permanece intocado até a inferência.

Empates são preservados no backtest e tratados pela regra configurada, mas não entram no ajuste binário de alta/baixa. Nenhum resultado é usado antes de sua liquidação.

`InferenceResult` define a fronteira auditável com probabilidades de alta e baixa, indicação de calibração, decisão, motivos, qualidade dos dados e versões do modelo e das features.

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

O holdout final é separado antes do ajuste, com gap temporal, e nunca participa do treino ou da calibração. A evidência registra SHA-256 do conjunto e das observações, versões, fim do treino, início do holdout e quantidade avaliada. A promoção só pode ficar aprovada quando essa evidência corresponde exatamente ao candidato e às observações comparadas.

O registro guarda versão de features, identidade do dataset, checksum e localização do artefato, métricas e estado. Toda promoção e reversão produz evento auditável. Um modelo não pode promover a si próprio nem alterar limites de risco.

Baseline e candidato também precisam ter fonte, ativo, período, payout, regra de liquidação e observações fora da amostra idênticos. A avaliação rejeita comparações incompatíveis.
