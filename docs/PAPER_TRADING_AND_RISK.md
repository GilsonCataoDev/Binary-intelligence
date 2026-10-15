# Paper trading e gestão de risco — Fase 8

## Fluxo

O modelo fornece probabilidades. O motor `decisions` recalcula a probabilidade de equilíbrio `1 / (1 + payout)` e o valor esperado. Uma operação só é aceita quando os dados são válidos, as probabilidades estão calibradas, o modelo está aprovado, o payout é atual, notícias e volatilidade permitem e todos os controles de risco aprovam.

Como o pipeline formal de promoção será implementado na Fase 10, os modelos atuais não estão aprovados para operação. Os testes de paper trading usam decisões aprovadas construídas explicitamente como fixtures.

## Controles independentes

`RiskManager` aplica exposição máxima, perda diária, drawdown, máximo diário de operações, perdas consecutivas, erros operacionais, dados desatualizados, volatilidade extrema, pausa e parada de emergência. O valor da entrada tem limite fixo; não existe martingale ou aumento para recuperar perdas.

A parada de emergência exige liberação explícita. A troca do dia UTC reinicia apenas os contadores diários; saldo e pico histórico são preservados.

## Simulação

`PaperTradingEngine` cria operações virtuais somente para CALL ou PUT, usa chave de idempotência, impede liquidação antes da expiração e calcula ganho, perda ou empate. O resultado é identificado como `paper` no banco e nunca é misturado com backtest ou execução real.

As tabelas `paper_trades` e `risk_audit_events` armazenam operações e eventos auditáveis. Ainda não existe adaptador de execução real.

## Limitações

- O estado em memória será orquestrado e recuperado pela API na Fase 9.
- Não há modelo promovido nem payout ao vivo.
- Retomada automática após limites de perda não foi habilitada.
- Reconciliação externa pertence a uma futura integração oficial.

## Executar

```powershell
cd services/ai-engine
.\.venv\Scripts\python.exe -m pytest -q
```

Em volume PostgreSQL existente, aplique `infrastructure/postgres/005_paper_trading.sql` antes do teste de integração.
