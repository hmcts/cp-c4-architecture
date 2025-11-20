# Changelog

All notable changes to the Common Platform C4 Architecture project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Case Progression Service Architecture
- **Complete Progression Service Model Expansion**
  - Expanded `progression-service` application in `product-case-management-system.c4` with detailed component-level architecture
  - Added component-level detail for Case Progression Service:
    - **Command API**: REST API for case progression commands
    - **Command Handler**: Processes progression commands and triggers domain events
    - **Query API**: REST API for querying case progression data
    - **Query View**: Provides read models for case progression queries
    - **Event Listener**: Listens to events from other systems
    - **Event Processor**: Processes events and updates the viewstore, handles notifications and ID mappings
    - **Event Indexer**: Indexes events for search functionality
    - **View Store Persistence**: CRUD Repository for progression viewstore data
  - Added two databases:
    - **Progression Database**: Stores events, aggregates, and viewstore data
    - **Progression Event Processor Store Database**: Stores event processor state and checkpoint data
  - Documented relationships to shared components:
    - **Notification Notify System**: Sends email and letter notifications
    - **ID Mapper System**: Creates and queries ID mappings for notifications, materials, and documents
    - **Reference Data System**: Queries reference data

- **Comprehensive View Definitions for Progression Service**
  - Created system context, container, and component views in `model.views.case-administration.c4`:
    - **System Context View**: Shows progression-service with relationships to shared components (notification-notify, system-id-mapper, reference-data) and prosecutor-ui
    - **Container View**: Shows internal structure with all components, databases, and external dependencies
    - **Component View**: Shows detailed component-level relationships

#### Shared Components Architecture
- **Complete Shared Components Model Expansion**
  - Expanded `model.shared-components.c4` with detailed component-level architecture for all shared component systems
  - Added component-level detail for 8 shared component services:
    - **Staging System**: Added components (command-api, command-handler, event-processor, viewstore-persistence), database, and relationships to IDAM and users-groups
    - **System Scheduling**: Added components (command-api, command-handler, event-processor, scheduler, viewstore-persistence) and database
    - **UI Notification System**: Added components (command-api, query-api, event-processor, subscription-manager, viewstore-persistence) and database
    - **Notification Notify System**: Added components (command-api, event-processor, gov-notify-client, office365-client, viewstore-persistence), database, and external systems (GOV.UK Notify, Office 365)
    - **ID Mapper System**: Added components (api, persistence) and database
    - **Users and Groups System**: Enhanced with component details (command-api, query-api, event-processor, cache, viewstore-persistence)
    - **Document Generation System**: Added components (command-api, query-api, docmosis-service, validation, event-processor, viewstore-persistence) and database
    - **Support System**: Added components (command-api, query-api, event-processor, viewstore-persistence) and database

- **Comprehensive View Definitions**
  - Created system context, container, and component views for all shared component systems in `model.views.shared-components.c4`:
    - Staging System views (system context, container, component)
    - System Scheduling views (system context, container, component)
    - UI Notification System views (system context, container, component)
    - Notification Notify System views (system context, container, component)
    - ID Mapper System views (system context, container, component)
    - Users and Groups System views (enhanced existing, added component view)
    - Document Generation System views (system context, container, component)
    - Support System views (system context, container, component)
    - Reference Data System views (existing, maintained)

- **Navigation and Overview**
  - Added `shared-components-overview` view in `model.views.c4` for navigation to all shared component systems
  - Updated `common-platform-subdomains` view to include `cp.shared-components-subdomain.*` to display all shared components in the system landscape
  - Fixed navigation from the Shared Components subdomain box to show all 10 shared component systems

- **External Systems Integration**
  - Added GOV.UK Notify external system definition in `model-external-systems.c4` (moved from notify-system to appear outside NOTIFY SYSTEM boundary)
  - Added Office 365 external system definition in `model-external-systems.c4` (moved from notify-system to appear outside NOTIFY SYSTEM boundary)
  - Documented relationships to IDAM (Crime IDAM) for Staging and Users and Groups services
  - Added cross-subdomain relationships with proper styling

- **Court Hearings Subdomain Enhancements**
  - Added `hearing-nows` application to `hearing-system` product
  - Documented relationships from hearing-nows to:
    - **System ID Mapper**: Creates and queries ID mappings for notifications, materials, and documents
    - **Users and Groups System**: Queries groups with organisation
    - **Document Generation System**: Generates NOW documents
    - **Notification Notify System**: Sends email and letter notifications

- **Component Mapping**
  - Mapped Maven modules to logical C4 components:
    - `{service}-command` → `command-api` component
    - `{service}-event` → `event-processor` component
    - `{service}-viewstore` → `viewstore-persistence` component
    - `{service}-query` → `query-api` component
    - `{service}-domain` → business logic components
    - Special modules (e.g., `docmosis-service`, `azure`) → specific components

### Changed

- **System Landscape View**
  - Updated `common-platform-subdomains` view to include shared components subdomain contents (`cp.shared-components-subdomain.*`)
  - Enhanced visibility of shared components in the main system landscape diagram

- **Users and Groups System**
  - Removed duplicate staging application definition (moved to separate staging-system)
  - Updated staging reference in users-and-groups-system to point to `cp.staging-system.staging`
  - Enhanced users-and-groups application with detailed component structure

### Fixed

- **Navigation Issues**
  - Fixed Shared Components subdomain navigation to properly display all shared component systems
  - Resolved duplicate view definition for shared-components-overview
  - Fixed subdomain reference in staging system (changed from `cp.users-and-groups-subdomain` to `cp.users-and-groups-system`)

- **Model Consistency**
  - Fixed typo in listing-ui summary ("coute listings" → "court listings")
  - Ensured consistent relationship labeling across all shared components
  - Standardized component naming conventions

- **Notification Notify System Context View**
  - Fixed external systems (GOV.UK Notify, Office 365) to appear outside NOTIFY SYSTEM boundary as gray boxes
  - Moved GOV.UK Notify and Office 365 from `notify-system` shared-component to `model-external-systems.c4`
  - Updated notification-notify application relationships to reference external systems from root level (`cp.gov-uk-notify`, `cp.office365`)
  - Updated notification-notify-context view to explicitly include external systems and show relationships from notification-notify application
  - Added missing relationship from hearing-nows to notification-notify system

- **View Clutter Reduction**
  - Removed unnecessary subdomain includes from shared component context views that had no direct relationships
  - Updated views to only include subdomains/systems that actually have documented relationships

### Technical Details

- **Files Modified**:
  - `src/shared-components/model.shared-components.c4` - Expanded with component-level details
  - `src/shared-components/model.views.shared-components.c4` - Added comprehensive views for all systems, fixed external systems display
  - `src/model.views.c4` - Added shared-components-overview view and updated system landscape
  - `src/model-external-systems.c4` - Added GOV.UK Notify and Office 365 external systems
  - `src/subdomain-scheduling-listing/product-scheduling-and-listing-system.c4` - Fixed typo
  - `src/subdomain-case-administration/product-case-management-system.c4` - Expanded progression-service with component-level details
  - `src/subdomain-case-administration/model.views.case-administration.c4` - Added progression-service views
  - `src/subdomain-court-hearings/product-hearing-system.c4` - Added hearing-nows application with relationships

- **Architecture Patterns**:
  - Followed C4 model conventions (System Context → Container → Component hierarchy)
  - Maintained consistency with existing subdomain patterns (e.g., scheduling-and-listing)
  - Used descriptive relationship labels with technology tags where appropriate
  - Implemented proper include/exclude patterns for view filtering

- **View Structure**:
  - System Context Views: Show actors, external systems, and high-level relationships
  - Container Views: Show applications, databases, and webapps within systems
  - Component Views: Show internal component structure with drill-down capability

## Notes

- All shared component systems now have complete drill-down capability from System Landscape → Overview → System Context → Container → Component views
- External systems (GOV.UK Notify, Office 365) are properly documented and linked, appearing outside system boundaries as gray boxes
- Cross-subdomain relationships are maintained with appropriate styling
- The architecture follows the same patterns as other subdomains for consistency
- Case Progression Service now has complete C4 documentation with component-level detail and comprehensive views
- Progression Service demonstrates CQRS architecture pattern with separate command and query components
- Hearing NOWs application is now fully documented with relationships to shared components (ID Mapper, Users and Groups, Document Generation, Notification Notify)
- Notification Notify System Context view correctly shows external systems (GOV.UK Notify, Office 365) outside the NOTIFY SYSTEM boundary with proper relationships

