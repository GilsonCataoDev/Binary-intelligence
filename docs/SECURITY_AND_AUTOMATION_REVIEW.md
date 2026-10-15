# Revisão de segurança e viabilidade — Fase 12

## Decisão

| Escopo | Decisão |
|---|---|
| Desenvolvimento local e dados simulados/CSV autorizados | **GO** |
| Paper trading local | **GO condicionado** a dados, payout e modelo válidos |
| Descoberta e propostas transitórias Deriv | **GO condicionado** aos termos e à conta |
| Piloto em conta demo Deriv | **NO-GO até concluir as pendências da Fase 11** |
| Execução com dinheiro real | **NO-GO** |

O projeto é um protótipo local auditável para pesquisa e simulação. Ele não está aprovado para automação real e não demonstra rentabilidade.

## Barreiras implementadas

- A API escuta somente em `127.0.0.1`, restringe CORS ao loopback, usa Helmet e valida entradas.
- A inicialização falha se a chave tiver menos de 32 caracteres, se o modo não for `simulation`, se `REAL_EXECUTION_ENABLED` não for `false` ou se a origem do painel não for local.
- Endpoints protegidos comparam a chave em tempo constante. Logs não incluem a chave e aceitam somente request IDs curtos e seguros.
- Limite local de requisições reduz abuso acidental. Estado é reiniciado junto com o processo; produção exigiria limite distribuído.
- O gateway revalida bot, dados, payout, exposição, perdas, provedor, autorização e parada de emergência. Todo provedor marcado como real é bloqueado por código.
- Risco, parada de emergência, promoção de modelos e monitoramento permanecem independentes do modelo.

## Riscos que impedem execução real

1. Os termos da Deriv limitam o cache do feed a 24 horas e impedem armazenamento permanente sem autorização; isso conflita com treino e auditoria persistentes.
2. Conta, região, contratos, payout, moeda, liquidação e permissões não foram validados de forma autenticada.
3. Não existe adaptador Deriv autenticado, reconciliação após desconexão, proteção comprovada contra compra duplicada ou allowlist de conta demo.
4. API e dashboard ainda exibem estado local em memória e não reconciliam continuamente o PostgreSQL e o motor Python.
5. A API usa uma única chave local. Produção exigiria identidade por usuário/serviço, rotação, papéis, cofre de segredos e trilha de administração.

## Dependências e dados

Os pacotes Node retornaram zero vulnerabilidades conhecidas no `npm audit` executado nesta fase. Isso é uma fotografia temporal, não monitoramento contínuo. Dependências Python e Node têm limites de versão principal; uma esteira futura deve executar auditoria de vulnerabilidades, gerar SBOM, fixar artefatos por checksum e bloquear releases vulneráveis.

`.env`, dumps, logs, artefatos de modelo e credenciais não entram no Git. A senha PostgreSQL do Compose é apenas para desenvolvimento local e a porta é ligada a `127.0.0.1`. Fora do computador local, use segredo aleatório, TLS, conta de privilégio mínimo, backup criptografado e política de retenção compatível com as licenças.

## Testes de abuso verificados

- Dado vencido bloqueia o gateway.
- Qualquer provedor real é bloqueado mesmo com pré-checagens positivas.
- Checklist incompleto nunca habilita demo; checklist completo ainda não habilita dinheiro real.
- Chave curta ou padrão impede a inicialização da API.
- `EXECUTION_MODE=real` e `REAL_EXECUTION_ENABLED=true` impedem a inicialização.
- Endpoint de integração informa demo e real como indisponíveis.

## Executar a verificação no Windows PowerShell

```powershell
cd services/ai-engine
.\.venv\Scripts\python.exe -m pytest

cd ..\..\apps\api
npm ci
npm audit
npm run build
$env:API_KEY = -join ((1..48) | ForEach-Object { [char](Get-Random -Minimum 33 -Maximum 127) })
$env:EXECUTION_MODE = "simulation"
$env:REAL_EXECUTION_ENABLED = "false"
npm run start

cd ..\dashboard
npm ci
npm audit
npm run build
```

## Condições mínimas para nova revisão

Uma nova decisão sobre demo exige autorização de dados, aplicativo registrado, conta demo elegível, contrato verificado em tempo real e testes de reconciliação, duplicidade, rate limit, desconexão e emergência. Dinheiro real exigiria ainda revisão jurídica, segurança externa, autenticação forte, segregação de funções, observabilidade contínua e um piloto formal com limites mínimos. Nenhuma dessas condições deve ser inferida a partir de backtest ou paper trading.
