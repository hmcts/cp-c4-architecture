# Hearing System — Relationship Review

Based on analysis of the actual GitHub source code for each component.

## Legend

- **Status**: `pending` | `approved` | `rejected` | `done`
- **Action**: what we'll do once approved

---

## 1. Notepad Parsing UI

The notepad parsing feature is confirmed built into `cpp-ui-hearing` (Court Hearing UI). It is a single service file (`notepad-parser.service.ts`) within the Enter Results feature — not a separate app or distinct module.

| # | Issue | Action | Status |
|---|-------|--------|--------|
| 1.1 | `notepad-parsing-ui` exists as a separate element but is part of `court-hearing-ui` | Remove element entirely | `approved` |
| 1.2 | `court_clerk -> notepad-parsing-ui` "records hearing using" | Move to `court-hearing-ui` (covered by existing actor items in section 8) | `approved` |
| 1.3 | `notepad-parsing-ui -> cp.reference-data-system.reference-data` "obtains result definition data from" | Move to `court-hearing-ui` (covered by item 2.2) | `approved` |

---

## 2. Court Hearing UI

Currently has **zero** outgoing relationships. The `cpp-ui-hearing` repo confirms calls to all of the following:

| # | Target | Title | Description | Action | Status |
|---|--------|-------|-------------|--------|--------|
| 2.1 | `hearing-service` | manages hearings using | Retrieves hearing lists, logs hearing events, records session times, and manages draft results | Add relationship | `approved` |
| 2.2 | `cp.reference-data-system.reference-data` | looks up reference data from | Obtains judicial members, verdict types, trial types, sentencing options, and parses notepad shorthand into result definitions | Add relationship | `approved` |
| 2.3 | `cp.reference-data-system.reference-data-offences` | looks up offence definitions from | Searches for offence types and their details | Add relationship | `approved` |
| 2.4 | `cp.case-management-system.progression-service` | downloads court documents and submits breach applications using | Downloads Notification of Work documents and submits breach applications for case progression | Add relationship | `approved` |
| 2.5 | `cp.case-management-system.application-court-orders-service` | retrieves court orders from | Looks up court orders associated with a defendant and their offence dates | Add relationship | `approved` |
| 2.6 | `cp.case-management-system.sjp-service` | retrieves outstanding fines from | Retrieves outstanding fine information for Single Justice Procedure cases | Add relationship | `approved` |
| 2.7 | `cp.users-and-groups-system.users-and-groups` | validates user permissions using | Checks user roles, permissions, group memberships, and feature access to control what court staff can do. **Kind: `auth`** | Add relationship | `approved` |
| 2.8 | `cp.results-distribution-system.results-service` | checks defendant tracking status using | Retrieves electronic monitoring and tracking status for defendants during hearings | Add relationship | `approved` |
| 2.9 | `cp.scheduling-and-listing-system.listing-service` | searches for available hearings in | Finds available hearing slots when booking provisional hearings | Add relationship | `approved` |

---

## 3. Hearing Service

Currently has: `-> hearing-database`, `-> results-service`, `-> mi-report-data-service`.

Missing relationships confirmed from `cpp-context-hearing` repo:

| # | Target | Title | Description | Action | Status |
|---|--------|-------|-------------|--------|--------|
| 3.1 | `cp.reference-data-system.reference-data` | looks up reference data from | Retrieves Xhibit event mappings, court data, and other reference information needed to process hearings | Add relationship | `approved` |
| 3.2 | `cp.case-management-system.progression-service` | updates case progression using | Sends and retrieves case progression information as hearing events occur | Add relationship | `approved` |
| 3.3 | `cp.case-management-system.material-service` | manages case material using | Submits material updates related to hearings | Add relationship | `approved` |
| 3.4 | `cp.notify-system.notification-notify` | sends notifications using | Triggers notifications to relevant parties when hearing events occur. **Kind: `notify`** | Add relationship | `approved` |
| 3.5 | `cp.results-distribution-system.staging-enforcement-service` | sends and retrieves enforcement data using | Submits enforcement actions arising from hearings and queries enforcement status | Add relationship | `approved` |
| 3.6 | `cp.users-and-groups-system.users-and-groups` | makes authorisation decisions using | Validates user permissions and group memberships for hearing operations. **Kind: `auth`** | Add relationship | `approved` |
| 3.7 | `cp.id-mapper-system.system-id-mapper` | looks up IDs using | Translates identifiers between Common Platform and external systems such as Xhibit | Add relationship | `approved` |
| 3.8 | `cp.document-generation-system.document-generator` | generates documents using | Requests generation of hearing-related documents and reports | Add relationship | `approved` |
| 3.9 | `cp.file-service-system` | stores and retrieves files using | Persists hearing-related documents and binary content | Add relationship | `approved` |
| 3.10 | `xhibit` | publishes hearing events to | Generates and sends XML messages containing court status and hearing event data for public display | Add relationship | `approved` |
| 3.11 | `cp.audit-system` | sends audit data to | Automatic framework interceptor writes audit messages for all hearing operations. **Kind: `audit`** | Add relationship | `approved` |

---

## 4. Resulting Service

Currently has: `-> resulting-database`, `-> mi-system-data-service`, `-> mi-report-data-service`.

Missing relationships confirmed from `cpp-context-resulting` repo:

| # | Target | Title | Description | Action | Status |
|---|--------|-------|-------------|--------|--------|
| 4.1 | `cp.reference-data-system.reference-data` | looks up reference data from | Retrieves result definitions, enforcement areas, prosecutors, and organisation units | Add relationship | `approved` |
| 4.2 | `cp.reference-data-system.reference-data-offences` | looks up offence definitions from | Retrieves offence details by code for result processing | Add relationship | `approved` |
| 4.3 | `cp.case-management-system.sjp-service` | retrieves SJP case details from | Queries cases, sessions, employer details, and financial means for Single Justice Procedure cases, and uploads case documents | Add relationship | `approved` |
| 4.4 | `cp.case-management-system.prosecution-case-file-service` | retrieves prosecution case details from | Queries prosecution case information when processing results | Add relationship | `approved` |
| 4.5 | `cp.document-generation-system.document-generator` | generates documents using | Requests PDF generation for result orders, employer attachment to earnings, and intention to disqualify notices | Add relationship | `approved` |
| 4.6 | `cp.notify-system.notification-notify` | sends letter notifications using | Sends printed letter notifications for result orders and other hearing outcomes. **Kind: `notify`** | Add relationship | `approved` |
| 4.7 | `cp.file-service-system` | stores and retrieves files using | Persists generated PDF documents such as result orders | Add relationship | `approved` |
| 4.8 | `cp.id-mapper-system.system-id-mapper` | looks up IDs using | Maps notification IDs to case IDs for document print tracking | Add relationship | `approved` |
| 4.9 | `cp.case-management-system.material-service` | retrieves case material from | Obtains PDF file URLs for case materials linked to notifications | Add relationship | `approved` |
| 4.10 | `cp.users-and-groups-system.users-and-groups` | makes authorisation decisions using | Automatic framework interceptor enforces authorisation rules. **Kind: `auth`** | Add relationship | `approved` |
| 4.11 | `cp.audit-system` | sends audit data to | Automatic framework interceptor writes audit messages for all resulting operations. **Kind: `audit`** | Add relationship | `approved` |

---

## 5. Staging DARTS

Currently has: `-> staging-darts-database`, `cp.listing-service -> this`.

Missing relationships confirmed from `cpp-context-staging-darts` repo:

| # | Target | Title | Description | Action | Status |
|---|--------|-------|-------------|--------|--------|
| 5.1 | `cp.reference-data-system.reference-data` | looks up reference data from | Retrieves court room mappings and hearing event mappings for DARTS integration | Add relationship | `approved` |
| 5.2 | `darts` | sends hearing events and court lists to | Forwards hearing event logs, court daily lists, case archives, and transcription requests to the external DARTS system via SOAP | Add relationship | `approved` |
| 5.3 | `cp.users-and-groups-system.users-and-groups` | makes authorisation decisions using | Automatic framework interceptor enforces authorisation rules. **Kind: `auth`** | Add relationship | `approved` |
| 5.4 | `cp.audit-system` | sends audit data to | Automatic framework interceptor writes audit messages for all staging DARTS operations. **Kind: `audit`** | Add relationship | `approved` |

---

## 6. External Services UI

Currently has: `-> results-distribution-system.staging-dvla-service`.

Missing relationships confirmed from `cpp-ui-external-services` repo:

| # | Target | Title | Description | Action | Status |
|---|--------|-------|-------------|--------|--------|
| 6.1 | `cp.reference-data-system.reference-data` | looks up reference data from | Retrieves driver audit reason types for DVLA record searches | Add relationship | `approved` |
| 6.2 | `cp.users-and-groups-system.users-and-groups` | validates user permissions using | Checks user permissions and group memberships at startup. **Kind: `auth`** | Add relationship | `approved` |

---

## 7. Product-Level Relationships

These currently exist at the `hearing-system` product level and should be moved to specific containers now that we have container-level detail:

| # | Current relationship | Resolution | Action | Status |
|---|---------------------|------------|--------|--------|
| 7.1 | `hearing-system -> darts` "posts hearing events to" | Replaced by 5.2 (`staging-darts -> darts`) | Remove product-level relationship | `approved` |
| 7.2 | `hearing-system -> hmpps` "posts hearing events to" | This flows via results-distribution-system, not directly from hearing-system containers | Remove product-level relationship | `approved` |
| 7.3 | `hearing-system -> laa` "posts hearing events to" | This flows via results-distribution-system, not directly from hearing-system containers | Remove product-level relationship | `approved` |
| 7.4 | `hearing-system -> cp.scheduling-and-listing-system` "hearing details changed" | Originates from hearing-service via domain events | Replace with `hearing-service -> cp.scheduling-and-listing-system.listing-service` "publishes hearing changes to" | `approved` |
| 7.5 | `hearing-system -> cp.case-management-system` "shares case markers..." | Already captured by specific container relationships in sections 3 and 4 (progression-service, material-service, sjp-service, prosecution-case-file-service) | Remove product-level relationship | `approved` |

---

## 8. Actor Relationships

All actors interact with the system through the Court Hearing UI. Move relationships from product level to container level.

| # | Current relationship | Action | Status |
|---|---------------------|--------|--------|
| 8.1 | `defendant -> hearing-system` "enters plea using" | Move to `defendant -> court-hearing-ui` | `approved` |
| 8.2 | `judge_or_magestrate -> hearing-system` "accesses hearing lists and boxwork using" | Move to `judge_or_magestrate -> court-hearing-ui` | `approved` |
| 8.3 | `recorder -> hearing-system` "records events during hearings using" | Move to `recorder -> court-hearing-ui` | `approved` |
| 8.4 | `listing_officer -> hearing-system` "manages court schedule and allocates hearings using" | Move to `listing_officer -> court-hearing-ui` | `approved` |
| 8.5 | `court_clerk -> hearing-system` "runs court room logistics on hearing day using" | Move to `court_clerk -> court-hearing-ui` (also absorbs `court_clerk -> notepad-parsing-ui` from 1.2) | `approved` |
| 8.6 | `legal_advisor -> hearing-system` "manages hearings in court and advises magistrates using" | Move to `legal_advisor -> court-hearing-ui` | `approved` |
| 8.7 | `court_admin -> hearing-system` "administrates hearings and manages documentation using" | Move to `court_admin -> court-hearing-ui` | `approved` |
