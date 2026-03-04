# C4 Model Gap Analysis

Updated: 2026-03-03

Comparison of three data sources:
- **PDF**: Service and Component Catalogue (Confluence export)
- **Model**: Current C4 LikeC4 model (.c4 files)
- **GitHub**: HMCTS org repos matching `cpp-*` / `cp-*` prefixes

Status key: **Resolved** = merged to main | **Outstanding** = not yet addressed | **Investigated** = repo examined, placement determined but not yet added to model

---

## 1. In PDF but not in Model

Services listed in the PDF catalogue that have no corresponding C4 component.

### Case and Material Ingestion

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| Prosecutors Civil | cpp.context.staging.prosecutors.civil | cpp-context-staging-prosecutors-civil | **Resolved** — added as new CPCI product |
| Prosecutors | cpp.context.staging.prosecutors | cpp-context-staging-prosecutors | **Resolved** — added to CPPI |
| Prosecution Document Queue | cpp.context.prosecution.documentqueue | cpp-context-prosecution-documentqueue | **Resolved** — added to document-ingestion-system |
| Bulk Scan | cpp.context.staging.bulkscan | cpp-context-staging-bulkscan | **Resolved** — added to document-ingestion-system |
| Material | cpp.context.material | cpp-context-material | **Resolved** — added to case-management-system |
| CPS MCC UI | cpp-ui-cps-mcc | *(not in GitHub)* | **Not in scope** — abandoned project for manual CPS case creation; never built |
| Bulk Scan UI | cpp-ui-bulkscan | cpp-ui-bulkscan | **Resolved** — added to document-ingestion-system |

### Case Administration

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| Directions Management | cpp.context.directions-management | *(not in GitHub)* | **Outstanding** — no repo found |
| Unified Search Query | cpp.context.unifiedsearch.query | cpp-context-unifiedsearch-query | **Resolved** — added to case-management-system |
| Defence UI | cpp-ui-defence | cpp-ui-defence | **Resolved** — added to advocate-portal |

### Court Hearings

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| Box Work Management | cpp.context.boxworkmanagement | cpp-context-boxworkmanagement | **Resolved** — added to case-management-system |
| Online Plea UI | cpp-ui-onlineplea | *(not in GitHub)* | **Resolved** — added to online-plea product |
| Results UI | cpp-ui-results | *(not in GitHub)* | **Resolved** — not a separate deployment; results functionality (enter-results, copy-results, share-results) is a built-in module within cpp-ui-hearing |
| External Services UI | cpp-ui-externalservices | cpp-ui-external-services | **Resolved** — added to hearing-system |

### OPAMI

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| MI System Data | cpp.context.mi.systemdata | cpp-context-mi-systemdata | **Resolved** — added to management-information-system |
| MI Report Data | cpp.context.mi.reportdata | cpp-context-mi-reportdata | **Resolved** — added to management-information-system |
| Audit2DLS | cpp.context.audit2dls | cpp-context-audit2dls | **Resolved** — added to audit-system |
| OPAMI UI | cpp-ui-opami | cpp-ui-opami | **Resolved** — added to management-information-system |

### Scheduling and Listing

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| Scheduling (decommissioning) | cpp.context.scheduling | cpp-scheduler | **Outstanding** — skipped (marked for decommissioning) |

---

## 2. In GitHub but not in Model

Repos in the HMCTS org (service/UI repos only, excluding infra/terraform/test/build) that have no corresponding C4 component.

### Service repos (`cpp-context-*`)

| Repo | Status |
|------|--------|
| cpp-context-archiving | **Resolved** — added to case-management-system |
| cpp-context-boxworkmanagement | **Resolved** — added to case-management-system |
| cpp-context-correspondence | **Resolved** — added to case-management-system |
| cpp-context-material | **Resolved** — added to case-management-system |
| cpp-context-material-id-mapper | **Resolved** — added to case-management-system |
| cpp-context-mi-reportdata | **Resolved** — added to management-information-system |
| cpp-context-mi-systemdata | **Resolved** — added to management-information-system |
| cpp-context-audit2dls | **Resolved** — added to audit-system |
| cpp-context-prosecution-documentqueue | **Resolved** — added to document-ingestion-system |
| cpp-context-resulting | **Resolved** — added to hearing-system |
| cpp-context-staging-bulkscan | **Resolved** — added to document-ingestion-system |
| cpp-context-staging-dcs | **Resolved** — added to case-management-system |
| cpp-context-staging-prosecutors | **Resolved** — added to CPPI |
| cpp-context-staging-prosecutors-civil | **Resolved** — added as new CPCI product |
| cpp-context-unifiedsearch-query | **Resolved** — added to case-management-system |

### UI repos (`cpp-ui-*`)

| Repo | Status |
|------|--------|
| cpp-ui-ai-intelligence | **Pending Discussion** — Angular 19 UI for AI-powered document intelligence search. Representation to be discussed with owning team |
| cpp-ui-audit-reports | **Resolved** — added to audit-system |
| cpp-ui-core | **Not in scope** — shared Angular library, not a deployable service |
| cpp-ui-defence | **Resolved** — added to advocate-portal |
| cpp-ui-external-services | **Resolved** — added to hearing-system |
| cpp-ui-home | **Resolved** — added to Common Platform User Interface shared component |
| cpp-ui-pdk2 | **Not in scope** — shared Angular library, not a deployable service |

### `cp-*` repos (services and libraries)

| Repo | Description | Technology | Status |
|------|-------------|------------|--------|
| cp-ai-rag-service | Document ingestion RAG service with 4 Azure Functions (doc metadata check, doc ingestion, answer retrieval, answer scoring) | Java 17+, Azure Functions | **Pending Discussion** — new AI/Intelligence capability. Representation to be discussed with owning team |
| cp-audit-filter | Spring Boot filter that publishes audit data to Artemis queues | Spring Boot, Java | **Not in scope** — reusable library (`java-library` plugin, published to Maven), not a deployable service. Removed from model |
| cp-audit-reports-service-v2 | Self-service audit reports backend | Java 21, Spring Boot, Gradle | **Resolved** — added to audit-system |
| cp-auth-rules-filter | Spring Boot filter for authorization rules on incoming requests | Spring Boot, Java, Gradle | **Not in scope** — reusable library, not a deployable service |
| cp-case-document-knowledge-service | AI-powered cited, auditable answers about case documents | Java 21, Spring Boot 4, PostgreSQL | **Pending Discussion** — new AI/Intelligence capability. Representation to be discussed with owning team |
| cp-client-mirror-gateway | Legacy mirror gateway for Crime Portal | Java 8, WildFly 10, PostgreSQL | **Not in scope** — part of Crime Portal, separate architecture |
| cp-court-list-publishing-service | Court list publishing service | Java 21, Spring Boot, Gradle | **Resolved** — added to scheduling-and-listing-system |
| cp-crime-portal | Large legacy monolith (crimeportal-web, gateway, mirrorgateway, cp-admin, contentprovider, notify, externalgateway, DbLayer, alfresco) | Java, Maven, multi-module | **Not in scope** — separate architecture, not part of Common Platform |
| cp-event-store | Event sourcing framework/library (aggregate-snapshot, event-buffer, event-sourcing modules) | Java, Maven | **Not in scope** — shared library, not a deployable service |
| cp-job-manager | Stateful multithreaded job/task execution engine (library) | Java 21, Gradle | **Not in scope** — shared library, not a deployable service |
| cp-result-definitions-browser | Developer/BA tool for result definitions and NOWs lookup with AI semantic search | Java 25, Spring Boot 3.5, React 18, PostgreSQL | **Not in scope** — developer/BA tool, not part of the production system |
| cp-task-manager | Distributed job scheduling and execution system with REST API | Java 21, Spring Boot, PostgreSQL | **Not in scope** — reusable library, not a deployable service |
| cp-vodafone-services | Vodafone-hosted services for Crime Portal (Gateway, Data Access, Quartz, Scheduler, Message/Doc Loaders, Oracle DB) | Java 7, WebLogic 10.3.6, Oracle DB | **Not in scope** — part of Crime Portal, separate architecture |

---

## 3. In Model but no Repo Link

Components in the C4 model that could not be matched to a GitHub repo.

| Component | Kind | Product | Subdomain | Status |
|-----------|------|---------|-----------|--------|
| subscriptions-ui | user-interface | case-management-system | Case Administration | **Resolved** — link to cpp-ui-subscriptions added |
| assignment-service | microservice | case-management-system | Case Administration | **Outstanding** — no repo found |
| work-management-ui | user-interface | work-management-system | Case Administration | **Resolved** — link to cpp-ui-work-management added |
| camunda | application | work-management-system | Case Administration | **Resolved** — third-party app, no repo expected |
| camunda-optimize | application | work-management-system | Case Administration | **Resolved** — third-party app, no repo expected |
| error-queue-ui | user-interface | spi | Case Ingestion | **Outstanding** — no repo found |
| case-filter | functions | spi | Case Ingestion | **Resolved** — link to cpp-context-staging-prosecutors-spi added (Azure Functions module in SPI repo). Fixed technology from TypeScript/Node.js to Java |
| notepad-parsing-ui | user-interface | hearing-system | Court Hearings | **Resolved** — not a separate deployment; notepad-parser.service.ts is a built-in service within cpp-ui-hearing's results module |
| dlrm-integration-functions | functions | legacy-case-migration-system | DLRM | **Resolved** — link to cpp-context-stagingdlrm added (shares repo with staging-dlrm service) |
| idam-events-consumer | microservice | users-and-groups-system | Shared Components | **Resolved** — link to cpp-context-idam-events-consumer added |
| pnld-offences | microservice | reference-data-system | Shared Components | **Resolved** — already linked to cpp-context-staging-pnld-offences in model (repo confirmed to exist) |
| manage-permissions-ui | user-interface | users-and-groups-system | Shared Components | **Resolved** — link to cpp-ui-managepermissions added |
| listing-ui | user-interface | scheduling-and-listing-system | Scheduling and Listing | **Resolved** — link to cpp-ui-listing added |
| court-scheduler-ui | user-interface | scheduling-and-listing-system | Scheduling and Listing | **Resolved** — link to cpp-ui-courtscheduler added |

---

## 4. Products with no Components (Shell Products)

| Product | Subdomain | Status |
|---------|-----------|--------|
| audit-system | OPAMI | **Resolved** — audit2dls service added |
| management-information-system | OPAMI | **Resolved** — MI system-data and report-data services added |
| online-plea | Court Hearings | **Resolved** — online-plea-ui added |
| cppi | Case Ingestion | **Resolved** — staging-prosecutors service added |

---

## 5. Subdomain Discrepancies

| Component | PDF Domain | Model Subdomain | Status |
|-----------|-----------|-----------------|--------|
| prosecution-case-file-service | Case and Material Ingestion | Case Administration | **Resolved** — keeping in Case Administration |
| Prosecution Casefile UI | Case and Material Ingestion | Case Administration | **Resolved** — same as above |

---

## 6. New Capabilities Discovered (not in PDF or Model)

Repos that represent entirely new capabilities not previously tracked.

### AI / Intelligence (3 repos forming a new product)

| Repo | Description | Technology |
|------|-------------|------------|
| cp-ai-rag-service | Document ingestion RAG pipeline (4 Azure Functions) | Java 17+, Azure Functions, Azure AI |
| cp-case-document-knowledge-service | AI-powered case document Q&A service | Java 21, Spring Boot 4, PostgreSQL |
| cpp-ui-ai-intelligence | Document intelligence search UI | Angular 19, TypeScript |

These three repos form a cohesive AI/Intelligence capability. Representation to be discussed with owning team.

### Crime Portal / Legacy (not in scope)

cp-crime-portal, cp-client-mirror-gateway, and cp-vodafone-services are part of the Crime Portal system which has a separate architecture and is not part of Common Platform.

### Shared Platform Libraries (not deployable services)

| Repo | Description | Technology |
|------|-------------|------------|
| cp-audit-filter | Spring Boot servlet filter for request/response auditing via Artemis JMS | Java 21, Gradle |
| cp-event-store | Event sourcing framework (aggregate-snapshot, event-buffer) | Java, Maven |
| cp-job-manager | Job/task execution engine library | Java 21, Gradle |
| cpp-ui-core | Shared Angular component framework | Angular, TypeScript |
| cpp-ui-pdk2 | Platform Development Kit v2 (design system) | Angular, TypeScript |

These are shared libraries/frameworks consumed as dependencies. May not need C4 modelling.

---

## Summary

| Category | Resolved | Pending Discussion | Outstanding | Not in scope | Total |
|----------|----------|--------------------|-------------|--------------|-------|
| Repo links added (Phase 2) | 42 | — | — | — | 42 |
| PDF items not in model (Section 1) | 16 | 0 | 2 | 1 | 19 |
| GitHub repos not in model (Section 2) | 21 | 3 | 0 | 11 | 35 |
| Model components without repo link (Section 3) | 12 | 0 | 2 | — | 14 |
| Shell products (Section 4) | 4 | 0 | 0 | — | 4 |
| New capabilities (Section 6) | 0 | 3 | — | 5 | 8 |
