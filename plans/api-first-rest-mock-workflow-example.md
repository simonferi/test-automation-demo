# API First Rest Mock Workflow Example #1

Tento dokument opisuje kompletný lokálny scenár, v ktorom z jednej OpenAPI špecifikácie vznikne spustiteľný REST mock server. Postup využíva tri CLI nástroje z tohto monorepa a ukazuje, ako ich zreťaziť do jedného skriptu.

## Rýchly variant – skript `scripts/payments-smoke-e2e.ps1`

Ak chcete vyskúšať celý tok (parsing → mock konfigurácia → mock server + smoke testy), použite pripravený PowerShell skript:

```powershell
pwsh ./scripts/run-smoke-pipeline.ps1 `
  -SpecPath specs/payments.yaml `
  -MockPort 9101 `
  -OutputFormat rich
```

Parametre môžete upraviť pre ľubovoľnú OpenAPI špecifikáciu (napr. `specs/commerce.yaml`, `specs/flights.yaml`). Skript spustí všetky komponenty v správnom poradí a následne spustí mock server na pozadí, takže okamžite vygeneruje aj `runs/<service>-<version>-<timestamp>/results.json`. Zvyšok dokumentu ponecháva detailný manuálny walkthrough, ktorý sa stále hodí, keď skript potrebujete prispôsobiť alebo spustiť každý krok zvlášť.

## Prerekvizity
- Windows PowerShell alebo Bash (príklady nižšie používajú PowerShell).
- `uv` synchronizovaný projekt (`uv sync`).
- OpenAPI/Swagger súbor uložený v `specs/payments.yaml` (možno prispôsobiť).
- Prázdne adresáre:
  - `workspace/catalog` – uloženie IR.
  - `artifacts/mocks` – mock konfigurácie.

## Krok 1 – contract-parser
**Cieľ:** Validovať OpenAPI a vytvoriť normalizovaný IR JSON.

```powershell
uv run python apps/contract-parser/contract_parser/main.py `
  --spec specs/payments.yaml `
  --output-dir workspace/catalog
```

Výstup: `workspace/catalog/payments-api/1.0.0.json` (názov služby a verzia sa automaticky detekujú zo špecifikácie).

## Krok 2 – mock-config-builder
**Cieľ:** Z IR vyrobiť konfiguráciu pre mock server.

```powershell
uv run python apps/mock-config-builder/mock_config_builder/main.py `
  --ir workspace/catalog/payments-api/1.0.0.json `
  --output-dir artifacts/mocks `
  --port rest=9101
```

Výstup: `artifacts/mocks/payments-api/1-0-0/mock-config.yaml` s definíciou servera, portov a odpovedí.

## Krok 3 – mock-server
**Cieľ:** Spustiť server podľa vytvorenej konfigurácie.

```powershell
$env:CONSOLE_OUTPUT_FORMAT = "rich"
uv run python apps/mock-server/mock_server/main.py `
  --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml
```

Server otvorí port 9101 a bude odpovedať na definované REST endpointy. Logy používajú structured logging so štyrmi formátmi (auto, rich, plain, json).

## Jednotný PowerShell skript
Nasledujúci skript spája všetky kroky do jedného testovacieho scenára. Uložte ho napr. do `scripts/api-first-rest-mock-example.ps1`.

```powershell
param(
  [string]$SpecPath = "specs/payments.yaml",
  [string]$Service = "Payments",
  [string]$Version = "1.0.0",
  [string]$RestPort = "9101"
)

$ErrorActionPreference = "Stop"
$serviceSlug = ($Service.ToLower() -replace ' ', '-')
$versionSlug = ($Version.ToLower() -replace '[^0-9a-z_-]', '-')
$irFile = "workspace/catalog/$serviceSlug/$Version.json"
$mockDir = "artifacts/mocks/$serviceSlug/$versionSlug"
$configFile = "$mockDir/mock-config.yaml"

Write-Host "[1/4] Contract Parser" -ForegroundColor Cyan
uv run python apps/contract-parser/contract_parser/main.py `
  --spec $SpecPath `
  --output-dir "workspace/catalog"

Write-Host "[2/4] Mock Config Builder" -ForegroundColor Cyan
uv run python apps/mock-config-builder/mock_config_builder/main.py `
  --ir $irFile `
  --output-dir "artifacts/mocks" `
  --port "rest=$RestPort"

Write-Host "[3/4] Test Scenario Builder" -ForegroundColor Cyan
uv run python apps/test-scenario-builder/test_scenario_builder/main.py `
  --ir $irFile `
  --output-dir "artifacts/tests" `
  --scenario-prefix smoke

Write-Host "[4/4] Mock Server" -ForegroundColor Cyan
uv run python apps/cli-mock-runtime/cli_mock_runtime/main.py `
  --config $configFile `
  --log-level INFO `
  --log-format json
```

> Poznámka: krok 3 drží proces otvorený (počas testu). Ukončite ho `Ctrl+C`, ak potrebujete skript ukončiť. Pre neblokujúci beh možno použiť PowerShell `Start-Process` alebo `Start-Job`.

## Overenie mock servera
Po spustení kroku 3 môžete v inom okne overiť správanie cez `curl` alebo `Invoke-RestMethod`:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:9101/payments -Method GET
```

Očakávaná odpoveď zodpovedá payloadu, ktorý vygenerovala `cli-mock-generator` pre daný endpoint.

## Čistenie a ďalšie scenáre
- Zastavte runtime (`Ctrl+C`).
- Pre ďalší scenár zmeňte názov služby, verziu alebo porty v skripte. IR aj mock konfigurácia sa uloží do oddelených priečinkov, takže je možné mať viac instancií runtime paralelne (stačí unikátne porty).
