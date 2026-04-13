# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Crime Common Platform** architecture model, using [LikeC4](https://likec4.dev/) DSL and the C4 modelling approach to describe the system architecture. The output is a static site deployed to GitHub Pages at https://hmcts.github.io/cp-c4-architecture/.

## Commands

- `npm run dev` / `npm run start` — Start local LikeC4 dev server with live reload
- `npm run build` — Build static site to `./dist`
- `npm run test` — Run model validation tests (vitest)
- `npm run generate:model` — Regenerate TypeScript model from .c4 sources to `./test/likec4-model.ts` (also runs on `postinstall`)
- `npm run generate:relationships-csv` — Generate CSV of all relationships
- `npm run generate:product-components-csv` — Generate CSV of products and components grouped by subdomain

Package manager is **npm** (the committed lockfile is `package-lock.json` and CI runs `npm install`). Node.js 20+ required.

## Architecture & File Structure

### LikeC4 DSL Files (`src/`)

All architecture is defined in `.c4` files using LikeC4 DSL:

- **`_spec.c4`** — Element/relationship specification (kinds, styles, tags, colors). Defines element types: `actor`, `platform`, `subdomain`, `product`, `shared-component`, `system`, `external-system`, `application`, `microservice`, `functions`, `component`, `service`, `user-interface`, `datastore`, `db-table`. Also defines relationship kinds: `audit`, `auth`, `mi`, `shared`, `solid`, `many-to-many`.
- **`model.c4`** — Root `cp` system element definition
- **`model.people.c4`** — Actor definitions (defendants, judges, court staff, etc.)
- **`model.views.c4`** — Top-level views (system landscape, subdomains overview)
- **`model-external-systems.c4`** — External systems (Libra, Xhibit, DARTS, HMPPS, etc.)

### Subdomain Directories

Each subdomain has its own directory under `src/` with consistent naming:
- `subdomain-{name}/subdomain-{name}.c4` — Subdomain definition (extends `cp` using `extend cp { ... }`)
- `subdomain-{name}/product-{name}.c4` — Product definitions (extend the subdomain)
- `subdomain-{name}/model.views.{name}.c4` — Subdomain-specific views

The `shared-components/` directory follows a similar pattern but uses `shared-component` kind instead of `product`.

### Model Hierarchy

The C4 model is organized as: `cp` (system) → subdomains → products/shared-components → microservices/UIs/datastores. Element IDs follow dot-notation: `cp.{subdomain}.{product}.{component}`.

### Custom Generators (`likec4.config.ts`)

Two custom generators produce CSV reports by traversing the model programmatically via the `likec4model` API. They use `ctx.write()` to output files and `ctx.abort()` on error.

### Model Validation (`test/`)

Tests use Vitest and the generated TypeScript model (`test/likec4-model.ts`, gitignored). The global setup regenerates the model before tests run. Current validations:
- Many-to-many relationships are only allowed between `db-table` elements
- All `component` elements must have a `technology` property

### CI/CD

GitHub Actions (`.github/workflows/pages.yml`) runs validation then builds and deploys to GitHub Pages. Also auto-redeploys when LikeC4 releases a new version.

## Conventions for .c4 Files

Use the `c4-model-maintenance` skill when working on `.c4` files — it covers LikeC4 syntax patterns, relationship conventions, view configuration, and source code verification workflows.
