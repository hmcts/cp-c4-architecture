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
```
view my-product-context of cp.my-product {
    title '[System Context] My Product'
    include *
    where
        not (kind is application or kind is microservice or kind is functions or kind is datastore or kind is user-interface)
    include cp.my-subdomain._
    exclude * -> *
    include * <-> cp.my-product
    exclude * <-> *
        where kind is mi
}
```

**Container view:**
```
view my-product-container-view of cp.my-product {
    title '[Container View] My Product'
    include *
    include cp.shared-components-subdomain.reference-data-system
    exclude * -> *
    include * <-> cp.my-product._
    include cp.my-product._ <-> cp.my-product._    // IMPORTANT: shows internal relationships
    exclude * <-> *
        where kind is mi
}
```

The `include product._ <-> product._` line is essential — without it, internal relationships between containers (e.g. UI → microservice) will not appear.

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
| `[audit]` | `cp.audit-system` | `sends data to` |
| `[notify]` | `cp.notification-notify` | `sends notifications using` |
| `[mi]` | MI system services | `sends data to` |

### JEE/Wildfly framework interceptors

Every microservice using the CPP JEE/Wildfly framework automatically gets two relationships via framework interceptors:

```
this -[auth]-> cp.users-and-groups 'makes authorisation decisions using'
this -[audit]-> cp.audit-system 'sends data to'
```

Always add these when defining a microservice.

### Granularity rules

- **Container-level over product-level**: When container detail exists, define relationships on specific containers, not the product
- **Actor relationships target UIs**: Actors interact through specific UI containers, not at product level
- **Remove product-level relationships** once they have been decomposed to container level

## Source Code Verification Workflow

When adding relationships for a product, consider verifying against the actual source code in GitHub repos. This avoids guessing based on patterns from other products.

**For Java microservices, check:**
- `pom.xml` — Maven dependencies reveal which other services are called (look for `*-query-api`, `*-command-api` artifacts)
- REST client definitions (often generated from RAML)
- JMS/ActiveMQ topic subscriptions in event source config
- Datasource configuration (standalone XML or resource descriptors)
- Liquibase migrations for database schema

**For Angular UIs, check:**
- Service files (`*.service.ts`) for HTTP calls to backend APIs
- `package.json` for `@cpp/*` shared library dependencies
- App routes for feature modules
- Environment/config files for API base URLs

**What to look for:**
- Database connections (datasource config)
- REST/HTTP calls to other services
- JMS/ActiveMQ topics and queues
- Shared libraries (`@cpp/*` npm packages, Maven dependencies)
- External system integrations (SOAP, XML generation)

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
