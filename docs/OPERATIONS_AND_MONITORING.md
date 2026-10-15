# Operação e monitoramento — Fase 10

## Estado seguro

O sistema continua em simulação. `REAL_EXECUTION_ENABLED=false` e `EXECUTION_MODE=simulation` são obrigatórios. A saúde geral permanece `degraded` enquanto dados de mercado reais e o motor como serviço não estiverem configurados. Estado desconhecido, dado vencido, notícia sem cobertura, risco excedido ou modelo pausado resultam em abstenção.

## Promoção e reversão

1. Separe o holdout antes de qualquer ajuste com `evaluate_untouched_holdout`.
2. Gere `PromotionAssessment`; todos os critérios e a identidade do holdout precisam passar.
3. Registre versão, features, SHA-256 do dataset, URI e SHA-256 do artefato.
4. Um operador chama `ModelRegistry.promote`; a versão anterior passa a `retired`.
5. Em incidente, pause a versão ativa e execute `rollback(reason=...)`. Cada transição gera evento.

O artefato deve ser imutável no local indicado. Confira seu checksum antes de carregar. A reversão só escolhe uma versão que já esteve ativa.

## Sinais e alertas

O monitor calcula PSI para features numéricas, Brier e erro esperado de calibração sobre resultados liquidados. Amostras menores que 100 são marcadas `insufficient_data`, sem inventar métricas.

| Estado | Critério padrão | Ação |
|---|---|---|
| `healthy` | PSI < 0,10, ECE < 0,08 e Brier < 0,26 | manter simulação |
| `warning` | algum limite de aviso atingido | investigar dados e segmentos |
| `blocked` | PSI ≥ 0,25, ECE ≥ 0,12 ou Brier ≥ 0,30 | pausar decisões do modelo |
| `insufficient_data` | feature ou resultado abaixo da amostra mínima | manter abstenção onde a avaliação for obrigatória |

O monitor recomenda pausa; ele não altera stake, payout, limites de risco nem promove versões. A pausa é uma ação explícita e auditável do operador.

## Resposta a incidente

1. Pare novas decisões e preserve operações em papel já abertas para liquidação auditável.
2. Registre horário, versão, ativo, alerta, request ID e intervalo afetado.
3. Verifique frescor e continuidade dos candles, cobertura de notícias e estado do banco.
4. Pause o modelo quando `should_pause=true`; reverta se existir versão anterior saudável.
5. Só retome depois de repetir qualidade, holdout, monitoramento e smoke test.

Nunca apague registros para “corrigir” um incidente. Faça correções aditivas com evento e motivo.

## PostgreSQL

Suba o banco em `infrastructure` com `docker compose up -d --wait`. Em volume já existente, aplique os SQLs novos em ordem; a inicialização automática só ocorre na primeira criação do volume. Antes de migração ou atualização, produza backup:

```powershell
docker compose exec -T postgres pg_dump -U binary_ai -d binary_intelligence_ai -Fc > binary-intelligence-ai.dump
```

Teste a restauração em outro banco. Preserve `model_versions`, `model_events`, `monitoring_assessments`, resultados de backtest, operações em papel e auditoria de risco. Defina retenção conforme volume e obrigação local antes de usar dados externos.

## Verificação de release

Execute testes Python, teste integrado com PostgreSQL, build da API, build do dashboard e chamada de `/api/health`. O release falha se qualquer etapa falhar. Segredos ficam somente no ambiente; `.env`, dumps e artefatos de modelo não entram no Git.

## Limites atuais

Não há feed real, provedor econômico real, corretora, execução financeira, agendador de monitoramento ou evidência de rentabilidade. O rollback opera no registro; o processo que serve inferência ainda precisa recarregar explicitamente a versão ativa.
