# Redis Cache Usage Investigation

All services connect to the same shared Azure Cache for Redis instance, but use different Redis database numbers and key namespaces to isolate their data.

## How Each Service Uses Redis

### 1. Reference Data Service (`reference-data`) — DB 0
**Purpose:** Caches its own query API responses (courts, result definitions, offences, prosecutors, etc.)
**Pattern:** Read-through cache via `CacheInterceptor` on the query API chain. On cache miss, executes the DB query and caches the response. External callers just call the reference-data REST API — they don't interact with Redis directly.
**Keys:** `{queryName}?{params}` e.g. `referencedata.query.court-centres`
**TTL:** 24 hours. Manual flush endpoint available (`FLUSHDB`).

### 2. Results Service (`results-service`) — DB 0
**Purpose:** Stores hearing results for downstream Azure Functions to read.
**Pattern:** Write-on-event. When a `hearing-resulted` event arrives, the service writes the result payload to Redis and sends an EventGrid notification. The Azure Functions then read the result directly from Redis using matching key patterns.
**Keys:** `{prefix}_{hearingId}_{hearingDay}_result_` where prefix is `EXT_` (external/LAA format), `INT_` (internal/detailed), or `SJP_` (Single Justice Procedure).
**TTL:** External keys (`EXT_`): ~91 days. Internal/SJP keys: 24 hours.

### 3. Azure Functions — Results Distribution (`laa-result-functions`, etc.) — DB 0
**Purpose:** Read cached hearing results written by the results-service.
**Pattern:** Cache-aside read. All functions use a shared `HearingResultedCacheQuery` activity that checks Redis first, falling back to the results-query-api REST endpoint on cache miss.
**Keys:** Same key patterns as results-service (`EXT_`, `INT_`, `SJP_` prefixes).

| Function | Prefix Read | Purpose |
|---|---|---|
| LAA Result Functions | `EXT_` | Publishes results to Legal Aid Agency |
| Probation Result Functions | `EXT_` | Publishes results to HMPPS/probation |
| Court Order Result Functions | `INT_` | Creates court orders |
| Court Register Result Functions | `INT_` | Updates court register |
| Prison Court Record Result Functions | `INT_` | Prison court records |
| Informant Register Result Functions | `INT_` | Updates informant register |
| NOWs Result Functions | `INT_` | Creates NOWs documents |
| SJP Result Functions | `SJP_` | SJP case results |

### 4. Users and Groups (`users-and-groups`) — DB 5
**Purpose:** Caches user details, groups, permissions, roles, and org data.
**Pattern:** Read-through cache with event-driven invalidation. Query responses are cached; when a user/group/role change event arrives, all keys in the affected domain are invalidated using Redis Sets for targeted removal. Cache is flushed on startup.
**Keys:** `{queryName}_{identifier}?{params}` e.g. `usersgroups.get-user-details_{userId}`
**TTL:** 24 hours. Manual flush endpoint available.

### 5. MI Report Data Service (`mi-report-data-service`) — DB 1
**Purpose:** Caches reference data fetched from the reference-data API for use in MI report generation and event processing.
**Pattern:** Preload on startup + scheduled refresh (every ~3 hours). Uses Redis hash maps. Does NOT cache its own query responses — it caches reference data from external APIs.
**Keys:** Enum names as hash keys: `COURTS`, `HEARING_TYPES`, `JUDICIARIES`, `VERDICT_TYPES`, `OFFENCES`, `RESULTS`, `PROSECUTORS`
**TTL:** None (no expiry, overwritten on each refresh cycle).

### 6. Material Service (`material-service`) — DB 2
**Purpose:** Caches material query API responses.
**Pattern:** Read-through cache via `CacheInterceptor` (same pattern as reference-data). Certain queries excluded (downloadable-materials, structured forms).
**Keys:** `{queryName}?{params}` e.g. `material.query.material-metadata?caseId="abc"`
**TTL:** 24 hours.

### 7. Court Scheduler Service (`court-scheduler-service`) — DB 0
**Purpose:** Caches reference data (court rooms, business types, judiciaries, session allocations) fetched from the reference-data API for use in court scheduling.
**Pattern:** Lazy-load on cache miss. When data is requested and not in Redis, fetches from reference-data API and caches. Fetching a single item warms the cache for all items of that type.
**Keys:** Prefixed by data type: `RotaBusinessType_{code}`, `RotaCourtRoom_{uuid}`, `CpCourtRoom_{id}`, `RotaJudiciaries_`, etc.
**TTL:** 24 hours (session allocations: 5 minutes).

### 8. Staging Enforcement Service (`staging-enforcement-service`) — DB 0
**Purpose:** Caches GOB (enforcement) outstanding fines SOAP responses to avoid duplicate calls for the same defendant.
**Pattern:** Cache-aside. On defendant search, checks Redis first, falls back to SOAP call on miss.
**Keys:** `stagingenforcement-query-api_outstanding-fines_{defendantId}`
**TTL:** 10 seconds (very short — just deduplication).

## Summary by Usage Pattern

| Pattern | Services |
|---|---|
| **Read-through cache** (caches own query responses) | reference-data, users-and-groups, material-service |
| **Write-for-others** (writes data for other services to read) | results-service → Azure Functions |
| **Cache external data** (fetches from other APIs, caches locally) | mi-report-data-service, court-scheduler-service |
| **Short-lived dedup cache** | staging-enforcement-service |

## Redis Database Allocation

| DB | Services |
|---|---|
| 0 | reference-data, results-service, Azure Functions, court-scheduler, staging-enforcement |
| 1 | mi-report-data-service |
| 2 | material-service |
| 5 | users-and-groups |
