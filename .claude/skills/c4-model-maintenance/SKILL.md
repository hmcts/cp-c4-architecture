---
name: c4-model-maintenance
description: Use when adding, modifying, or reviewing C4 model elements — new subdomains, products, shared components, relationships, or views. Also use when asked to explore or document system architecture.
---

# C4 Model Maintenance

## Overview

Reference guide for maintaining the Common Platform C4 architecture model using LikeC4 DSL. Covers project conventions, syntax patterns, and workflows for adding or reviewing model elements.

## Project Structure

### Model Hierarchy

`cp` (system) → subdomains → products/shared-components → containers (microservices/UIs/datastores)

Element IDs use dot-notation: `cp.{subdomain}.{product}.{component}`

### File Layout

```
src/
  _spec.c4                                    # Element kinds, relationship kinds, styles
  model.c4                                    # Root cp element
  model.people.c4                             # Actor definitions
  model.views.c4                              # Top-level views
  model-external-systems.c4                   # External systems
  subdomain-{name}/
    subdomain-{name}.c4                       # Subdomain definition (extends cp)
    product-{name}.c4                         # Product definitions (extend subdomain)
    model.views.{name}.c4                     # Views for this subdomain
  shared-components/
    model.shared-components.c4                # Shared component definitions
```

## LikeC4 Syntax Patterns

### Extending the model

Products extend their parent subdomain:

```
model {
    extend cp.{subdomain} {
        my-product = product {
            title 'My Product'
            summary 'What it does'

            // containers go here
        }
    }
}
```

### Element definitions

**Microservice:**
```
my-service = microservice {
    title 'My Service'
    technology 'Java EE'
    summary 'What it does'
    metadata {
        language 'Java'
        software-framework 'Java EE 8'
    }
    link https://github.com/hmcts/repo-name 'Repository'
}
```

**User interface:**
```
my-ui = user-interface {
    title 'My UI'
    technology 'Angular'
    summary 'What it provides'
    metadata {
        language 'TypeScript'
        software-framework 'Angular'
    }
    style {
        icon tech:angular
    }
    link https://github.com/hmcts/repo-name 'Repository'
}
```

**Datastore:**
```
my-database = datastore {
    title 'My Database'
    technology 'PostgreSQL'
    summary 'Stores events and entities'
    style {
        icon tech:postgresql
    }
}
```

### Relationship syntax

```
// Standard relationship
this -> target 'title'

// Relationship with kind
this -[auth]-> target 'title'

// Incoming relationship (defined inside the target)
source -> this 'title'

// With technology annotation
this -> target 'title' {
    technology 'JSON/HTTPS'
}
```

### View syntax

**System context view:**

Shows the product as a single box (no internal containers), surrounded by upstream/downstream subdomains and their products. Excludes cross-cutting relationship kinds that aren't the focus of this view.

```
view my-product-context of cp.my-product {
    title '[System Context] My Product'
    include *
    where
        not (kind is application or kind is microservice or kind is functions or kind is datastore or kind is user-interface or kind is component)
    include cp.my-subdomain._                       // sibling products in same subdomain
    include cp.other-subdomain._                    // upstream/downstream subdomains
    include cp.shared-components-subdomain._
        where kind is product
    exclude * -> *
    include * <-> cp.my-product
    exclude * <-> *
        where kind is audit or kind is mi or kind is auth or kind is shared

    style cp.other-subdomain.*, cp.shared-components-subdomain.* {
        color secondary
    }
}
```

**Key rules for context views:**
- Filter out ALL container kinds including `component` — only products, subdomains, and actors should appear
- Include every subdomain that has relationships with the product
- Exclude cross-cutting relationship kinds (`audit`, `mi`, `auth`, `shared`) UNLESS the product IS that cross-cutting system. E.g. the Audit System context view should NOT exclude `[audit]` relationships since showing who sends audit data is the whole point. Same for MI System and `[mi]`.
- Style external subdomains as `color secondary` to visually distinguish them

**Container view:**

Shows the product's internal containers with relationships between them and to external systems. Include upstream subdomains so their products are visible alongside the internal containers.

```
view my-product-container-view of cp.my-product {
    title '[Container View] My Product'
    include *
    include cp.other-subdomain._                    // upstream subdomains with relationships
    include cp.shared-components-subdomain._
        where kind is product
    exclude * -> *
    include * <-> cp.my-product._
    include cp.my-product._ <-> cp.my-product._    // IMPORTANT: shows internal relationships
    exclude * <-> *
        where kind is mi or kind is auth or kind is shared
}
```

**Key rules for container views:**
- The `include product._ <-> product._` line is essential — without it, internal relationships between containers (e.g. UI → microservice) will not appear
- Include upstream subdomains so their products show as context around the containers
- Apply the same cross-cutting exclusion logic as context views (don't exclude the system's own kind)

## Relationship Conventions

### Title format

Titles fill a sentence: **"A title B"**. The title is the part between source and target.

- First letter always lowercase
- Should read as natural language
- Examples:
  - `this -> hearing-service 'manages hearings using'`
  - `this -> cp.reference-data-system.reference-data 'looks up reference data from'`
  - `this -> darts 'sends hearing events and court lists to'`

### Descriptions

When a relationship has a description, write it in business language:
- "Retrieves result definitions, enforcement areas, and prosecutors"
- NOT "queries REST endpoint for reference data entities"

### Relationship kinds

Defined in `_spec.c4`. Use these for specific shared component integrations:

| Kind | Target | Title pattern |
|------|--------|---------------|
| `[auth]` | `cp.users-and-groups` | `makes authorisation decisions using` |
| `[audit]` | `cp.audit-system.audit-message-broker` | `sends data to` |
| `[notify]` | `cp.notification-notify` | `sends notifications using` |
| `[mi]` | MI system services | `sends data to` |

### JEE/Wildfly framework interceptors

Every microservice using the CPP JEE/Wildfly framework automatically gets two relationships via framework interceptors (`LocalAuditInterceptor` and `LocalAccessControlInterceptor`):

```
this -[auth]-> cp.users-and-groups 'makes authorisation decisions using'
this -[audit]-> cp.audit-system.audit-message-broker 'sends data to'
```

Always add these when defining a Java EE microservice.

**Audit interceptor details:**
- Audit is enabled by default on command-api, query-api, and event-api layers (configurable via JNDI)
- Some services override the command API interceptor chain for file uploads (e.g. Progression, Staging Prosecutors) — they omit audit on commands but still send via query/event APIs. These should still get the `[audit]` relationship.
- The `system-id-mapper` sends audit data, but it's filtered out during Fabric Lakehouse ingestion as it's not useful for forensic audit.

**Spring Boot microservices** do NOT automatically get audit. They can optionally use the `cp-audit-filter` library (check `build.gradle` for the dependency). Only add `[audit]` if the service uses this library. Spring Boot services also do NOT get the `[auth]` relationship to Users & Groups — they handle auth differently.

### Granularity rules

- **Container-level over product-level**: When container detail exists, define relationships on specific containers, not the product
- **Actor relationships target UIs**: Actors interact through specific UI containers, not at product level
- **Remove product-level relationships** once they have been decomposed to container level

## Source Code Verification Workflow

When adding relationships for a product, consider verifying against the actual source code in GitHub repos. This avoids guessing based on patterns from other products. Use `gh` CLI (not the GitHub MCP plugin) to explore repos.

**Finding repos:**
```bash
gh search repos --owner hmcts "keyword" --match name --json name,description
```

**Reading files from repos:**
```bash
gh api repos/hmcts/{repo}/contents/{path} --jq '.content' | base64 -d
gh api repos/hmcts/{repo}/contents/{directory} --jq '.[].name'
```

**Searching code across the org:**
```bash
gh search code "pattern" --owner hmcts --json repository,path
gh search code "pattern" --repo hmcts/{repo} --json path
```

**For Java EE microservices, check:**
- `pom.xml` — Maven dependencies reveal which other services are called (look for `*-query-api`, `*-command-api` artifacts)
- `*InterceptorChainProvider.java` — Custom interceptor chains may override default audit/auth behaviour
- REST client definitions (often generated from RAML)
- JMS/ActiveMQ topic subscriptions in event source config
- Datasource configuration (standalone XML or resource descriptors)
- Liquibase migrations for database schema

**For Spring Boot microservices, check:**
- `application.yaml` — Service base URLs, paths, and integrations reveal all downstream dependencies
- `build.gradle` — Check for `cp-audit-filter` dependency (audit) and other CP libraries
- Service classes (`*Service.java`) — REST client calls to other CP services
- Config classes (`*Config.java`) — Bean definitions for external service clients

**For Angular UIs, check:**
- Service files (`*.service.ts`) for HTTP calls to backend APIs
- `package.json` for `@cpp/*` shared library dependencies
- App routes for feature modules
- Environment/config files for API base URLs

**For Node.js Azure Functions (Azure Durable Functions), check:**
- `pom.xml` in the `azure-functions/` directory — `frontend-maven-plugin` pins the Node.js version (`<nodeVersion>`)
- File extensions (`.js` vs `.ts`) and presence of `tsconfig.json` to determine actual language
- Orchestrator files (`*Handler/index.js` or `*Orchestrator/index.js`) — these define the activity pipeline and reveal the full sequence of operations
- Activity files (`*/index.js`) — each activity may make HTTP calls to other services via environment variables like `*_CONTEXT_API_BASE_URI`
- Shared utilities (e.g. `HearingResultedCacheQuery`) — typically read from Redis first, then fall back to a query API on cache miss
- `host.json` — Durable Task hub configuration and extension bundles
- Test fixtures (`test/*.json`) — often reveal payload structures and recipient data that clarify business purpose
- Note: multiple function apps may live in a single monorepo under separate directories

**Tracing document lifecycle across services:**
When a function app submits data to a service like Progression for document generation, trace the full chain to understand what happens downstream. The function app's C4 description should capture the end-to-end outcome (e.g. "aggregated into a daily PDF and emailed to YOTs"), not just "sends data to Progression". Check:
- What the receiving service does with the payload (aggregation? immediate processing?)
- Whether it calls Document Generator (Docmosis templates) for PDF rendering
- Whether it calls Notification Notify / GOV.UK Notify for email distribution
- Who the recipients are (from subscription/test data)

**What to look for:**
- Database connections (datasource config)
- REST/HTTP calls to other services
- JMS/ActiveMQ topics and queues
- Shared libraries (`@cpp/*` npm packages, Maven dependencies)
- External system integrations (SOAP, XML generation)

## Confluence as Architecture Source

The Atlassian MCP can read Confluence pages for architecture context not visible in code (data flow designs, pipeline documentation, BFF designs, decommission plans). Use when modelling new or redesigned systems:
- Read team home pages for architecture overviews
- Explore child pages under "Architecture" sections for technical designs
- Look for data flow descriptions, sequence diagrams (in text), and pipeline documentation

## Validation

After making changes, always run:

```bash
npm run build    # Build static site — checks for syntax errors
npm run test     # Run model validation tests
```

### Fixing layout drift

When adding new elements or relationships, affected views will show a "layout drift detected" warning during build. This means the view's saved layout is out of date and new elements won't appear on the diagram until re-laid out.

**Before committing**, ask the user to:
1. Open the dev server (`npm run dev`)
2. Navigate to each affected view
3. Re-layout the diagram so new elements are positioned correctly
4. Save the updated layout

This is especially important when adding new elements (datastores, microservices, etc.) — they will be invisible on the published site until the layout is updated.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Container view missing internal relationships | Add `include product._ <-> product._` |
| Relationships defined at product level when containers exist | Move to specific containers |
| Actors pointing to product instead of UI | Point to the specific `user-interface` element |
| Missing auth/audit on microservices | Add `[auth]` and `[audit]` relationships |
| Technical relationship titles | Use business language that reads as a sentence |
| Uppercase first letter in relationship title | Always lowercase |
| Guessing relationships from other products | Verify against actual source code |
