# API Smoke Test Platform – Lokálne Spustenie

## 1. Ciele a Kontext
- **Primárny cieľ**: automaticky generovať a spúšťať smoke testy a mock servery pre REST API iba pomocou Python CLI nástrojov.
- **Rozsah**: lokálne spúšťanie bez vzdialených služieb; všetky artefakty zostávajú v súborovom systéme.
- **Podporované OS**: Windows (PowerShell), Linux (Bash) a macOS.

## 1.1 Referenčné špecifikácie a univerzálny skript
- V repozitári sú pripravené tri špecifikácie (`specs/payments.yaml`, `specs/commerce.yaml`, `specs/flights.yaml`) spolu s hotovými výstupmi v `artifacts/` a `runs/`.
- Skript [`scripts/run-smoke-pipeline.ps1`](../scripts/README.md) je univerzálny pipeline pre ľubovoľnú OpenAPI špecifikáciu:
  ```powershell
  .\scripts\run-smoke-pipeline.ps1 -SpecPath "specs/payments.yaml"
  ```
- Výstupom skriptu je nový priečinok `runs/<service>-<version>-<timestamp>/` s výsledkami testov.

## 2. Architektonický Prehľad
- **Monorepo**: Čistý Python workspace spravovaný pomocou `uv` package managera
- **Prostredie**: `uv run python ...` vytvára deterministické virtuálne prostredia
- **Úložiská**:
  - `specs/`: vstupné OpenAPI špecifikácie
  - `workspace/catalog/`: IR JSON + JSON search index
  - `artifacts/tests/` + `artifacts/mocks/`: generované test scenáre a mock konfigurácie
  - `runs/<scenario>-<timestamp>/`: výsledky testov
- **Závislosti**: Python 3.12+, Typer, Pydantic, PyYAML, structlog, Rich

## 3. Komponenty

| Komponent | Úloha | Príklad príkazu |
| --- | --- | --- |
| `contract-parser` | Validuje OpenAPI, vytvorí IR JSON a search index | `uv run python apps/contract-parser/contract_parser/main.py --spec specs/payments.yaml --output-dir workspace/catalog` |
| `test-scenario-builder` | Generuje test scenáre z IR | `uv run python apps/test-scenario-builder/test_scenario_builder/main.py --ir workspace/catalog/payments-api/1.0.0.json --output-dir artifacts/tests` |
| `mock-config-builder` | Generuje mock konfigurácie z IR | `uv run python apps/mock-config-builder/mock_config_builder/main.py --ir workspace/catalog/payments-api/1.0.0.json --output-dir artifacts/mocks --port rest=9101` |
| `mock-server` | FastAPI mock server runtime | `uv run python apps/mock-server/mock_server/main.py --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml` |
| `test-executor` | Spúšťa smoke testy s Rich UI | `uv run python apps/test-executor/test_executor/main.py --bundle artifacts/tests/payments-api/1.0.0 --output-dir runs` |

## 4. Workflow

### Univerzálny Pipeline (Odporúčaný)
```powershell
# Kompletný pipeline v jednom príkaze
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath "specs/payments.yaml" `
    -MockPort 9101 `
    -OutputFormat rich
```

### Manuálne Kroky

**1. Parsovanie kontraktu**
```powershell
uv run python apps/contract-parser/contract_parser/main.py `
    --spec specs/payments.yaml `
    --output-dir workspace/catalog
```

**2. Generovanie mock konfigurácie**
```powershell
uv run python apps/mock-config-builder/mock_config_builder/main.py `
    --ir workspace/catalog/payments-api/1.0.0.json `
    --output-dir artifacts/mocks `
    --port rest=9101
```

**3. Generovanie test scenárov**
```powershell
uv run python apps/test-scenario-builder/test_scenario_builder/main.py `
    --ir workspace/catalog/payments-api/1.0.0.json `
    --output-dir artifacts/tests `
    --scenario-prefix smoke
```

**4. Spustenie mock servera**
```powershell
$env:CONSOLE_OUTPUT_FORMAT = "rich"
$mockJob = Start-Job -ScriptBlock {
    Set-Location "C:\disk_d\workspace\AI_HUB\test-automation-demo"
    uv run python apps/mock-server/mock_server/main.py `
        --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml
}
```

**5. Spustenie smoke testov**
```powershell
$env:CONSOLE_OUTPUT_FORMAT = "rich"
uv run python apps/test-executor/test_executor/main.py `
    --bundle artifacts/tests/payments-api/1.0.0 `
    --output-dir runs
```

**6. Cleanup**
```powershell
Stop-Job $mockJob
Receive-Job $mockJob
Remove-Job $mockJob
```

## 5. Konfigurácia

### Environment Premenné

**CONSOLE_OUTPUT_FORMAT** - Kontrola výstupu konzoly
- `rich` - Krásne terminal UI (default pre interaktívne prostredie)
- `plain` - Jednoduchý text (CI/CD friendly)
- `json` - Štruktúrované JSON logy
- `auto` - Automatická detekcia

**LOG_LEVEL** - Úroveň logovania
- `DEBUG` - Všetky správy vrátane debug info
- `INFO` - Štandardné operačné správy (default)
- `WARNING` - Len varovania a chyby
- `ERROR` - Len chyby

### Technológie

| Technológia | Verzia | Účel |
| --- | --- | --- |
| Python | 3.12+ | Runtime environment |
| uv | latest | Package manager (10-100× rýchlejší ako pip) |
| Ruff | 0.9.0+ | Linting a formátovanie (10-100× rýchlejší ako Black) |
| Typer | 0.15.0+ | CLI framework |
| Pydantic | 2.10.0+ | Data validácia |
| Rich | 13.9.0+ | Terminal UI |
| structlog | 24.4.0+ | Structured logging |

## 6. Výstupy a Artefakty

### Test Results
```
runs/
  smoke-payments-1-0-0-20260112-122906/
    results.json          # Detailné výsledky testov
    summary.txt           # Textové zhrnutie
```

### Mock Konfigurácie
```
artifacts/mocks/
  payments-api/
    1-0-0/
      mock-config.yaml    # Mock server konfigurácia
```

### Test Scenáre
```
artifacts/tests/
  payments-api/
    1.0.0/
      manifest.json       # Test suite metadata
      test_*.json         # Jednotlivé test cases
```

## 7. Lokálne Spúšťanie – Odporúčané Kroky

1. **Inštalácia uv**
   ```powershell
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Linux/macOS
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Synchronizácia závislostí**
   ```powershell
   uv sync
   ```

3. **Spustenie univerzálneho pipeline**
   ```powershell
   .\scripts\run-smoke-pipeline.ps1 -SpecPath "specs/payments.yaml"
   ```

4. **Overenie výsledkov**
   ```powershell
   # Pozrite si výsledky v runs/ directory
   Get-ChildItem runs -Directory | Sort-Object CreationTime -Descending | Select-Object -First 1
   ```

## 8. Kvalita a Validácia

### Linting a Formátovanie
```powershell
# Format kódu
ruff format .

# Lint kódu
ruff check .

# Fix automaticky opraviteľné problémy
ruff check --fix .
```

### Type Checking
Pydantic modely poskytujú runtime type checking.

## 9. CI/CD Integrácia

### GitHub Actions
```yaml
- name: Run Smoke Tests
  env:
    CONSOLE_OUTPUT_FORMAT: plain
  run: |
    pwsh scripts/run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
```

### GitLab CI
```yaml
script:
  - export CONSOLE_OUTPUT_FORMAT=plain
  - pwsh scripts/run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
```

## 10. Ďalšie Kroky

1. Prečítajte si [scripts/README.md](../scripts/README.md) pre detailnú dokumentáciu univerzálneho pipeline
2. Pozrite si [README.md](../README.md) pre prehľad celého projektu
3. Prečítajte si dokumentáciu jednotlivých komponentov:
   - [contract-parser](../apps/contract-parser/README.md)
   - [mock-config-builder](../apps/mock-config-builder/README.md)
   - [test-scenario-builder](../apps/test-scenario-builder/README.md)
   - [mock-server](../apps/mock-server/README.md)
   - [test-executor](../apps/test-executor/README.md)


## 3. Projekty a Zdieľané Knižnice
| Typ | Názov | Úloha |
| --- | --- | --- |
| CLI | `cli-contract-intake` | Validuje OpenAPI/WSDL/Proto, normalizuje ich do IR JSON a FAISS indexu. |
| CLI | `cli-test-generator` | Používa IR + prompt knižnicu na generovanie scenárov (YAML + payloady). |
| CLI | `cli-mock-generator` | Kompiluje editovateľné mock konfigurácie a handler kód pre REST/SOAP/gRPC. |
| CLI | `cli-smoke-runtime` | Jednotný runtime spúšťajúci scenáre a produkujúci výstupy. |
| CLI | `cli-report` | Filtrovanie a agregácia `runs/*/summary.json` podľa metadát. |
| Runtime | `runtime-mock-rest/soap/grpc` | Samostatné Typer CLIs spúšťajúce mock servery z konfigov. |
| Lib | `libs/contract_ir` | Pydantic modely IR, diff nástroje, semantic hashing. |
| Lib | `libs/ai_pipeline` | RAG helpery, adaptery pre AI poskytovateľov, guardrails. |
| Lib | `libs/runtime_config` | Schémy scenárov/mokov, loader s `ruamel.yaml`. |
| Lib | `libs/logging` | `structlog` konfigurácia a korelačné ID. |
| Lib | `libs/reporting` | Analytické helpery, JUnit/JSON schema definície. |

### 3.1 Hatch skripty a mapovanie CLI

| Skript (`hatch run …`) | Vnútorný príkaz | Použitie |
| --- | --- | --- |
| `intake` | `python apps/cli-contract-intake/cli_contract_intake/main.py` | Normalizácia špecifikácie do IR/FAISS. Odovzdajte `--spec`, `--output-dir`, `--service-name`. |
| `test_generate` | `python apps/cli-test-generator/cli_test_generator/main.py` | Generovanie scenárov/payloadov z IR (parametre: `--ir`, `--output-dir`, `--scenario-prefix`, `--tag`). |
| `mock_generate` | `python apps/cli-mock-generator/cli_mock_generator/main.py` | Príprava mock konfigurácií (napr. `--format yaml --port rest=9101`). |
| `mock_runtime` | `python apps/cli-mock-runtime/cli_mock_runtime/main.py` | Spustenie mock servera podľa vytvoreného YAML. |
| `smoke` | `python apps/cli-smoke-runtime/cli_smoke_runtime/main.py` | Spustenie smoke bundle (`hatch run smoke -- run --bundle ... --output-dir runs`). |
| `lint` | `ruff apps libs` | Rýchly lint všetkých CLI + knižníc. |
| `type_check` | `mypy apps/…` | Striktná statická analýza. |
| `tests` | `pytest` | Behy jednotkových a integračných testov. |
| `format` | `black apps libs` | Formátovanie zdrojového kódu. |

## 4. Toky Práce
1. **Intake**: `hatch run intake -- --spec specs/payments.yaml --output-dir workspace/catalog --service-name Payments` uloží IR do `workspace/catalog/payments/v2.json` a aktualizuje index. V distribuovanom režime je ekvivalent `python -m cli_contract_intake.main --spec ...` alebo nainštalovaný `cli-contract-intake` wheel.
2. **Generovanie scenárov**: `cli-test-generator` načíta IR + prompt, vyberie AI poskytovateľa (`config/ai-providers.yaml`), vytvorí `artifacts/tests/<protocol>/<service>/<version>/` balík.
3. **Generovanie mokov**: `cli-mock-generator` pripraví `artifacts/mocks/...` s YAML konfiguráciou a handler kódom.
4. **Lokálne mocky**: operátor spustí napr. `hatch run mock_runtime -- --config artifacts/mocks/payments/1-0-0/mock-config.yaml --log-format console` (porty definované v konfigurácii). Runtime od januára 2026 nativne obsluhuje aj `HEAD`/`OPTIONS`, takže generované scenáre môžu pokrývať health-check a CORS handshake bez ručných handlerov.
5. **Smoke beh**: `hatch run smoke -- run --bundle artifacts/tests/payments/1.0.0 --project PAY --branch release/1.3 --tags smoke,rest` (alebo `python -m cli_smoke_runtime.main run ...` po `pip install`). Runtime načíta scenár, aplikuje CLI metadáta, spustí protokolové adaptéry (REST/httpx, SOAP/zeep, gRPC/grpcio) a uloží výstupy do `runs/<timestamp>/<scenario-id>/`.
6. **Reportovanie**: `cli-report filter --runs runs --project PAY --since 2026-01-01 --format markdown > reports/payments.md`.

## 5. Konfigurácia AI a Prompts
- `config/ai-providers.yaml` definuje aliasy (napr. `openai-prod`, `vertex-payments`, `local-llama`) s `type`, `base_url`, `model_id`, spôsobom autentifikácie (env vars, token file) a limitmi.
- Prompt knižnica (`prompts/<workflow>/<locale>.yaml`) obsahuje templaty s makrami (`${OPERATION_NAME}`) a metadata (locale, tón). `cli-test-generator prompts ls|edit|new` spravuje verzie.
- Audit trail (poskytovateľ, model, prompt verzia, parametre) sa zapisuje do `runs/<timestamp>/summary.json` pre reprodukovateľnosť.

## 6. Konfigurácia Scenárov a Mokov
- **Scenár** (`scenario.yaml`): obsahuje `protocol`, `steps`, `assertions`, povinné metadáta (`test_id`, `test_name`, `project`, `branch`, `test_type`, `tags`) a voliteľný `custom` blok.
- **Metadata overrides**: CLI parametre majú vyššiu prioritu, zlúčenie prebieha cez hlboký merge.
- **Moky**: YAML definuje `routes`/`operations`, odpovede, latency injection a voliteľný `instances` blok (port, TLS, dataset). Runtimes sledujú súbory pre manuálne zmeny (reload cez CLI parameter).
- **Env overrides**: `SMOKE_RUNTIME_BASE_URL`, `SMOKE_RUNTIME_TIMEOUT` a `SMOKE_RUNTIME_LOG_LEVEL` sú dostupné pre každý driver/spúšťanie a používajú sa aj v orchestrasčnom skripte.

## 7. Logovanie a Artefakty
- `structlog` formátuje logy do JSON/console; korelačné ID párujú smoke kroky s mock odpoveďami. Bez centralizovaného monitoringu ostávajú logy v `runs/<ts>/<scenario-id>/<module>.log`.
- `events.jsonl` zachytáva každý krok (timestamp, protokol, status, latencia, metadáta).
- `summary.json` sumarizuje výsledok a obsahuje audit trail AI a konfigurácie.
- Voliteľný `results.junit.xml` umožní import do testovacích nástrojov alebo neskôr do CI.

## 8. Lokálne Spúšťanie – Odporúčané Kroky
Najrýchlejšie overenie je `pwsh ./scripts/payments-smoke-e2e.ps1` (prípadne s parametrami pre `commerce`/`flights`). Skript pripraví artefakty, spustí mock runtime a uloží run summary, takže okamžite viete, či lokálne prostredie funguje end-to-end.

1. `pipx install hatch` (alebo `pip install hatch`) a následne `hatch env create`, aby sa vytvorilo virtuálne prostredie s projektom aj dev závislosťami. Alternatívne je možné použiť `uv sync` alebo manuálny `python -m venv` podľa firemných politík.
2. `hatch run lint`, `hatch run type_check` a `hatch run tests` pre základnú kontrolu kvality.
3. `hatch run intake -- --spec specs/... --output-dir workspace/catalog --service-name <Service>` pre každý kontrakt (alebo zabalene `python -m cli_contract_intake.main`).
4. `hatch run test_generate -- --ir workspace/catalog/<service>/<version>.json --output-dir artifacts/tests --scenario-prefix smoke --tag <tag>`.
5. `hatch run mock_generate -- --ir workspace/catalog/<service>/<version>.json --output-dir artifacts/mocks --format yaml --port rest=9101`.
6. `hatch run mock_runtime -- --config artifacts/mocks/<service>/<version>/mock-config.yaml --log-format console` (ponechajte bežať na pozadí alebo použite `Start-Job`).
7. `hatch run smoke -- run --bundle artifacts/tests/<service>/<version> --output-dir runs --project <code> --tags smoke` pre jednotlivé alebo dávkové scenáre.
8. `cli-report filter --runs runs --format markdown` (po `pip install cli-report` wheeli) alebo pripravte vlastný hatch skript pre reporting.

## 9. Kvalita a Overenie
- Hatch skripty `lint`, `type_check`, `tests` a `format` zabalia `ruff`, `black`, `mypy --strict`, `pytest`. Vývojár spúšťa `hatch run lint type_check tests` pred commitom (alebo podľa potreby samostatne).
- Konfiguračné validátory (`cli-test-generator validate`, `cli-mock-generator validate`) kontrolujú manuálne upravené YAML pred spustením.
- Porovnanie IR snapshotov pomocou `libs/contract_ir` (semantic hash) zabezpečuje, že regenerácia je deterministická.

## 10. Ďalšie Kroky
1. Dokončiť implementáciu všetkých CLI podľa tejto architektúry a zdokumentovať konkrétne Hatch skripty (prípadne `python -m` príkazy pre distribúciu).
2. Pridať README sekciu „Lokálne scenáre“ s ukážkovými príkazmi pre Windows PowerShell, Bash a macOS.
3. Pripraviť vzorové `specs/` a `artifacts/` pre rýchly onboarding (napr. `payments`, `orders`).
4. Rozšíriť `cli-report` o šablóny Markdown/HTML pre publikovanie výsledkov.
5. Až po stabilizácii lokálneho toku doplniť CI templates (GitLab/GitHub/Jenkins), ktoré znovu použijú tie isté príkazy.
