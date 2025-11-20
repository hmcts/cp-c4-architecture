# Common Platform C4 Architecture - Comprehensive Reference Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Project Overview](#project-overview)
3. [Project Structure](#project-structure)
4. [C4 Model Concepts](#c4-model-concepts)
5. [File Organization and Naming Conventions](#file-organization-and-naming-conventions)
6. [Architecture Hierarchy](#architecture-hierarchy)
7. [Navigating the Architecture](#navigating-the-architecture)
8. [Adding and Modifying Components](#adding-and-modifying-components)
9. [View Types and Their Purposes](#view-types-and-their-purposes)
10. [Best Practices](#best-practices)
11. [Examples and Patterns](#examples-and-patterns)
12. [Development Workflow](#development-workflow)
13. [Troubleshooting](#troubleshooting)
14. [Glossary](#glossary)

---

## Introduction

This reference manual provides comprehensive documentation for the Common Platform C4 Architecture project. The project uses [LikeC4](https://likec4.dev/) tools and DSL to describe the architecture following the [C4 Model](https://c4model.com/) approach.

### Purpose

The C4 architecture documentation serves to:
- Provide a visual representation of the Common Platform system architecture
- Enable stakeholders to understand system relationships and dependencies
- Support architectural decision-making and communication
- Facilitate onboarding of new team members
- Document the current state of the system

### Target Audience

- Software architects and engineers
- Product managers and business analysts
- DevOps and infrastructure teams
- New team members onboarding to the project
- External stakeholders requiring system understanding

---

## Project Overview

### What is C4 Model?

The C4 model is a hierarchical approach to visualizing software architecture:
- **Level 1: System Context** - Shows the system and its relationships with users and external systems
- **Level 2: Container** - Shows applications, databases, and webapps within a system
- **Level 3: Component** - Shows components within an application
- **Level 4: Code** - Shows classes and interfaces (not typically modeled in C4)

### Technology Stack

- **LikeC4**: DSL and tooling for C4 model visualization
- **Node.js**: Runtime environment (version 20+ required)
- **TypeScript**: Configuration and custom generators
- **Vite**: Build tool for deployment

### Live Documentation

The architecture can be viewed interactively at: https://hmcts.github.io/cp-c4-architecture/

---

## Project Structure

```
cp-c4-architecture/
├── src/
│   ├── model.c4                          # Root system definition
│   ├── model.people.c4                   # Actor definitions
│   ├── model-external-systems.c4         # External system definitions
│   ├── model.views.c4                   # Main system landscape views
│   ├── _spec.c4                         # LikeC4 specifications
│   │
│   ├── shared-components/                # Shared components subdomain
│   │   ├── model.subdomain.shared-components.c4
│   │   ├── model.shared-components.c4
│   │   └── model.views.shared-components.c4
│   │
│   ├── subdomain-case-administration/   # Case Administration subdomain
│   │   ├── subdomain-case-administration.c4
│   │   ├── product-case-management-system.c4  # Contains progression-service with component details
│   │   ├── product-defence-portal.c4
│   │   ├── product-work-management-system.c4
│   │   └── model.views.case-administration.c4  # Contains progression-service views
│   │
│   ├── subdomain-case-ingestion/        # Case Ingestion subdomain
│   ├── subdomain-court-hearings/        # Court Hearings subdomain
│   ├── subdomain-opami/                 # OPAMI subdomain
│   └── subdomain-scheduling-listing/    # Scheduling and Listing subdomain
│
├── test/                                # Model validation tests
├── .github/                             # GitHub workflows
├── likec4.config.ts                     # LikeC4 configuration
├── package.json                         # Node.js dependencies
├── README.md                            # Quick start guide
├── CHANGELOG.md                         # Change history
└── REFERENCE_MANUAL.md                  # This document
```

### Directory Structure Principles

1. **Subdomains**: Each business subdomain has its own directory
2. **Separation of Concerns**: Models, views, and subdomain definitions are separated
3. **Consistency**: All subdomains follow the same structure pattern
4. **Scalability**: Easy to add new subdomains or components

---

## C4 Model Concepts

### Element Types

#### System
The top-level container representing the entire Common Platform.

```c4
cp = system 'Common Platform' {
    description 'Crime Common Platform'
}
```

#### Subdomain
A logical grouping of related products within the Common Platform.

```c4
case-administration-subdomain = subdomain {
    title 'Case Administration'
    style {
        color pale-yellow
    }
}
```

#### Product
A product or system within a subdomain that delivers business value.

```c4
case-management-system = product {
    title 'Case Management System'
    description 'Manages cases'
}
```

#### Shared Component
A reusable component shared across multiple subdomains.

```c4
staging-system = shared-component {
    title 'Staging System'
    summary 'Receives IDAM events and stages them for processing'
}
```

#### Application
A deployable software application within a product or shared component.

```c4
staging = application {
    title 'Staging'
    technology 'JavaEE + Wildfly'
    summary 'Receives IDAM events via the IDAM Events Consumer'
}
```

#### Component
A logical component within an application.

```c4
command-api = component {
    title 'Command API'
    technology 'Java Component'
    summary 'REST API for receiving IDAM events'
}
```

#### Webapp
A web application user interface.

```c4
listing-ui = webapp {
    title 'Listing UI'
    technology 'Angular'
    summary 'Provides functionality for managing court listings'
}
```

#### Database
A data storage system.

```c4
staging-database = database {
    title 'Staging Database'
    summary 'Stores events and viewstore data'
}
```

#### Actor
A person or role that interacts with the system.

```c4
listing_officer = actor "Listing Officer" "Manages the court's daily schedule"
```

#### External System
A system outside the Common Platform.

```c4
crime-idam = external-system "Crime IDAM" ""
```

### Relationships

Relationships define how elements interact:

```c4
this -> staging-database 'stores events in'
crime-idam -> this 'sends user and group changes to' 'JSON/HTTPS'
this -[auth]-> cp.users-and-groups-system.users-and-groups 'makes authorisation decisions using'
```

**Relationship Types:**
- `->` : Standard relationship
- `-[tag]->` : Tagged relationship (e.g., `-[auth]->`, `-[audit]->`, `-[mi]->`)

**Technology Tags:**
- `'JSON/HTTPS'` : Protocol/format specification
- `'JMS'` : Messaging protocol

---

## File Organization and Naming Conventions

### File Naming Patterns

1. **Subdomain Definition**: `subdomain-{name}.c4`
   - Example: `subdomain-case-administration.c4`

2. **Product Definition**: `product-{name}.c4`
   - Example: `product-case-management-system.c4`

3. **Model Definitions**: `model.{purpose}.c4`
   - Example: `model.shared-components.c4`
   - Example: `model.views.shared-components.c4`

4. **View Definitions**: `model.views.{scope}.c4`
   - Example: `model.views.case-administration.c4`
   - Example: `model.views.shared-components.c4`

### Element Naming Conventions

1. **Subdomains**: `{domain}-subdomain`
   - Example: `case-administration-subdomain`

2. **Products**: `{name}-system` or `{name}`
   - Example: `case-management-system`
   - Example: `hearing-system`

3. **Shared Components**: `{name}-system`
   - Example: `staging-system`
   - Example: `users-and-groups-system`

4. **Applications**: Use descriptive names
   - Example: `staging`, `users-and-groups`, `notification-service`

5. **Components**: Use descriptive, hyphenated names
   - Example: `command-api`, `event-processor`, `viewstore-persistence`

6. **Databases**: `{system}-database`
   - Example: `staging-database`, `notification-database`

### ID Naming

- Use kebab-case (lowercase with hyphens)
- Be descriptive and consistent
- Follow the hierarchy: `cp.{subdomain}.{product}.{application}.{component}`

---

## Architecture Hierarchy

### Hierarchy Levels

```
Common Platform (cp)
├── Subdomains
│   ├── Case Administration
│   │   ├── Case Management System (product)
│   │   │   ├── Applications
│   │   │   │   ├── Components
│   │   │   │   └── Databases
│   │   │   └── Webapps
│   │   ├── Defence Portal (product)
│   │   └── Work Management System (product)
│   │
│   ├── Court Hearings
│   ├── Case Ingestion
│   ├── Scheduling and Listing
│   ├── OPAMI (Operational and Management Information)
│   └── Shared Components
│       ├── Staging System
│       ├── Notify System
│       ├── ID Mapper System
│       ├── Scheduling System
│       ├── UI Notification System
│       ├── Document Generation System
│       ├── Users and Groups System
│       └── Support System
│
├── Actors
└── External Systems
```

### Accessing Elements

Elements are accessed using dot notation:

```c4
cp.shared-components-subdomain.staging-system.staging.command-api
```

**Full Path Structure:**
- `cp` - Root system
- `{subdomain}` - Subdomain name
- `{product}` or `{shared-component}` - Product/component name
- `{application}` - Application name (optional)
- `{component}` - Component name (optional)

---

## Navigating the Architecture

### View Hierarchy

1. **System Landscape** (`index` view)
   - Top-level view showing all subdomains
   - Access: Root view when opening the documentation

2. **Subdomain Overview** (`common-platform-subdomains`)
   - Shows all subdomains and their products
   - Click on a subdomain to see its overview

3. **Product/System Views**
   - **System Context View**: Shows actors, external systems, and high-level relationships
   - **Container View**: Shows applications, databases, and webapps
   - **Component View**: Shows internal component structure

### Navigation Flow

```
System Landscape
    ↓
Subdomain Overview
    ↓
Product/System Overview (if exists)
    ↓
System Context View
    ↓
Container View
    ↓
Component View
```

### Shared Components Navigation

1. From System Landscape, click on **"Shared Components"** gray box
2. View **Shared Components Overview** showing all 10 systems
3. Click any system to see:
   - System Context View
   - Container View
   - Component View (drill-down)

### View Types

#### System Landscape Views
- **Purpose**: High-level overview of the entire platform
- **Location**: `model.views.c4`
- **Examples**: `index`, `common-platform-subdomains`

#### System Context Views
- **Purpose**: Show the system, its users, and external systems
- **Pattern**: `{system}-context`
- **Example**: `staging-system-context`

#### Container Views
- **Purpose**: Show applications, databases, and webapps
- **Pattern**: `{system}-container-view`
- **Example**: `staging-system-container-view`

#### Component Views
- **Purpose**: Show internal component structure
- **Pattern**: `{application}-component-view`
- **Example**: `staging-component-view`

---

## Adding and Modifying Components

### Adding a New Subdomain

1. **Create subdomain directory**:
   ```bash
   mkdir -p src/subdomain-{name}
   ```

2. **Create subdomain definition file** (`subdomain-{name}.c4`):
   ```c4
   model {
       extend cp {
           {name}-subdomain = subdomain {
               title '{Display Name}'
               style {
                   color {color-name}
               }
           }
       }
   }
   ```

3. **Create product files** (`product-{name}.c4`):
   ```c4
   model {
       extend cp.{name}-subdomain {
           {product-name} = product {
               title '{Product Title}'
               description '{Description}'
           }
       }
   }
   ```

4. **Create views file** (`model.views.{name}.c4`):
   ```c4
   views {
       view {product-name}-context of cp.{product-name} {
           title '[System Context] {Product Title}'
           include *
           where
               not (kind is application or kind is database or kind is webapp)
           exclude * -> *
           include * <-> cp.{product-name}
       }
   }
   ```

5. **Update main views** (`model.views.c4`):
   ```c4
   view common-platform-subdomains of cp {
       include
           cp.{name}-subdomain.*
   }
   ```

### Adding a New Shared Component

1. **Edit** `src/shared-components/model.shared-components.c4`:
   ```c4
   model {
       extend cp.shared-components-subdomain {
           {name}-system = shared-component {
               title '{System Title}'
               summary '{Summary}'
               
               {application-name} = application {
                   title '{Application Title}'
                   technology 'JavaEE + Wildfly'
                   summary '{Summary}'
               }
           }
       }
   }
   ```

2. **Add views** in `model.views.shared-components.c4`:
   ```c4
   view {name}-system-context of cp.{name}-system {
       title '[System Context] {System Title}'
       include *
   }
   ```

3. **Update overview view** in `model.views.c4`:
   ```c4
   view shared-components-overview of cp.shared-components-subdomain {
       include
           cp.shared-components-subdomain.{name}-system
   }
   ```

### Adding Components to an Application

1. **Edit the product/shared-component file**:
   ```c4
   {application-name} = application {
       title '{Application Title}'
       
       {component-name} = component {
           title '{Component Title}'
           technology 'Java Component'
           summary '{Summary}'
           
           this -> {other-component}
       }
   }
   ```

### Adding Relationships

```c4
# Application to database
this -> {database-name} 'stores data in'

# Component to component
this -> {other-component} 'calls'

# Application to external system
this -> {external-system} 'sends data to' 'JSON/HTTPS'

# Tagged relationships
this -[auth]-> cp.users-and-groups-system.users-and-groups 'makes authorisation decisions using'
this -[audit]-> cp.audit-system 'sends data to'
this -[mi]-> cp.management-information-system 'sends data to'
```

---

## View Types and Their Purposes

### System Landscape Views

**Purpose**: Provide high-level overview of the entire platform

**Key Views:**
- `index`: Main entry point showing all subdomains
- `common-platform-subdomains`: Detailed subdomain and product view
- `common-platform`: All products and components view

**Pattern:**
```c4
view {name} of cp {
    title '[System Landscape] {Title}'
    include cp, cp.{subdomain}.*
    exclude * <-> *
}
```

### System Context Views

**Purpose**: Show the system, its users (actors), and external systems

**Characteristics:**
- Excludes applications, databases, and webapps
- Shows actors and external systems
- Focuses on high-level relationships

**Pattern:**
```c4
view {system}-context of cp.{system} {
    title '[System Context] {System Title}'
    include *
    where
        not (kind is application or kind is database or kind is webapp)
    exclude * -> *
    include * <-> cp.{system}
    exclude * <-> *
        where kind is audit or kind is mi or kind is auth
}
```

### Container Views

**Purpose**: Show applications, databases, and webapps within a system

**Characteristics:**
- Includes all containers (applications, databases, webapps)
- May include related systems from other subdomains
- Shows container-level relationships

**Pattern:**
```c4
view {system}-container-view of cp.{system} {
    title '[Container View] {System Title}'
    include *
    // Optionally include related systems
    include cp.{other-subdomain}.{other-system}
}
```

### Component Views

**Purpose**: Show internal component structure within an application

**Characteristics:**
- Shows components within a specific application
- Shows component-to-component relationships
- Provides drill-down capability

**Pattern:**
```c4
view {application}-component-view of cp.{system}.{application} {
    title '[Component View] {Application Title}'
    include *
}
```

### Overview Views

**Purpose**: Show all systems within a subdomain

**Pattern:**
```c4
view {subdomain}-overview of cp.{subdomain} {
    title '[System Landscape] {Subdomain Title}'
    include cp.{subdomain}.*
    exclude * <-> *
}
```

---

## Best Practices

### Model Definition

1. **Be Descriptive**: Use clear, descriptive titles and summaries
2. **Consistent Naming**: Follow established naming conventions
3. **Complete Information**: Include technology, summary, and relationships
4. **Avoid Duplication**: Don't define the same element twice
5. **Use Relationships**: Document all important relationships

### View Definition

1. **Appropriate Level**: Match view type to the level of detail needed
2. **Filtering**: Use `where` clauses to filter appropriately
3. **Styling**: Use consistent styling for secondary elements
4. **Exclusions**: Exclude relationships that add noise (e.g., audit, MI)
5. **Include Patterns**: Be explicit about what to include

### Component Structure

1. **Logical Grouping**: Group related components together
2. **Clear Boundaries**: Define clear component boundaries
3. **Technology Tags**: Include technology information
4. **Summary Text**: Provide meaningful summaries
5. **Relationships**: Document component interactions

### Relationship Documentation

1. **Descriptive Labels**: Use clear relationship descriptions
2. **Technology Tags**: Include protocol/format when relevant
3. **Tagged Relationships**: Use tags for special relationships (auth, audit, MI)
4. **Direction**: Ensure relationships point in the correct direction
5. **Completeness**: Document all important relationships

### File Organization

1. **One Concept Per File**: Keep related definitions together
2. **Logical Grouping**: Group by subdomain or purpose
3. **Consistent Structure**: Follow established patterns
4. **Separation**: Separate models from views
5. **Naming**: Use clear, consistent file names

### Maintenance

1. **Keep Updated**: Update architecture as system evolves
2. **Version Control**: Commit changes regularly
3. **Documentation**: Update this manual when patterns change
4. **Validation**: Run tests to validate model
5. **Review**: Review changes with team

---

## Examples and Patterns

### CQRS Application Example: Case Progression Service

The Case Progression Service demonstrates a CQRS (Command Query Responsibility Segregation) architecture pattern with event-driven components:

**Application Definition** (in `product-case-management-system.c4`):
```c4
progression-service = application {
    title 'Case Progression Service'
    technology 'JavaEE + Wildfly'
    summary 'Manages case progression, hearings, documents, and notifications for prosecution cases'
    this -> progression-database
    this -> progression-eventprocessorstore-database
    this -> cp.notify-system.notification-notify 'sends email and letter notifications' 'JSON/HTTPS'
    this -> cp.id-mapper-system.system-id-mapper 'creates and queries ID mappings for notifications, materials, and documents' 'JSON/HTTPS'
    this -> cp.reference-data-system.reference-data 'queries reference data' 'JSON/HTTPS'

    // Command Side (Write)
    command-api = component {
        title 'Command API'
        technology 'Java Component'
        summary 'REST API for case progression commands'
        this -> command-handler
    }

    command-handler = component {
        title 'Command Handler'
        technology 'Java Component'
        summary 'Processes progression commands and triggers domain events'
        this -> event-processor
    }

    // Query Side (Read)
    query-api = component {
        title 'Query API'
        technology 'Java Component'
        summary 'REST API for querying case progression data'
        this -> query-view
    }

    query-view = component {
        title 'Query View'
        technology 'Java Component'
        summary 'Provides read models for case progression queries'
        this -> viewstore-persistence
    }

    // Event Processing
    event-listener = component {
        title 'Event Listener'
        technology 'Java Component'
        summary 'Listens to events from other systems'
        this -> event-processor
    }

    event-processor = component {
        title 'Event Processor'
        technology 'Java Component'
        summary 'Processes events and updates the viewstore, handles notifications and ID mappings'
        this -> viewstore-persistence
        this -> event-indexer
    }

    event-indexer = component {
        title 'Event Indexer'
        technology 'Java Component'
        summary 'Indexes events for search functionality'
        this -> viewstore-persistence
    }

    viewstore-persistence = component {
        title 'View Store Persistence'
        technology 'Java Component'
        summary 'CRUD Repository for progression viewstore data'
        this -> progression-database
    }
}
```

**Key Patterns Demonstrated:**
- **CQRS**: Separate command (write) and query (read) paths
- **Event-Driven**: Event listener and processor for asynchronous updates
- **Multiple Databases**: Separate databases for event store and viewstore
- **Shared Component Integration**: Relationships to notification, ID mapper, and reference data systems

### Complete Subdomain Example

**Subdomain Definition** (`subdomain-example.c4`):
```c4
model {
    extend cp {
        example-subdomain = subdomain {
            title 'Example Subdomain'
            style {
                color pale-blue
            }
        }
    }
}
```

**Product Definition** (`product-example-system.c4`):
```c4
model {
    extend cp.example-subdomain {
        example-system = product {
            title 'Example System'
            description 'An example system for demonstration'
            
            example-ui = webapp {
                title 'Example UI'
                technology 'Angular'
                summary 'User interface for the example system'
                
                this -> example-service 'makes API calls to'
            }
            
            example-service = application {
                title 'Example Service'
                technology 'JavaEE + Wildfly'
                summary 'Main application service'
                this -> example-database
                
                this -[auth]-> cp.users-and-groups-system.users-and-groups 'makes authorisation decisions using'
                this -[audit]-> cp.audit-system 'sends data to'
                
                command-api = component {
                    title 'Command API'
                    technology 'Java Component'
                    summary 'REST API for commands'
                    
                    this -> command-handler
                }
                
                command-handler = component {
                    title 'Command Handler'
                    technology 'Java Component'
                    summary 'Processes commands'
                    
                    this -> event-processor
                }
                
                event-processor = component {
                    title 'Event Processor'
                    technology 'Java Component'
                    summary 'Processes events'
                    
                    this -> viewstore-persistence
                }
                
                viewstore-persistence = component {
                    title 'View Store Persistence'
                    technology 'Java Component'
                    summary 'CRUD Repository'
                    
                    this -> example-database
                }
            }
            
            example-database = database {
                title 'Example Database'
                summary 'Stores application data'
            }
        }
    }
}
```

**Views** (`model.views.example.c4`):
```c4
views {
    view example-system-context of cp.example-system {
        title '[System Context] Example System'
        include *
        where
            not (kind is application or kind is database or kind is webapp)
        include cp.shared-components-subdomain._
        exclude * -> *
        include * <-> cp.example-system
        exclude * <-> *
            where kind is audit or kind is mi or kind is auth
        
        style cp.shared-components-subdomain.* {
            color secondary
        }
    }
    
    view example-system-container-view of cp.example-system {
        title '[Container View] Example System'
        include *
    }
    
    view example-service-component-view of cp.example-system.example-service {
        title '[Component View] Example Service'
        include *
    }
}
```

### Shared Component Pattern

```c4
model {
    extend cp.shared-components-subdomain {
        example-shared-system = shared-component {
            title 'Example Shared System'
            summary 'Provides shared functionality'
            
            example-service = application {
                title 'Example Service'
                technology 'JavaEE + Wildfly'
                summary 'Shared service application'
                this -> example-database
                
                this -[auth]-> cp.users-and-groups-system.users-and-groups 'makes authorisation decisions using'
                
                api = component {
                    title 'API'
                    technology 'Java Component'
                    summary 'REST API'
                    
                    this -> persistence
                }
                
                persistence = component {
                    title 'Persistence'
                    technology 'Java Component'
                    summary 'Data persistence layer'
                    
                    this -> example-database
                }
            }
            
            example-database = database {
                title 'Example Database'
                summary 'Stores data'
            }
        }
    }
}
```

### Relationship Patterns

**Standard Relationship:**
```c4
this -> database-name 'stores data in'
```

**Relationship with Technology:**
```c4
this -> external-system 'sends data to' 'JSON/HTTPS'
```

**Tagged Relationship:**
```c4
this -[auth]-> cp.users-and-groups-system.users-and-groups 'makes authorisation decisions using'
this -[audit]-> cp.audit-system 'sends data to'
this -[mi]-> cp.management-information-system 'sends data to'
```

**Cross-Subdomain Relationship:**
```c4
this -> cp.{other-subdomain}.{system} 'interacts with'
```

---

## Development Workflow

### Local Development

1. **Start Development Server**:
   ```bash
   npm start
   # or
   npx likec4 start
   ```

2. **Open Browser**: Navigate to `http://localhost:5173/`

3. **Make Changes**: Edit `.c4` files

4. **View Changes**: Browser auto-reloads on file changes

5. **Validate Model**:
   ```bash
   npm test
   ```

### Adding New Components

1. **Plan**: Determine where the component fits in the hierarchy
2. **Create/Edit Files**: Add definitions following patterns
3. **Add Views**: Create appropriate views
4. **Test**: Validate model and check views
5. **Commit**: Commit changes with descriptive messages

### Viewing Specific Views

1. **In Browser**: Navigate through the interactive interface
2. **Direct URL**: Access views via URL pattern
3. **Search**: Use search functionality to find elements
4. **Navigation**: Click elements to drill down

### Exporting Diagrams

```bash
# Export to PNG
npx likec4 export png -o png

# Export relationships to CSV
npm run generate:relationships-csv
```

### Model Validation

```bash
# Run validation tests
npm test

# Check for errors
npx likec4 validate
```

---

## Troubleshooting

### Common Issues

#### Views Not Showing

**Problem**: Views don't appear or show empty diagrams

**Solutions**:
1. Check file syntax - ensure proper C4 DSL syntax
2. Verify includes - ensure elements are included in views
3. Check element IDs - ensure IDs match exactly
4. Restart server - restart LikeC4 development server
5. Clear cache - hard refresh browser (Ctrl+Shift+R)

#### Navigation Not Working

**Problem**: Clicking elements doesn't navigate to views

**Solutions**:
1. Verify view exists - ensure view is defined
2. Check view target - ensure view is "of" the correct element
3. Check file location - ensure view file is in correct location
4. Restart server - restart LikeC4 development server

#### Elements Not Appearing

**Problem**: Elements don't show in views

**Solutions**:
1. Check includes - verify elements are included
2. Check filters - review `where` clauses
3. Verify hierarchy - ensure element is in correct subdomain
4. Check syntax - ensure proper model definition

#### Relationship Errors

**Problem**: Relationships show errors or don't display

**Solutions**:
1. Verify IDs - ensure source and target IDs are correct
2. Check syntax - ensure proper relationship syntax
3. Verify elements exist - ensure both elements are defined
4. Check scope - ensure elements are in scope

### Debugging Tips

1. **Check Console**: Look for errors in browser console
2. **Validate Model**: Run `npm test` to check for issues
3. **Incremental Changes**: Make small changes and test
4. **Compare Patterns**: Compare with working examples
5. **Check Logs**: Review LikeC4 server logs

### Getting Help

1. **Documentation**: Review LikeC4 documentation
2. **Examples**: Check existing subdomains for patterns
3. **Team**: Consult with team members
4. **Issues**: Check GitHub issues for similar problems

---

## Glossary

### Terms

- **Actor**: A person or role that interacts with the system
- **Application**: A deployable software application
- **Component**: A logical component within an application
- **Container**: Applications, databases, and webapps (C4 terminology)
- **Database**: A data storage system
- **External System**: A system outside the Common Platform
- **Product**: A product or system that delivers business value
- **Shared Component**: A reusable component shared across subdomains
- **Subdomain**: A logical grouping of related products
- **System**: The top-level container (Common Platform)
- **View**: A diagram showing a specific perspective of the architecture
- **Webapp**: A web application user interface

### Abbreviations

- **C4**: Context, Containers, Components, Code (modeling approach)
- **CP**: Common Platform
- **IDAM**: Identity and Access Management
- **MI**: Management Information
- **OPAMI**: Operational and Management Information
- **SPI**: Standard Prosecutor Interface
- **CPPI**: Common Platform Prosecutor Interface

### LikeC4 Specific

- **DSL**: Domain Specific Language
- **Element**: Any model entity (system, subdomain, product, etc.)
- **Relationship**: Connection between elements
- **View**: A diagram definition
- **Include/Exclude**: View filtering mechanisms

---

## Appendix

### Color Palette

Subdomains use the following color scheme:
- **Case Administration**: `pale-yellow`
- **Court Hearings**: `pale-purple`
- **Case Ingestion**: (default)
- **Scheduling and Listing**: `pale-green`
- **OPAMI**: (default)
- **Shared Components**: `pale-grey`

### Technology Stack References

Common technologies used:
- **JavaEE + Wildfly**: Main application server
- **Angular**: Frontend framework
- **Java Component**: Java-based component
- **PostgreSQL**: Database (implied)
- **JSON/HTTPS**: API protocol
- **JMS**: Messaging protocol

### File Locations Reference

- **Root Models**: `src/model*.c4`
- **Subdomain Definitions**: `src/subdomain-*/subdomain-*.c4`
- **Product Definitions**: `src/subdomain-*/product-*.c4`
- **View Definitions**: `src/subdomain-*/model.views.*.c4`
- **Shared Components**: `src/shared-components/*.c4`

---

## Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history and changes.

---

## Additional Resources

- [LikeC4 Documentation](https://likec4.dev/)
- [C4 Model](https://c4model.com/)
- [Project README](./README.md)
- [Changelog](./CHANGELOG.md)

---

**Last Updated**: 2024
**Maintained By**: Common Platform Architecture Team

