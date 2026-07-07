# YML Operational Excellence Hotfix

Este documento fixa o padrão mínimo para workflows GitHub Actions do projeto `relativity-living-light`.

Objetivo: reduzir falha em cascata, preservar confiabilidade acadêmica e manter rastreabilidade operacional sem promover claims científicos por efeito de CI.

## Diagnóstico do incidente

Um commit em um workflow disparou múltiplos workflows. Isso expôs três classes de problema:

1. acoplamento excessivo entre workflows;
2. comandos `run:` frágeis com strings multilinha difíceis de auditar;
3. gates que misturavam erro sintático bloqueante com auditoria metodológica ainda em refatoração.

## Princípios de correção

### 1. Sintaxe é gate bloqueante

Todo `.yml` e `.yaml` deve passar por parser real.

Falha de sintaxe deve falhar o workflow.

### 2. Auditoria metodológica é evidência consultável por padrão

A auditoria de política de workflows deve produzir artefato, log e status JSON.

Ela só deve bloquear quando `strict_workflow_audit=true` for escolhido manualmente.

Motivo: durante refatoração de muitos workflows, bloquear tudo por lacunas conhecidas impede estabilização progressiva.

### 3. Menor privilégio

Padrão:

```yaml
permissions:
  contents: read
```

Permissão de escrita só pode existir em job separado, manual ou opt-in explícito.

### 4. Concorrência controlada

Padrão:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Exceção: workflows de snapshot/rollback podem usar `cancel-in-progress: false` quando a ordem histórica importar.

### 5. Timeout obrigatório

Todo job executável precisa de `timeout-minutes`.

Sugestões:

| Tipo | Timeout |
| --- | --- |
| lint / YAML / schema | 5–10 min |
| testes focados | 10–20 min |
| pipeline científico | 30 min |
| Android/Gradle | 45–60 min |

### 6. Checkout seguro

Padrão:

```yaml
- uses: actions/checkout@v4
  with:
    persist-credentials: false
```

Exceção: jobs que fazem commit/push explícito devem justificar a escrita e ficar isolados.

### 7. Shell determinístico

Para blocos complexos:

```yaml
run: |
  set -euo pipefail
  comando
```

Evitar strings longas entre aspas com heredoc embutido.

### 8. Artefatos não devem quebrar diagnóstico

Em workflows de validação durante refatoração:

```yaml
if: always()
if-no-files-found: warn
retention-days: 14
```

Usar `error` apenas quando a ausência do artefato for o próprio resultado testado.

### 9. Claim boundary obrigatório em workflows científicos

Todo workflow que toque dados reais, validação cosmológica, RLL, seed real ou resultado científico deve declarar limite de claim.

Padrão textual:

```yaml
CLAIM_BOUNDARY: Auxiliary real-data workflow only; no RLL/cosmology/superiority claim and no synthetic, mock, fixture, demo, example, or placeholder promotion beyond explicit run checks.
```

### 10. Separação entre ciência e CI

CI confirma:

- estrutura;
- reprodutibilidade local;
- presença de artefatos;
- checksums;
- limites de claim.

CI não confirma:

- validade científica final;
- superioridade sobre LCDM/CPL;
- aceitação acadêmica;
- evidência observacional além dos dados efetivamente processados.

## Hotfix aplicado

### YAML Syntax Validation Gate

Alteração: separar parse YAML bloqueante de auditoria de política consultável.

- YAML inválido continua bloqueando.
- Auditoria de política gera `workflow_audit.log` e `workflow_audit_status.json`.
- Auditoria só bloqueia se `strict_workflow_audit=true`.

### Workflows endurecidos

- `.github/workflows/RLL-CI.yml`
- `.github/workflows/RLL_SCIENTIFIC.yml`
- `.github/workflows/android-build.yml`

Padrões adicionados:

- `permissions: contents: read`
- `concurrency`
- `timeout-minutes`
- `persist-credentials: false`
- uploads com `if: always()` e `if-no-files-found: warn` quando apropriado

## Padrão recomendado para próximos hotfixes

1. corrigir um workflow por vez;
2. não alterar scripts científicos junto com YAML;
3. preservar claim boundary;
4. mover escrita para job opt-in;
5. manter auditoria em artefatos;
6. só tornar strict depois de zerar lacunas conhecidas.

## Estado operacional

- `F_DE_RESOLVIDO`: sintaxe YAML separada de auditoria metodológica; workflows principais endurecidos.
- `F_DE_GAP`: workflows com escrita ou schedule podem exigir revisão manual por política de segurança.
- `F_DE_NEXT`: continuar refatoração por blocos pequenos, começando pelos workflows que aparecem no ledger com `LACUNA_CONCURRENCY`, `LACUNA_TIMEOUT` ou `LACUNA_PERMISSIONS`.
