# Common Platform C4 Architecture - User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding the Interface](#understanding-the-interface)
3. [Navigation Basics](#navigation-basics)
4. [Exploring the Architecture](#exploring-the-architecture)
5. [Understanding Diagram Types](#understanding-diagram-types)
6. [Common Navigation Scenarios](#common-navigation-scenarios)
7. [Tips and Tricks](#tips-and-tricks)
8. [Troubleshooting](#troubleshooting)
9. [Quick Reference](#quick-reference)

---

## Getting Started

### Accessing the Documentation

The Common Platform C4 Architecture documentation is available in two ways:

1. **Online (Recommended)**: https://hmcts.github.io/cp-c4-architecture/
2. **Local Development**: Run `npm start` and access `http://localhost:5173/`

### First Steps

1. **Open the Documentation**: Navigate to the online version or start the local server
2. **Start with the System Landscape**: The main page shows the overall system structure
3. **Familiarize Yourself**: Take a moment to understand the layout and controls
4. **Begin Exploring**: Click on subdomains or systems to drill down

### What You'll See

When you first open the documentation, you'll see:
- **System Landscape View**: A high-level diagram showing all subdomains
- **Navigation Panel**: On the left (if visible) showing available views
- **Toolbar**: At the top with search, export, and other controls
- **Interactive Elements**: Clickable boxes representing systems and components

---

## Understanding the Interface

### Main Components

#### 1. Diagram Area
The central area where architecture diagrams are displayed. This is where you'll spend most of your time exploring.

**Features:**
- **Zoom**: Use mouse wheel or pinch gesture to zoom in/out
- **Pan**: Click and drag to move around the diagram
- **Click Elements**: Click any box to navigate or see details

#### 2. Navigation Bar (Top)
Located at the top of the page, provides:
- **View Title**: Current view name
- **Navigation Arrows**: Move between views
- **Search Icon**: Search for specific systems or components
- **Share Button**: Share current view
- **Export Button**: Export diagram as image
- **View Counter**: Shows current view number (e.g., "2/14")

#### 3. Side Panel (if visible)
Shows:
- **View List**: All available views
- **Element Details**: Information about selected elements
- **Relationships**: Connections to/from selected elements

#### 4. Element Information
When you hover over or click an element, you may see:
- **Title**: Name of the system/component
- **Description**: Summary of what it does
- **Technology**: Technology stack used
- **Relationships**: Connections to other elements

### Color Coding

The diagrams use colors to distinguish different types of elements:

- **Blue Boxes**: Products and systems
- **Gray Boxes**: Subdomains (logical groupings)
- **Dashed Borders**: Boundaries (subdomains, systems)
- **Colored Dashed Borders**: Different subdomains use different colors:
  - **Green**: Scheduling and Listing
  - **Yellow**: Case Administration
  - **Purple**: Court Hearings
  - **Gray**: Shared Components
  - **Red**: Operational and Management Information

### Element Types

You'll encounter different types of elements:

- **Subdomain**: A logical grouping (shown as a box with dashed border)
- **Product/System**: A complete system (blue box)
- **Application**: A deployable application (within a system)
- **Component**: Internal component (within an application)
- **Database**: Data storage (cylinder icon)
- **Webapp**: Web application (browser icon)
- **Actor**: Person or role (person icon)
- **External System**: System outside Common Platform

---

## Navigation Basics

### Clicking Elements

**Single Click**: 
- On a **subdomain**: Navigate to subdomain overview
- On a **system/product**: Navigate to system context view
- On an **application**: Navigate to container or component view
- On a **component**: Show component details

**Double Click**: 
- Zoom to fit the element
- Focus on that element

### Navigation Paths

The documentation follows a hierarchical structure:

```
System Landscape (Top Level)
    ↓
Subdomain Overview
    ↓
System/Product Overview
    ↓
System Context View
    ↓
Container View
    ↓
Component View (Deepest Level)
```

### Using the Back Button

- **Browser Back**: Use browser back button to return to previous view
- **Navigation Arrows**: Use left/right arrows in toolbar
- **Breadcrumbs**: Some views show breadcrumb navigation

### Search Functionality

1. **Click Search Icon**: In the top navigation bar
2. **Type Search Term**: Enter system name, component name, or keyword
3. **Select Result**: Click on search result to navigate
4. **Clear Search**: Click X or outside search box

**Search Tips:**
- Search is case-insensitive
- Partial matches work
- Search across all views and elements

---

## Exploring the Architecture

### Starting Your Exploration

#### Option 1: Top-Down Approach (Recommended for New Users)

1. **Start at System Landscape**
   - View: "Common Platform Subdomains and Products"
   - See all subdomains at once
   - Understand the big picture

2. **Choose a Subdomain**
   - Click on a subdomain box (e.g., "Case Administration")
   - See all products/systems in that subdomain

3. **Select a System**
   - Click on a specific system (e.g., "Case Management System")
   - View the System Context diagram

4. **Drill Down**
   - Click "Container View" to see applications
   - Click "Component View" to see internal structure

#### Option 2: Search-First Approach (For Specific Information)

1. **Use Search**
   - Search for a specific system or component
   - Navigate directly to relevant views

2. **Explore from There**
   - Use navigation to see related systems
   - Follow relationships to understand connections

### Exploring Subdomains

#### Case Administration Subdomain

**What it contains:**
- Case Management System
  - **Case Progression Service**: Manages case progression, hearings, documents, and notifications
  - Subscriptions Service
  - SJP Service
  - Prosecution Case File Service
  - Assignment Service
  - Application Court Orders Service
- Defence Portal
- Work Management System

**How to explore:**
1. Click "Case Administration" subdomain box
2. See all three systems
3. Click "Case Management System" to see all applications
4. **To explore Case Progression Service:**
   - Click on "Case Progression Service" application
   - Navigate through three views:
     - **System Context View**: Shows relationships to shared components (notification-notify, system-id-mapper, reference-data) and prosecutor-ui
     - **Container View**: Shows all components, databases, and external dependencies
     - **Component View**: Shows detailed component-level relationships
5. Navigate through System Context → Container → Component views for other systems

#### Court Hearings Subdomain

**What it contains:**
- Hearing System
- Online Plea
- Results Distribution System

**How to explore:**
1. Click "Court Hearings" subdomain box
2. Select a system of interest
3. Explore relationships with other subdomains

#### Scheduling and Listing Subdomain

**What it contains:**
- Scheduling and Listing System

**How to explore:**
1. Click "Scheduling and Listing" subdomain box
2. View the system structure
3. See relationships with Court Hearings and Case Administration

#### Case Ingestion Subdomain

**What it contains:**
- Standard Prosecutor Interface (SPI)
- Common Platform Prosecutor Interface (CPPI)

**How to explore:**
1. Click "Case and Material Ingestion" subdomain box
2. Understand how cases enter the system
3. See connections to Case Administration

#### Operational and Management Information (OPAMI) Subdomain

**What it contains:**
- Management Information System
- Audit System

**How to explore:**
1. Click "Operational and Management Information" subdomain box
2. Understand operational systems
3. See how they connect to other subdomains

### Exploring Shared Components

**What are Shared Components?**

Shared Components are reusable systems used across multiple subdomains. They provide common functionality like:
- User management
- Notifications
- Document generation
- Scheduling
- ID mapping

**How to explore:**

1. **Find Shared Components**
   - In System Landscape, look for gray box labeled "Shared Components"
   - Located at the bottom center of the diagram

2. **Click to Open Overview**
   - Click the "Shared Components" box
   - See all 10 shared component systems:
     - Staging System
     - Notify System
     - ID Mapper System
     - Scheduling System
     - UI Notification System
     - Document Generation System
     - Users and Groups System
     - Support System
     - Reference Data System
     - System Announcement System

3. **Select a System**
   - Click any shared component system
   - Navigate through available views:
     - **System Context View**: Shows who uses it and external dependencies
     - **Container View**: Shows applications and databases
     - **Component View**: Shows internal component structure

4. **Understand Relationships**
   - See which subdomains use each shared component
   - Understand dependencies between systems
   - Follow relationship lines to see connections

**Example: Exploring Users and Groups System**

1. Click "Shared Components" → "Users and Groups System"
2. **System Context View** shows:
   - Which subdomains use it (for authentication)
   - External systems (IDAM)
   - Actors who interact with it
3. **Container View** shows:
   - Users and Groups application
   - Manage Permissions UI
   - Databases
   - IDAM Events Consumer
   - Staging application
4. **Component View** shows:
   - Command API
   - Query API
   - Event Processor
   - Cache
   - View Store Persistence

---

## Understanding Diagram Types

### System Landscape Diagrams

**Purpose**: High-level overview of the entire platform

**What you see:**
- All subdomains as colored boxes
- Products/systems within subdomains
- High-level relationships

**When to use:**
- Getting oriented
- Understanding overall structure
- Finding where to explore next

**Example Views:**
- "Common Platform Subdomains and Products"
- "Common Platform Products and Components"

### System Context Diagrams

**Purpose**: Shows a system, its users, and external systems

**What you see:**
- The system in the center
- Actors (people/roles) who use it
- External systems it interacts with
- Other subdomains it connects to

**What you DON'T see:**
- Internal applications
- Databases
- Components

**When to use:**
- Understanding who uses a system
- Seeing external dependencies
- Understanding high-level interactions

**Example:**
- "System Context: Case Management System"
- Shows: Defendants, Court Staff, External Systems (Libra, etc.)

### Container Diagrams

**Purpose**: Shows applications, databases, and webapps within a system

**What you see:**
- Applications (deployable units)
- Databases (data storage)
- Webapps (user interfaces)
- How they connect to each other

**What you DON'T see:**
- Internal components
- Detailed implementation

**When to use:**
- Understanding system architecture
- Seeing what applications exist
- Understanding data flow between containers

**Example:**
- "Container View: Case Management System"
- Shows: Prosecution Case File Service, Subscriptions Service, Databases, etc.

### Component Diagrams

**Purpose**: Shows internal component structure within an application

**What you see:**
- Components within an application
- Component-to-component relationships
- How components interact

**What you DON'T see:**
- Other applications
- External systems (usually)

**When to use:**
- Understanding application internals
- Seeing component interactions
- Detailed technical understanding

**Example:**
- "Component View: Staging Service"
- Shows: Command API, Command Handler, Event Processor, View Store Persistence

### Overview Diagrams

**Purpose**: Shows all systems within a subdomain or category

**What you see:**
- All systems in a subdomain
- Grouped together for easy navigation

**When to use:**
- Finding systems in a subdomain
- Understanding subdomain scope
- Quick navigation

**Example:**
- "Shared Components Overview"
- Shows all 10 shared component systems

---

## Common Navigation Scenarios

### Scenario 1: "I want to understand how cases are managed"

**Path:**
1. Start at System Landscape
2. Click "Case Administration" subdomain
3. Click "Case Management System"
4. View System Context to see who uses it
5. View Container View to see applications
6. Click on specific applications to see components

**What you'll learn:**
- Who uses the case management system
- What applications handle cases
- How cases flow through the system
- What external systems are involved

### Scenario 2: "I need to understand user authentication"

**Path:**
1. Start at System Landscape
2. Click "Shared Components"
3. Click "Users and Groups System"
4. View System Context to see dependencies
5. View Container View to see architecture
6. View Component View to see implementation

**What you'll learn:**
- How authentication works
- Which systems use it
- How it connects to IDAM
- Internal component structure

### Scenario 3: "I want to see how hearings are scheduled"

**Path:**
1. Start at System Landscape
2. Click "Scheduling and Listing" subdomain
3. Click "Scheduling and Listing System"
4. View System Context to see actors (Listing Officers, etc.)
5. View Container View to see applications
6. Follow relationships to Court Hearings subdomain

**What you'll learn:**
- Who manages scheduling
- What applications handle scheduling
- How it connects to hearings
- Integration points

### Scenario 4: "I need to find where notifications are sent"

**Path:**
1. Use Search: Type "notification"
2. Select "Notification Notify" or "UI Notification System"
3. View System Context to see what uses it
4. View Container View to see architecture
5. Follow relationships to see which systems send notifications

**What you'll learn:**
- Two notification systems (UI and Email/Letter)
- Which systems use notifications
- How notifications are delivered
- External services (GOV.UK Notify, Office 365)

### Scenario 5: "I want to understand the end-to-end case flow"

**Path:**
1. Start at "Case Ingestion" subdomain
2. View SPI/CPPI systems (case entry)
3. Navigate to "Case Administration" → "Case Management System"
4. Follow relationships to "Scheduling and Listing"
5. Follow to "Court Hearings"
6. See how results flow back

**What you'll learn:**
- Complete case lifecycle
- How cases move between subdomains
- Integration points
- Data flow

### Scenario 6: "I need to find a specific component"

**Path:**
1. Use Search function
2. Type component name (e.g., "command-api")
3. Select from results
4. Navigate to Component View
5. See relationships and context

**What you'll learn:**
- Where the component is located
- What it does
- What it connects to
- How it fits in the architecture

---

## Tips and Tricks

### Efficient Navigation

1. **Use Search First**: If you know what you're looking for, search is fastest
2. **Follow Relationships**: Click on relationship lines to see connected systems
3. **Use Browser Back**: Quick way to return to previous view
4. **Bookmark Views**: Bookmark important views in your browser
5. **Zoom Out**: Zoom out to see the big picture, then zoom in for details

### Understanding Relationships

**Relationship Lines Show:**
- **Direction**: Arrow shows direction of interaction
- **Type**: Label describes the relationship
- **Technology**: Sometimes shows protocol (JSON/HTTPS, JMS)

**Special Relationship Tags:**
- **-[auth]->**: Authentication relationship
- **-[audit]->**: Audit logging relationship
- **-[mi]->**: Management Information relationship

**Following Relationships:**
- Click on a relationship line to highlight it
- Follow the line to see what it connects
- Use this to understand dependencies

### Zooming and Panning

**Zoom Controls:**
- **Mouse Wheel**: Scroll to zoom in/out
- **Pinch Gesture**: On touch devices
- **Zoom Buttons**: If available in toolbar
- **Double Click**: Zoom to fit element

**Panning:**
- **Click and Drag**: Move around the diagram
- **Arrow Keys**: Some views support arrow key navigation

### Viewing Element Details

**Hover:**
- Hover over elements to see quick info
- Tooltip shows title and summary

**Click:**
- Click element to see full details
- May show in side panel or popup
- Shows relationships

**Right-Click (if available):**
- Context menu with options
- Navigate to related views
- Export element information

### Exporting Diagrams

**Export Options:**
1. Click "Export" button in toolbar
2. Choose format (PNG, SVG, etc.)
3. Save to your computer

**Use Cases:**
- Including in presentations
- Sharing with team
- Documentation purposes
- Printing

### Keyboard Shortcuts

**Common Shortcuts:**
- **Ctrl/Cmd + F**: Search
- **Ctrl/Cmd + +/-**: Zoom
- **Arrow Keys**: Navigate (in some views)
- **Esc**: Close dialogs/panels

### Reading Diagrams Effectively

1. **Start with Title**: Understand what the diagram shows
2. **Look for Central Element**: Usually the main system
3. **Follow Relationships**: See what connects to what
4. **Check Colors**: Understand color coding
5. **Read Labels**: Relationship labels explain interactions
6. **Note Technology**: Technology tags show how things connect

### Finding Related Systems

**Methods:**
1. **Follow Relationships**: Click relationship lines
2. **Use Search**: Search for related terms
3. **Check Subdomain**: Other systems in same subdomain
4. **View System Context**: See what else connects
5. **Check Shared Components**: See if shared services are used

---

## Troubleshooting

### Diagram Not Loading

**Symptoms**: Blank page or error message

**Solutions:**
1. **Refresh Page**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
2. **Check Internet**: Ensure connection is working
3. **Clear Cache**: Clear browser cache
4. **Try Different Browser**: Switch browsers
5. **Check URL**: Ensure correct URL

### Can't Find a System

**Symptoms**: System not visible in diagram

**Solutions:**
1. **Use Search**: Search for the system name
2. **Check Subdomain**: System might be in different subdomain
3. **Zoom Out**: System might be off-screen
4. **Check Filters**: View might be filtering it out
5. **Navigate Up**: Go to higher level view

### Navigation Not Working

**Symptoms**: Clicking doesn't navigate

**Solutions:**
1. **Check Element Type**: Some elements don't have drill-down
2. **Try Different Click**: Single vs double click
3. **Check View**: Some views don't support navigation
4. **Refresh Page**: Reload the page
5. **Check Browser**: Ensure JavaScript is enabled

### Diagram Too Crowded

**Symptoms**: Too many elements, hard to read

**Solutions:**
1. **Zoom In**: Focus on specific area
2. **Navigate Down**: Go to more specific view
3. **Use Search**: Find specific element
4. **Pan Around**: Move to different area
5. **Export and Zoom**: Export and view in image viewer

### Relationship Lines Unclear

**Symptoms**: Can't see or follow relationships

**Solutions:**
1. **Zoom In**: Get closer view
2. **Click Relationship**: Highlight it
3. **Follow Manually**: Trace the line
4. **Check Labels**: Read relationship labels
5. **View Details**: Click elements to see relationships list

### Performance Issues

**Symptoms**: Slow loading or laggy interaction

**Solutions:**
1. **Close Other Tabs**: Free up browser resources
2. **Update Browser**: Use latest browser version
3. **Clear Cache**: Clear browser cache
4. **Reduce Zoom**: Less detail to render
5. **Use Search**: Instead of loading large views

---

## Quick Reference

### Navigation Quick Guide

| Action | Result |
|--------|--------|
| Click Subdomain | Navigate to subdomain overview |
| Click System/Product | Navigate to system context view |
| Click Application | Navigate to container/component view |
| Click Component | Show component details |
| Double Click Element | Zoom to fit element |
| Hover Element | Show quick info tooltip |
| Click Relationship | Highlight relationship |
| Use Search | Find and navigate to element |
| Browser Back | Return to previous view |

### View Types Quick Reference

| View Type | Shows | Use When |
|-----------|-------|---------|
| System Landscape | All subdomains | Getting started, overview |
| Subdomain Overview | Systems in subdomain | Exploring a domain |
| System Context | System, users, externals | Understanding who uses it |
| Container View | Applications, databases | Understanding architecture |
| Component View | Internal components | Technical details |

### Element Types Quick Reference

| Element | Appearance | Represents |
|---------|------------|------------|
| Subdomain | Dashed border box | Logical grouping |
| Product/System | Blue box | Complete system |
| Application | Box in system | Deployable application |
| Component | Small box | Internal component |
| Database | Cylinder icon | Data storage |
| Webapp | Browser icon | Web interface |
| Actor | Person icon | User/role |
| External System | Box with label | External system |

### Color Guide

| Color | Subdomain |
|-------|-----------|
| Green | Scheduling and Listing |
| Yellow | Case Administration |
| Purple | Court Hearings |
| Gray | Shared Components |
| Red | Operational and Management Information |
| (Default) | Case Ingestion, OPAMI |

### Common Search Terms

- **"case"**: Case Management, Case Administration
- **"hearing"**: Hearing System, Court Hearings
- **"notification"**: Notification systems
- **"user"**: Users and Groups System
- **"staging"**: Staging System
- **"scheduling"**: Scheduling systems
- **"document"**: Document Generation
- **"audit"**: Audit System

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl/Cmd + F | Search |
| Ctrl/Cmd + +/- | Zoom |
| Arrow Keys | Navigate (some views) |
| Esc | Close dialogs |
| Mouse Wheel | Zoom in/out |
| Click + Drag | Pan diagram |

---

## Getting Help

### Resources

- **Online Documentation**: https://hmcts.github.io/cp-c4-architecture/
- **Reference Manual**: See REFERENCE_MANUAL.md for technical details
- **Changelog**: See CHANGELOG.md for recent updates

### Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Review the Reference Manual for technical details
3. Contact the architecture team
4. Check for updates to the documentation

---

## Conclusion

This user guide provides the foundation for exploring the Common Platform C4 Architecture documentation. Remember:

- **Start Broad**: Begin with System Landscape for overview
- **Drill Down**: Click elements to explore details
- **Use Search**: Find specific systems quickly
- **Follow Relationships**: Understand how systems connect
- **Explore Systematically**: Use the scenarios as guides

The documentation is interactive and designed to help you understand the Common Platform architecture. Take your time exploring, and don't hesitate to navigate back and forth to build your understanding.

**Happy Exploring!**

---

**Last Updated**: 2024
**Documentation Version**: 1.0

