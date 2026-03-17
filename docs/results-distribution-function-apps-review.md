# Results Distribution System — Function Apps Review

All 8 function apps live in a single monorepo: [hmcts/cpp-context-azure-legalaidagency](https://github.com/hmcts/cpp-context-azure-legalaidagency)

## Common Findings (apply to all 8)

- **Language is JavaScript, not TypeScript** — no `.ts` files, no `tsconfig.json`, no TypeScript dependency in the repo
- **Node.js version is 20.9.0** — pinned in `azure-functions/pom.xml` via `frontend-maven-plugin`
- **All use Azure Durable Functions** — not plain Azure Functions
- **All have a Redis cache-miss fallback** to the Results Service query API — this relationship is missing from every function app in the current model
- **VEP (Victim Enforcement Portal)** is referenced by LAA and Probation functions but doesn't exist as an external system in the model yet

## Complexity Ranking (simplest → most complex)

| Rank | Function App | Directory | Outbound Relationships | Status |
|------|-------------|-----------|----------------------|--------|
| 1 | Court Register | `courtregister-azure-functions/` | 4 (Redis, Results Service, Reference Data, Progression) | **Done** |
| 2 | Informant Register | `informantregister-azure-functions/` | 4 (Redis, Results Service, Reference Data, Results Service write) | Todo |
| 3 | Prison Court Record | `prisoncourtregister-azure-functions/` | 4 (Redis, Results Service, Reference Data, Progression) | Todo |
| 4 | Probation | `probation-azure-functions/` | 4 (Redis, Results Service, Users & Groups, HMPPS, VEP) | Todo |
| 5 | Court Order | `courtorders-azure-functions/` | 3 services but complex business logic (Redis, Results Service, Court Orders Service with read+write) | Todo |
| 6 | LAA | `legalaidagency-azure-functions/` | 7 (Redis, Results Service, Unified Search, Progression, Hearing Service, LAA, Blob Storage + VEP) | Todo |
| 7 | NOWs | `nows-azure-functions/` | 8+ (12-step orchestration with extensive Reference Data lookups, Staging Enforcement, feature toggles) | Todo |
| 8 | SJP | `azure-functions/durable-functions/` | 7 (mega-orchestrator: Results Service, SJP Service, Staging Enforcement, Court Orders Service, Reference Data, Results Service write) | Todo |

## Per-Function App Details

### 1. Court Register Result Functions (DONE)

- **What it does**: Generates youth court register entries from hearing results for aggregation into a daily per-court PDF distributed to Youth Offending Teams
- **Key finding**: Only processes youth defendants — adults are filtered out in `OutboundCourtRegister/index.js`
- **Document output**: Progression aggregates submissions per court centre per day into a single PDF (Docmosis template `OEE_Layout5`) emailed to YOTs via GOV.UK Notify
- **Relationships updated**: Redis, Results Service (cache fallback), Reference Data (NOW subscriptions), Progression Service

### 2. Informant Register Result Functions

- **What it does**: Generates informant registers grouped by prosecution authority from hearing results
- **Missing relationships**: Results Service (cache fallback + command write), Reference Data (subscription metadata)
- **Key detail**: Submits informant registers to Results Command API (not Progression), grouped by prosecution authority. Output is a CSV (`InformantRegister_{prosecutionAuthorityCode}_{date}.csv`)
- **Recipients**: Prosecution authorities, matched via NOW subscription rules

### 3. Prison Court Record Result Functions

- **What it does**: Processes hearing results for defendants in custody and sends prison court register data to Progression
- **Missing relationships**: Results Service (cache fallback), Reference Data (subscriptions + prisons/custody suites)
- **Key detail**: Unlike the Youth Court Register, Prison Court Registers are NOT aggregated — each produces a separate PDF per defendant/hearing (`PrisonCourtRegister_{timestamp}.pdf`)
- **Current summary is misleading**: Says "notifies prison services" but it actually sends to Progression Service, which handles downstream distribution

### 4. Probation Result Functions

- **What it does**: Filters and distributes hearing results to HMPPS (probation) AND VEP (police forces)
- **Missing relationships**: Results Service (cache fallback), Users & Groups (youth filter feature toggle), VEP (external system)
- **Key detail**: Dual output — sends to both HMPPS and VEP. Filters out SJP/box hearings, youth defendants (toggle), LAA references, judiciary info
- **Requires**: VEP to be added as an external system in `model-external-systems.c4`

### 5. Court Order Result Functions

- **What it does**: Creates, updates, removes and resets court orders based on hearing results
- **Missing relationships**: Results Service (cache fallback). Court Orders Service relationship needs description (reads existing orders + writes create/update/remove/reset)
- **Key detail**: Complex business logic — queries existing court orders to determine create vs update vs remove. Skips group proceedings. Handles OREV (Order Revocation), variations, breaches, amended results

### 6. LAA Result Functions

- **What it does**: Filters and distributes hearing results to LAA, provides on-demand HTTP query APIs for LAA, and distributes police-case results to VEP
- **Missing relationships**: Results Service (cache fallback), Unified Search Query Service (LAA reference checks), Progression Service (application LAA references), Hearing Service (event logs), Azure Blob Storage (subscriber config)
- **Key detail**: Bidirectional — LAA calls INTO the function's HTTP endpoints. Also includes VEP publishing for police cases. Three flows: event-driven publishing, HTTP result query, HTTP event log query
- **Requires**: VEP external system

### 7. NOWs Result Functions

- **What it does**: Processes hearing results to generate NOWs documents, NCES tracking records, and financial enforcement requests
- **Missing relationships**: Results Service (cache fallback + NCES tracking writes), Reference Data (NOW metadata, subscriptions, org units, major creditors, enforcement areas), Users & Groups (feature permissions), Staging Enforcement Service (financial enforcement), Progression Service (legacy NOW path), Azure Blob Storage (intermediate payloads)
- **Key detail**: 12-step orchestration pipeline. Most complex business logic of all function apps. Feature toggle switches between Hearing NOWs Service and Progression Service for NOW document generation

### 8. SJP Result Functions

- **What it does**: Distributes Single Justice Procedure hearing results to 5 downstream services
- **Missing relationships**: Results Service (cache fallback + NCES tracking + informant register writes), SJP Service (financial imposition correlation IDs), Staging Enforcement Service (compliance enforcement), Application Court Orders Service (create/update/remove), Reference Data (subscription metadata)
- **Key detail**: Mega-orchestrator that duplicates logic from Court Order, Informant Register, and NOWs pipelines but for SJP cases specifically. Current model only had 1 relationship (Redis) — actually has 7+
