# C4 Model Gap Analysis

Generated: 2026-02-19

Comparison of three data sources:
- **PDF**: Service and Component Catalogue (Confluence export)
- **Model**: Current C4 LikeC4 model (.c4 files)
- **GitHub**: HMCTS org repos matching `cpp-*` / `cp-*` prefixes

Status key: **Resolved** = merged to main | **PR** = in PR #25 | **Outstanding** = not yet addressed

---

## 1. In PDF but not in Model

Services listed in the PDF catalogue that have no corresponding C4 component.

### Case and Material Ingestion

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| Prosecutors Civil | cpp.context.staging.prosecutors.civil | cpp-context-staging-prosecutors-civil | **PR** — added as new CPCI product |
| Prosecutors | cpp.context.staging.prosecutors | cpp-context-staging-prosecutors | **Outstanding** — needs investigation |
| Prosecution Document Queue | cpp.context.prosecution.documentqueue | cpp-context-prosecution-documentqueue | **Outstanding** |
| Bulk Scan | cpp.context.staging.bulkscan | cpp-context-staging-bulkscan | **Outstanding** |
| Material | cpp.context.material | cpp-context-material | **PR** — added to case-management-system |
| CPS MCC UI | cpp-ui-cps-mcc | *(not in GitHub)* | **Outstanding** — no repo found |
| Bulk Scan UI | cpp-ui-bulkscan | *(not in GitHub)* | **Outstanding** — no repo found |

### Case Administration

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| Directions Management | cpp.context.directions-management | *(not in GitHub)* | **Outstanding** — no repo found |
| Unified Search Query | cpp.context.unifiedsearch.query | cpp-context-unifiedsearch-query | **PR** — added to case-management-system |
| Defence UI | cpp-ui-defence | cpp-ui-defence | **PR** — added to defence-portal |

### Court Hearings

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| Box Work Management | cpp.context.boxworkmanagement | cpp-context-boxworkmanagement | **PR** — added to case-management-system |
| Online Plea UI | cpp-ui-onlineplea | *(not in GitHub)* | **PR** — added to online-plea product |
| Results UI | cpp-ui-results | *(not in GitHub)* | **Outstanding** — no repo found |
| External Services UI | cpp-ui-externalservices | cpp-ui-external-services | **Outstanding** — placement TBD |

### OPAMI

| PDF Name | PDF Repo ID | GitHub Repo | Status |
|----------|-------------|-------------|--------|
| MI System Data | cpp.context.mi.systemdata | cpp-context-mi-systemdata | **PR** — added to management-information-system |
| MI Report Data | cpp.context.mi.reportdata | cpp-context-mi-reportdata | **PR** — added to management-information-system |
| Audit2DLS | cpp.context.audit2dls | cpp-context-audit2dls | **PR** — added to audit-system |
| OPAMI UI | cpp-ui-opami | *(not in GitHub)* | **Outstanding** — no repo found |

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
| cpp-context-archiving | **PR** — added to case-management-system |
| cpp-context-boxworkmanagement | **PR** — added to case-management-system |
| cpp-context-correspondence | **PR** — added to case-management-system |
| cpp-context-material | **PR** — added to case-management-system |
| cpp-context-material-id-mapper | **Outstanding** — needs investigation |
| cpp-context-mi-reportdata | **PR** — added to management-information-system |
| cpp-context-mi-systemdata | **PR** — added to management-information-system |
| cpp-context-audit2dls | **PR** — added to audit-system |
| cpp-context-prosecution-documentqueue | **Outstanding** |
| cpp-context-resulting | **PR** — added to hearing-system |
| cpp-context-staging-bulkscan | **Outstanding** |
| cpp-context-staging-dcs | **PR** — added to case-management-system |
| cpp-context-staging-prosecutors | **Outstanding** — needs investigation |
| cpp-context-staging-prosecutors-civil | **PR** — added as new CPCI product |
| cpp-context-unifiedsearch-query | **PR** — added to case-management-system |

### UI repos (`cpp-ui-*`)

| Repo | Status |
|------|--------|
| cpp-ui-ai-intelligence | **Outstanding** — needs investigation |
| cpp-ui-audit-reports | **Outstanding** — needs investigation |
| cpp-ui-core | **Outstanding** — likely shared UI framework |
| cpp-ui-defence | **PR** — added to defence-portal |
| cpp-ui-external-services | **Outstanding** — placement TBD |
| cpp-ui-home | **Outstanding** — needs investigation |
| cpp-ui-pdk2 | **Outstanding** — needs investigation |

### `cp-*` repos (potentially services)

| Repo | Status |
|------|--------|
| cp-ai-rag-service | **Outstanding** — needs investigation |
| cp-audit-filter | **Outstanding** — needs investigation |
| cp-audit-reports-service-v2 | **Outstanding** — needs investigation |
| cp-auth-rules-filter | **Outstanding** — needs investigation |
| cp-case-document-knowledge-service | **Outstanding** — needs investigation |
| cp-client-mirror-gateway | **Outstanding** — needs investigation |
| cp-court-list-publishing-service | **Outstanding** — needs investigation |
| cp-crime-portal | **Outstanding** — needs investigation |
| cp-event-store | **Outstanding** — needs investigation |
| cp-job-manager | **Outstanding** — needs investigation |
| cp-result-definitions-browser | **Outstanding** — needs investigation |
| cp-task-manager | **Outstanding** — needs investigation |
| cp-vodafone-services | **Outstanding** — needs investigation |

---

## 3. In Model but no Repo Link

Components in the C4 model that could not be matched to a GitHub repo.

| Component | Kind | Product | Subdomain | Status |
|-----------|------|---------|-----------|--------|
| subscriptions-ui | user-interface | case-management-system | Case Administration | **Outstanding** — no repo found |
| assignment-service | microservice | case-management-system | Case Administration | **Outstanding** — no repo found |
| work-management-ui | user-interface | work-management-system | Case Administration | **Outstanding** — no repo found |
| camunda | application | work-management-system | Case Administration | **Outstanding** — third-party app, no repo expected |
| camunda-optimize | application | work-management-system | Case Administration | **Outstanding** — third-party app, no repo expected |
| error-queue-ui | user-interface | spi | Case Ingestion | **Outstanding** — no repo found |
| case-filter | functions | spi | Case Ingestion | **Outstanding** — no repo found |
| notepad-parsing-ui | user-interface | hearing-system | Court Hearings | **Outstanding** — no repo found |
| dlrm-integration-functions | functions | legacy-case-migration-system | DLRM | **Outstanding** — no repo found |
| idam-events-consumer | microservice | users-and-groups-system | Shared Components | **Outstanding** — no repo found (cpp-mbd-idam-integration is different) |
| pnld-offences | microservice | reference-data-system | Shared Components | **Outstanding** — no repo found |
| manage-permissions-ui | user-interface | users-and-groups-system | Shared Components | **Outstanding** — no repo found |
| listing-ui | user-interface | scheduling-and-listing-system | Scheduling and Listing | **PR** — link to cpp-ui-listing added |
| court-scheduler-ui | user-interface | scheduling-and-listing-system | Scheduling and Listing | **PR** — link to cpp-ui-courtscheduler added |

---

## 4. Products with no Components (Shell Products)

| Product | Subdomain | Status |
|---------|-----------|--------|
| audit-system | OPAMI | **PR** — audit2dls service added |
| management-information-system | OPAMI | **PR** — MI system-data and report-data services added |
| online-plea | Court Hearings | **PR** — online-plea-ui added |
| cppi | Case Ingestion | **Outstanding** — still a shell product |

---

## 5. Subdomain Discrepancies

| Component | PDF Domain | Model Subdomain | Status |
|-----------|-----------|-----------------|--------|
| prosecution-case-file-service | Case and Material Ingestion | Case Administration | **Resolved** — keeping in Case Administration |
| Prosecution Casefile UI | Case and Material Ingestion | Case Administration | **Resolved** — same as above |

---

## Summary

| Category | Resolved/PR | Outstanding | Total |
|----------|-------------|-------------|-------|
| Repo links added (Phase 2) | 42 | — | 42 |
| PDF items not in model (Section 1) | 10 | 8 | 18 |
| GitHub repos not in model (Section 2) | 12 | 23 | 35 |
| Model components without repo link (Section 3) | 2 | 12 | 14 |
| Shell products (Section 4) | 3 | 1 | 4 |
