# Results Distribution System — Function Apps Review

All 8 function apps live in a single monorepo: [hmcts/cpp-context-azure-legalaidagency](https://github.com/hmcts/cpp-context-azure-legalaidagency)

## Common Findings (apply to all 8)

- **Language is JavaScript, not TypeScript** — no `.ts` files, no `tsconfig.json`, no TypeScript dependency in the repo
- **Node.js version is 20.9.0** — pinned in `azure-functions/pom.xml` via `frontend-maven-plugin`
- **All use Azure Durable Functions** — not plain Azure Functions
- **All have a Redis cache-miss fallback** to the Results Service query API — this relationship is missing from every function app in the current model
- **VEP (Video Enabled Policing)** is referenced by LAA and Probation functions but doesn't exist as an external system in the model yet

## Complexity Ranking (simplest → most complex)

| Rank | Function App | Directory | Outbound Relationships | Status |
|------|-------------|-----------|----------------------|--------|
| 1 | Court Register | `courtregister-azure-functions/` | 4 (Redis, Results Service, Reference Data, Progression) | **Done** |
| 2 | Informant Register | `informantregister-azure-functions/` | 4 (Redis, Results Service, Reference Data, Results Service write) | **Done** |
| 3 | Prison Court Record | `prisoncourtregister-azure-functions/` | 4 (Redis, Results Service, Reference Data, Progression) | **Done** |
| 4 | Probation | `probation-azure-functions/` | 5 (Redis, Results Service, Users & Groups, HMPPS, VEP) | **Done** |
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

### 2. Informant Register Result Functions (DONE)

- **What it does**: Assembles informant register data grouped by prosecution authority from hearing results, matches recipients via NOW subscription rules from Reference Data, and submits to the Results Service for CSV generation and email distribution
- **Relationships updated**: Redis (cache read), Results Service (cache fallback read + informant register write), Reference Data (NOW subscription metadata)
- **Key detail**: Function app determines recipients via subscription matching; Results Service batches by prosecution authority + date, generates CSV (InformantRegister_{authorityCode}_{date}.csv), stores in File Service, and emails to recipients via GOV.UK Notify. For group cases, Results Service looks up member defendants from Progression Service.
- **Also updated**: Results Service — added summary, description (documenting result storage/caching, result distribution, and informant register lifecycle), and relationships to Progression Service and Notification Notify

### 3. Prison Court Record Result Functions (DONE)

- **What it does**: Generates per-defendant prison court registers from hearing results and submits to Progression for document generation and distribution to prisons and custody suites
- **Relationships updated**: Redis (cache read), Results Service (cache fallback), Reference Data (NOW subscription rules + prisons/custody suites), Progression Service (per-defendant submission)
- **Key details**:
  - 5-step orchestrator pipeline: HearingResultedCacheQuery → SetPrisonCourtRegister → PrisonCourtRegisterSubscriptions → OutboundPrisonCourtRegister → ProcessOutboundPrisonCourtRegister
  - Group proceedings are excluded entirely
  - Unlike Court Register (youth only, aggregated per court/day), Prison Court Register processes all defendants matching subscription rules and produces one register per defendant
  - Subscription matching uses `isPrisonCourtRegisterSubscription` flag and checks vocabulary rules: custody status, attendance type, defendant type (youth/adult), court type (English/Welsh), custodial results
  - Three recipient sources: (1) defendant's custodial establishment cross-referenced with Reference Data prisons/custody suites, (2) judicial result prompts containing prison organisation details, (3) static subscription configuration
  - Reference Data is called twice: once for NOW subscriptions, once for prisons and custody suites
  - Result filtering: includes results where `publishedForNows !== true` (differs from Court Register which also requires `isAvailableForCourtExtract`)
- **Also updated**: Progression Service — added prison court register documentation to its description
- **Fixed**: technology (Azure Functions → Azure Durable Functions), language (TypeScript → JavaScript), summary rewritten to accurately describe the function

### 4. Probation Result Functions (DONE)

- **What it does**: Filters and distributes hearing results to HMPPS (probation) AND VEP (police forces)
- **Relationships updated**: Redis (cache read), Results Service (cache fallback), Users & Groups (youth filter feature toggle), HMPPS (filtered hearing results), VEP (police-case results)
- **Key details**:
  - 5-step orchestrator pipeline: HearingResultedCacheQuery → ProbationHearingResultedFilter → HMPPSExternalPublisher → VEPHearingResultedFilter → VEPHearingResultedPublishHandler
  - VEP steps only run when police-originated prosecution cases exist in the hearing
  - Probation filter: excludes SJP/box/virtual box hearings, optionally removes youth defendants (controlled by feature toggle in Users & Groups), strips LAA references, judiciary, associated persons, and delegated powers
  - VEP filter: excludes SJP/box/virtual box hearings, strips LAA references, keeps only police-originated prosecution cases
  - Both publishers use mTLS client certificates for external HTTPS calls via Azure API Management
- **Also updated**: Added VEP (Video Enabled Policing) as a new external system in `model-external-systems.c4`
- **Fixed**: technology (Azure Functions → Azure Durable Functions), language (TypeScript → JavaScript), summary rewritten for dual HMPPS/VEP output

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
