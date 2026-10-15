# Notícias e contexto econômico — Fase 7

## Escopo entregue

O módulo `news` normaliza eventos, registra a origem, preserva os horários de publicação, evento e ingestão, associa ativos, impacto informado e evidências. O contrato exige UTC e rejeita registros sem horário verificável.

O `JsonNewsProvider` permite testes reproduzíveis com arquivos obtidos legalmente. Ele filtra informações que ainda não estavam publicadas ou ingeridas no momento analisado. O `UnavailableNewsProvider` representa explicitamente a ausência de cobertura. Nenhuma API externa ou notícia sintética foi adicionada.

## Bloqueio de segurança

O guardião determinístico bloqueia decisões em uma janela configurável, inicialmente 15 minutos antes e depois de eventos de alto impacto. Notícias não programadas só podem bloquear a partir de sua publicação; o sistema não presume conhecimento anterior.

Por padrão, cobertura degradada ou indisponível também bloqueia. O resultado informa os identificadores dos eventos e os motivos, permitindo auditoria e futura integração com o motor de decisão.

## Persistência e retenção

A migração `004_news_events.sql` armazena metadados normalizados e oferece um campo opcional para payload bruto. O payload só deve ser mantido quando a licença da fonte permitir. A identidade `(source, source_event_id)` impede duplicação.

## Limitações

- Não existe feed ao vivo configurado nem garantia de cobertura.
- Impacto é preservado como informado pela fonte; o sistema não o inventa.
- Classificação por NLP foi adiada até existir um conjunto real, licenciado e avaliável.
- O mapeamento entre eventos macroeconômicos e ativos precisa ser fornecido ou validado pela fonte escolhida.

## Executar no Windows PowerShell

```powershell
cd services/ai-engine
.\.venv\Scripts\python.exe -m pytest -q
```

Para aplicar a nova tabela em um volume PostgreSQL que já existia:

```powershell
cd infrastructure
docker compose up -d --wait
Get-Content .\postgres\004_news_events.sql | docker compose exec -T postgres psql -U binary_ai -d binary_intelligence_ai
```
