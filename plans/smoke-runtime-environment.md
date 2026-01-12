# Smoke Runtime Test Environment

Tento dokument popisuje cieľové testovacie prostredie určené na spúšťanie smoke testov cez `test-executor`. Pokrýva predprípravu scenárov (API-first workflow), požadované komponenty a varianty vykonania buď proti lokálnym mock serverom (spusteným cez `mock-server`), alebo proti reálnym implementáciám API služieb.

## Architektúra prostredia

```
OpenAPI spec --> contract-parser --> IR (workspace/catalog)
         IR --> mock-config-builder --> mock-config (artifacts/mocks)
         IR --> test-scenario-builder  --> scenario bundle (artifacts/tests)
Scenario bundle + drivers --> test-executor --> runs/<scenario>/
Mock-config --> mock-server --> REST endpoint 127.0.0.1:9101 (voliteľné)
```

- **Contract IR**: normalizovaný JSON popis služby, uložený pod `workspace/catalog/<service>/<version>.json`.
- **Mock configuration**: YAML/JSON definícia serverov a trás, ktorú vie načítať `mock-server`.
- **Scenario bundle**: adresár s `scenario.yaml`, payloadmi a Python driver modulom, ktorý vykonáva jednotlivé kroky.
- **Smoke runtime**: Typer CLI (`test-executor`) načítava scenár, spúšťa kroky a ukladá artefakty (`events.jsonl`, `summary.json`, `results.junit.xml`).

> Tip: Celý tok vrátane spustenia mock servera a smoke behu si môžete vyskúšať príkazom `pwsh ./scripts/run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml`. Parametre `-MockPort` a `-OutputFormat` umožnia znovu použiť skript pre `commerce` alebo `flights` špecifikácie.

## Prerekvizity

1. `uv` (https://github.com/astral-sh/uv) zosynchronizované cez `uv sync` – všetky CLI nástroje sa spúšťajú ako `uv run python ...` v rovnakom virtuálnom prostredí (Python 3.13 podľa lokálnej konfigurácie).
2. OpenAPI špecifikácia služby (napr. `specs/payments.yaml`).
3. Voľné adresáre: `workspace/catalog`, `artifacts/mocks`, `artifacts/tests`, `runs`.
4. Pre mock variant: dostupný port (štandardne `127.0.0.1:9101`).
5. Pre real-service variant: prístup na sieťovú adresu reálnych API a korektné autentifikačné údaje (ak sú potrebné – je možné ich preniesť cez environment variables alebo konfigurácie drivera).

## Predpríprava scenárov (API-First)

1. **contract-parser** – normalizácia špecifikácie a uloženie IR.
   ```powershell
   uv run python apps/contract-parser/contract_parser/main.py `
     --spec specs/payments.yaml `
     --output-dir workspace/catalog
   ```
   - Výsledok: `workspace/catalog/payments-api/1.0.0.json`

2. **mock-config-builder** – generuje `mock-config.yaml` (využije sa pri mock variante).
   ```powershell
   uv run python apps/mock-config-builder/mock_config_builder/main.py `
     --ir workspace/catalog/payments-api/1.0.0.json `
     --output-dir artifacts/mocks `
     --port rest=9101
   ```
   - Výsledok: `artifacts/mocks/payments-api/1-0-0/mock-config.yaml`

3. **test-scenario-builder** – pripravi smoke scenár a balík testov.
   ```powershell
   uv run python apps/test-scenario-builder/test_scenario_builder/main.py `
     --ir workspace/catalog/payments-api/1.0.0.json `
     --output-dir artifacts/tests `
     --scenario-prefix smoke
   ```
   - Výsledok: `artifacts/tests/payments-api/1.0.0/`

4. **Test implementation** – test bundle obsahuje testovací kód pripravený na spustenie.
   - Kľúčové premenné prostredia:
     - `CONSOLE_OUTPUT_FORMAT` – formát výstupu (auto, rich, plain, json)
     - `LOG_LEVEL` – úroň logovania (DEBUG, INFO, WARNING, ERROR)
   - Testované URL adresy sú automaticky generované z IR a mock konfigurácie.

## Variant A – Smoke test proti mock runtime

1. **Spustenie mock servera** (`mock-server`):
   ```powershell
   $mockJob = Start-Job -ScriptBlock {
     Set-Location 'C:/disk_d/workspace/AI_HUB/test-automation-demo'
     $env:CONSOLE_OUTPUT_FORMAT = "rich"
     uv run python apps/mock-server/mock_server/main.py `
       --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml
   }
   ```
   - Alternatíva na Linux/macOS: `uv run python ... &` a uloženie PID.
   - Logy zobrazíte cez `Receive-Job` alebo sledovaním stdout.

2. **Spustenie testov** (`test-executor`):
   ```powershell
   $env:CONSOLE_OUTPUT_FORMAT = "rich"
   uv run python apps/test-executor/test_executor/main.py `
     --bundle artifacts/tests/payments-api/1.0.0 `
     --output-dir runs
   ```
   - Výstup: `runs/<scenario_id>-<timestamp>/results.json` s počtami testov a zlyhaními.

3. **Ukončenie mock servera** – `Stop-Job`, `Receive-Job`, `Remove-Job` (resp. `kill <PID>` na Unix systémoch).

## Variant B – Smoke test proti reálnej službe

1. **Nepoužíva sa `mock-server`** – mock server nie je potrebný.
2. **Nastavte cieľovú URL**: Použite base URL reálneho API v testovacej konfigurácii alebo environment premennej.
   - V CI pipeline (Bash): `export SMOKE_RUNTIME_BASE_URL=https://real-api.example.com`
3. **Spustite `test-executor`** s rovnakým balíkom ako vyššie. Driver už smeruje na reálny endpoint a uplatní rovnaké asercie (`status == 200`, latencie atď.).
4. **Reset environmentu** – po dobehu odstráňte alebo zmeňte hodnotu premennej.

## Artefakty a monitoring

- Každý smoke beh generuje:
  - `runs/<scenario>/events.jsonl` – podrobný log krokov s časmi a chybami.
  - `runs/<scenario>/summary.json` – agregácia výsledkov (použiteľné pre dashboards, GitLab job artifacts).
  - `runs/<scenario>/results.junit.xml` – kompatibilné s CI test reportermi (GitLab, GitHub Actions, Azure DevOps).
- Mock runtime loguje každý request (`request_received`, `request_served`) spolu s metódou, cestou, latenciou a stavovým kódom – vhodné na koreláciu.

## Integrácia do CI

1. Inštalujte `uv` + Python 3.12+ v CI image.
2. Použite univerzálny pipeline skript:
   ```bash
   uv sync
   pwsh scripts/run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -OutputFormat plain
   ```
3. Artefakty `runs/*` pripojte k jobu (`artifacts: paths` v `.gitlab-ci.yml`).

## Konfigurovateľné parametre

| Komponent             | Parameter/Env Var                | Popis                                         |
|----------------------|----------------------------------|-----------------------------------------------|
| contract-parser      | `--spec`, `--output-dir`         | Špecifikácia a výstupný adresár               |
| mock-config-builder  | `--port rest=9101`               | Port pre mock server                          |
| test-scenario-builder| `--scenario-prefix`              | Prefix pre test scenáre                       |
| Všetky komponenty    | `CONSOLE_OUTPUT_FORMAT`          | Formát výstupu (auto, rich, plain, json)      |
| Všetky komponenty    | `LOG_LEVEL`                      | Úroveň logovania (DEBUG, INFO, WARNING, ERROR)|

## Zhrnutie

- Smoke testy sa spúšťajú v jednotnom prostredí spravovanom `uv`, ktoré zabezpečuje konzistentné závislosti naprieč OS (Windows, Linux, CI).
- Univerzálny pipeline skript automatizuje všetky kroky: parsing → mock config → test scenarios → mock server → test execution.
- Výsledné artefakty sú prenositeľné a vhodné pre automatizované CI/CD reporting.

