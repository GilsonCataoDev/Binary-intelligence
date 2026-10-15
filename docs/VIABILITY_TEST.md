# Teste de viabilidade com dados públicos da Deriv

Executado em **15/10/2026**. Pergunta: algum modelo do projeto acerta a direção com frequência suficiente para superar o payout real?

## Como funciona

`python -m binary_intelligence_ai.research.viability --symbol <símbolo> --horizon-minutes <n> --days <n>` (requer `pip install -e ".[research]"`).

1. Baixa candles M1 públicos da Deriv **somente em memória**; nenhum preço é gravado em disco (os termos limitam o cache a 24 h). A saída contém apenas métricas agregadas.
2. Obtém o payout atual de uma proposta CALL na duração pedida (fotografia do momento; o valor varia).
3. Divide a série em trechos contínuos (fechamentos de mercado) e rotula cada trecho separadamente, sem resultado atravessando um fechamento.
4. Roda walk-forward com treino crescente: baselines de frequência e regra técnica e os três candidatos calibrados (`technical-v1`). Toda previsão é fora da amostra.
5. Aplica os critérios estatísticos de promoção de `models/promotion.py`. Empate conta como perda, pois a Deriv paga somente se o preço for *estritamente* maior/menor.

## Descobertas sobre o produto

- **EUR/USD de 5 minutos não é oferecido pela Deriv**: a duração intradiária mínima é 15 minutos. A premissa original do projeto não existe nessa corretora.
- Índices sintéticos (ex.: `R_100`) aceitam 5 minutos, mas são gerados por sorteio; servem apenas como controle.

## Resultados

| Teste | Período | Observações fora da amostra | Payout líquido | Acerto necessário | Melhor acerto obtido | Resultado |
|---|---|---|---|---|---|---|
| Controle `R_100`, 5 min | 30 dias | 38.190 (20 folds) | 0,96 | 51,0% | 50,5% (IC95 49,8–51,2%) | todos negativos |
| `frxEURUSD`, 15 min | 4 dias | 374 (1 fold) | 0,82 | 54,9% | 62,8% (IC95 54,2–70,7%) | inconclusivo |
| `frxEURUSD`, 15 min | 60 dias | 55.616 (28 folds) | 0,87 | 53,5% | 51,8% (IC95 50,9–52,7%) | todos negativos |

No teste de 60 dias, em unidades de aposta: regra técnica −2.101; logística −386; random forest −916; boosting −836. Nenhum candidato superou o baseline em Brier, log loss ou maioria dos folds.

O teste de 4 dias ilustra o risco de amostras pequenas: 62% de acerto parece vantagem, mas desaparece quando o período é ampliado.

## Conclusão

**Não há evidência de vantagem.** Com indicadores técnicos (`technical-v1`) e os modelos atuais, a direção de EUR/USD em 15 minutos fica próxima de 50%, abaixo do break-even de ~53–55%. O controle sintético confirma que o procedimento não produz falsos positivos. Conclusão coerente com a decisão **NO-GO** da Fase 12.

## Limitações

- Liquidação aproximada pelo fechamento de candles M1, não pelos ticks de entrada e saída do contrato.
- Payout é a cotação do momento, aplicada a todo o período.
- Testa apenas o conjunto de features atual; outra abordagem exigiria nova avaliação com o mesmo rigor, inclusive holdout intocado.
