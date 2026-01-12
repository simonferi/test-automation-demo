# Payments Smoke Runtime Scenario

Tento dokument zachytáva kompletný testovací scenár, ktorý verifikuje všetky aplikácie v reťazci (intake → mock generator → test generator → mock runtime → smoke runtime) pre službu Payments.

## Prerekvizity
- Windows PowerShell (príkazy používajú spätné apostrofy `\`` na zalomenie riadku).
- Projekt synchronizovaný pomocou `uv sync` (alebo spustený v prostredí, kde sú závislosti dostupné).
- OpenAPI špecifikácia `specs/payments.yaml`.
- Prázdne/čisté adresáre:
  - `workspace/catalog`
  - `artifacts/mocks`
  - `artifacts/tests`
  - `runs`

> **Poznámka:** Všetky cesty sú relatívne ku koreňu repozitára (`C:\disk_d\workspace\AI_HUB\test-automation-demo`).

## Krok 1 – Normalizácia špecifikácie (`contract-parser`)
Validuje OpenAPI a uloží IR JSON.

```powershell
uv run python apps/contract-parser/contract_parser/main.py `
  --spec specs/payments.yaml `
  --output-dir workspace/catalog
```

- Výstup: `workspace/catalog/payments-api/1.0.0.json`

## Krok 2 – Generovanie mock konfigurácie (`mock-config-builder`)
Z IR vytvorí YAML konfiguráciu pre mock server.

```powershell
uv run python apps/mock-config-builder/mock_config_builder/main.py `
  --ir workspace/catalog/payments-api/1.0.0.json `
  --output-dir artifacts/mocks `
  --port rest=9101
```

- Výstup: `artifacts/mocks/payments-api/1-0-0/mock-config.yaml` s REST serverom na porte 9101.

## Krok 3 – Generovanie test bundle (`test-scenario-builder`)
Vytvorí scenár, payloady a metadáta pre test executor.

```powershell
uv run python apps/test-scenario-builder/test_scenario_builder/main.py `
  --ir workspace/catalog/payments-api/1.0.0.json `
  --output-dir artifacts/tests `
  --scenario-prefix smoke
```

- Výstup: `artifacts/tests/payments-api/1.0.0/` obsahuje test bundle s testovacími prípadmi.

## Krok 4 – Spustenie mock servera (`mock-server`)
Mock server je možné spustiť v samostatnom PowerShell jobe, aby bežal súbežne s testami.

```powershell
$mockJob = Start-Job -ScriptBlock {
  Set-Location 'C:/disk_d/workspace/AI_HUB/test-automation-demo'
  $env:CONSOLE_OUTPUT_FORMAT = "rich"
  uv run python apps/mock-server/mock_server/main.py `
    --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml
}
# Voliteľne sledujte logy:
Receive-Job -Id $mockJob.Id -Keep
```

Po štarte server vypíše informácie o dostupných REST trasách. Pre ukončenie použite `Stop-Job` + `Receive-Job` + `Remove-Job`.

## Krok 5 – Spustenie testov (`test-executor`)
Výkon smoke testov proti bežiacemu mock serveru.

```powershell
$env:CONSOLE_OUTPUT_FORMAT = "rich"
uv run python apps/test-executor/test_executor/main.py `
  --bundle artifacts/tests/payments-api/1.0.0 `
  --output-dir runs
```

- Každý beh vytvorí adresár `runs/<scenario_id>-<timestamp>/` s `results.json` a `summary.txt`.

## Overenie výsledkov
- Skontrolujte `results.json` pre celkové počty testov a zlyhania.
- Záznamy mock servera (viď PowerShell job) potvrdzújú, že každý endpoint obdržal požiadavku.
- Test executor interpretuje test bundle priamo; použite environment premenné, ak chcete mieriť na reálne API namiesto mocku.

## Riešenie problémov
- **Žiadne odpovede z mock servera:** overte, že port 9101 nie je blokovaný a job stále beží (`Get-Job`).
- **Chyby HTTP testov:** logy v `runs/` obsahujú detailné informácie o request/response pároch pre rýchle ladenie.

## Cleanup
1. Ukončite mock runtime job (`Stop-Job`, `Receive-Job`, `Remove-Job`).
2. Odstráňte alebo archivujte obsah `runs/`, `artifacts/mocks/`, `artifacts/tests/`, ak potrebujete čisté prostredie.

Týmto postupom je overená funkčnosť všetkých CLI nástrojov aj plného testovacieho toku pre službu Payments.
