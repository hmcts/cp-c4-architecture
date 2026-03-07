# File Service Usage Investigation

The File Service (`cp-file-service`) is "a simple drop in library for storing binary files in Postgres."
All consumers share a single database. We want to model the File Service as a shared component
containing the database, with relationships from each consuming microservice.

Repository: https://github.com/hmcts/cp-file-service

## Active Users

### Store and Retrieve

| C4 Element | Repo | Operations | Triggers |
|---|---|---|---|
| progression-service | cpp-context-progression | Store + Retrieve + Delete | **Store:** NOW documents, trial record sheets, court registers, online plea/finance documents, court document uploads. **Retrieve:** online plea metadata, generated document payloads. **Delete:** notification cleanup on sent/failed events. |
| prosecution-case-file-service | cpp-context-prosecution-casefile | Store + Retrieve + Delete | **Store:** add-material commands (v1, v2, bulk). **Retrieve:** POCA file content. **Delete:** cleanup on material-added, material-rejected, IDPC/bulkscan-rejected events. |
| sjp-service | cpp-context-sjp | Store + Retrieve | **Store:** transparency/press report payloads (English/Welsh), endorsement removal & enforcement email attachments, case document uploads. **Retrieve:** transparency report content files for download, generated document content. |
| material-service | cpp-context-material | Retrieve + Delete | **Retrieve:** file content for Alfresco upload, Azure blob archive, PDF conversion. **Delete:** on material-deleted and failed-to-add-material events. Files are stored upstream by prosecution-casefile or progression. |
| document-generator | cpp-context-system-doc-generator | Store + Retrieve | **Retrieve:** JSON payload for document rendering on `generate-document-requested` event. **Store:** rendered document (PDF/HTML/CSV) back to file service after generation. |
| staging-dvla | cpp-context-staging-dvla | Store + Retrieve | **Store:** document generator payloads, driver search audit report CSV. **Retrieve:** files during audit report lifecycle. |

### Store Only

| C4 Element | Repo | Triggers |
|---|---|---|
| archiving-service | cpp-context-archiving | Stores prosecution case JSON for archive document generation on `archive-requested` event. |
| defence-service | cpp-context-defence | Stores OPA PDF documents via `DocumentGeneratorService`, passes file ID to material upload. |
| results-service | cpp-context-results | Stores JSON payloads for doc generation, NCES PDF documents, NCES email notification templates, informant register CSVs for email distribution. |
| staging-prosecutors | cpp-context-staging-prosecutors | Stores binary document content extracted from CPS XML material submissions (CP20 TDocument entries). |
| applications-court-orders | cpp-context-applications-courtorders | REST adapter provides multipart file upload endpoint for court order/application documents. No custom Java code - framework-provided. |

### Retrieve Only

| C4 Element | Repo | Triggers |
|---|---|---|
| reference-data | cpp-context-reference-data | Retrieves CSV files and metadata on `judiciary-uploaded` event (judiciary data, LJA mappings). |
| pnld-offences | cpp-context-staging-pnld-offences | Retrieves uploaded zip file on `upload-offences` commands and `upload-accepted` events for batch XML processing. |
| notification-notify | cpp-context-notification-notify | Retrieves file attachments for email notifications on `notification-queued` events with fileId. |
| prosecution-document-queue | cpp-context-prosecution-documentqueue | Retrieves Base64-encoded document content via query API. Deletes expired/filtered documents. |

## No Active Usage (dependency only or legacy)

These repos have `file-service-persistence` or `rest-adapter-file-service` in their POM but do NOT call the library in Java code:

| Repo | Notes |
|---|---|
| cpp-context-listing | Legacy - file service usage removed in v2.1 |
| cpp-context-listing-courtscheduler | No dependency or usage found |
| cpp-context-staging-pubhub | No dependency or usage found |
| cpp-context-subscriptions | No dependency or usage found |
| cpp-context-staging-dcs | POM dependency only - uses Azure Blob Storage directly |
| cpp-context-hearing | POM dependency only - passes file service IDs but doesn't call store/retrieve |
| cpp-context-staging-prosecutors-spi | POM dependency only - misleadingly named ProsecutionCaseFileService queries cases, not files |
| cpp-context-correspondence | No dependency or usage found |
| cpp-context-resulting | No dependency or usage found |
| cpp-context-hearing-nows | No dependency or usage found |
| cpp-context-system-announcement | No dependency or usage found |
| cpp-context-staging (users-and-groups) | No dependency or usage found |
| cpp-context-mi-reportdata | No dependency or usage found |
| cpp-context-prosecution-casefile-dlrm | Delegates file handling to material context via commands |
