# OEDISI Simulation Designer - Vue 3 Application

This is a Vue 3 + Vite TypeScript application that provides a web-based interface for creating, configuring, and managing co-simulation workflow configurations.

## Features

- **Flowchart Designer**: Interactive drag-and-drop interface using Vue Flow for designing simulation workflows
- **Template Management**: Save, view, edit, and delete simulation templates
- **Component Library**: Pre-built components (Simulator, Data Source, Connector, Configuration)
- **Node Connections**: Connect components with visual edges in the flowchart
- **Responsive UI**: Built with Tailwind CSS and Radix UI Vue components
- **Backend API**: Express.js server with file-based JSON storage
- **Persistent Storage**: Templates stored as JSON files in `data/templates/`

## Project Structure

```
├── server/              # Backend API server
│   ├── index.js         # Express.js server and API routes
│   ├── database.js      # File-based template storage operations
│   └── README.md        # Server documentation
├── data/                # Template storage directory
│   └── templates/       # JSON template files ({id}.json)
├── src/
│   ├── components/
│   │   ├── ui/              # Reusable UI components (Button, Card, Dialog, etc.)
│   │   ├── CustomNode.vue   # Custom Vue Flow node component
│   │   ├── LeftSidebar.vue  # Component palette sidebar
│   │   ├── RightSidebar.vue # Properties editor sidebar
│   │   └── DataVisualization.vue
│   ├── pages/
│   │   ├── Home.vue                # Landing page
│   │   ├── FlowchartDesigner.vue   # Main designer interface with Vue Flow
│   │   ├── SavedConfigs.vue        # Template management
│   │   ├── SimulationResults.vue   # Results viewer
│   │   └── SimulationStatus.vue   # Status monitoring
│   ├── router/
│   │   └── index.ts         # Vue Router configuration
│   ├── lib/
│   │   ├── api.ts           # API client for backend communication
│   │   └── utils.ts         # Utility functions (cn, clsx)
│   ├── styles/
│   │   └── index.css        # Global styles and Tailwind directives
│   ├── App.vue              # Root component
│   └── main.ts              # Application entry point
└── package.json
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm/pnpm

### Installation

1. Navigate to the project directory:
```bash
cd /Users/alatif/Documents/GitHub/oedisi-frontend-app
```

2. Install dependencies:
```bash
npm install
# or
pnpm install
```

3. Start the development servers:

**Option 1: Run both frontend and backend together (recommended):**
```bash
npm run dev:all
```

**Option 2: Run separately:**

Terminal 1 - Backend server:
```bash
npm run dev:server
```

Terminal 2 - Frontend:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`  
The backend API will be available at `http://localhost:3001`

## Building

To create a production build:

```bash
npm run build
# or
pnpm build
```

## Pages

### Home
Landing page with quick access to main features:
- Create new simulation templates
- View saved templates
- Access simulation results
- Monitor simulation status

### Flowchart Designer
Main interface for creating simulation workflows using Vue Flow:
- Drag components from the left sidebar to the canvas
- Connect components by dragging from node handles (left/right sides)
- Edit component properties in the right sidebar
- Select and delete connections
- Save templates with custom names and descriptions
- Zoom, pan, and navigate with built-in controls
- Minimap for overview of the flowchart

### Saved Configs
Manage previously created templates:
- View all saved templates with metadata
- See all components in each template
- Load templates back into the designer
- Run simulations from saved templates
- Download templates as JSON files
- Delete templates

### Simulation Results
View and analyze simulation outputs (placeholder for future implementation)

### Simulation Status
Monitor active simulations and their progress (placeholder for future implementation)

## Technology Stack

### Frontend
- **Vue 3**: Progressive JavaScript framework
- **Vite**: Next generation frontend build tool
- **TypeScript**: Typed JavaScript
- **Vue Flow**: Interactive node-based graph library
- **Tailwind CSS**: Utility-first CSS framework
- **Vue Router**: Official routing library
- **Lucide Vue**: Beautiful SVG icons

### Backend
- **Express.js**: Web application framework
- **Node.js fs/path**: File system template persistence
- **CORS**: Cross-origin resource sharing

## Styling

The application uses Tailwind CSS with custom CSS variables for theming. Colors are defined in `src/styles/index.css` and can be customized in `tailwind.config.ts`.

## Component System

### UI Components
Located in `src/components/ui/`:
- `Button.vue`: Versatile button with multiple variants
- `Card.vue`: Container component with header, default, and footer slots
- `Dialog.vue`: Modal dialog with header, content, and footer
- `Input.vue`: Text input field
- `Textarea.vue`: Multi-line text input
- `Label.vue`: Form label component

### Page Components
Located in `src/pages/`:
Each page is a standalone component that uses the router and UI components.

### Layout Components
- `CustomNode.vue`: Custom Vue Flow node with connection handles
- `LeftSidebar.vue`: Component palette for the designer
- `RightSidebar.vue`: Properties editor
- `DataVisualization.vue`: Data display component

## Data Storage

Templates are stored as **JSON files** in `data/templates/`.

### Storage Structure
- Each template is stored as one JSON file: `data/templates/{id}.json`
- Files contain template metadata plus `nodes` and `edges`
- `GET /api/templates` returns all files sorted by `createdAt` (newest first)

### Template Schema
Each template document contains:
- `id`: Unique identifier (timestamp)
- `name`: Template name
- `description`: Template description
- `nodes`: Array of node objects with positions and data
- `edges`: Array of connection objects (source/target relationships)
- `createdAt`: ISO timestamp

### API Endpoints
The backend provides REST API endpoints:
- `GET /api/templates` - Get all templates
- `GET /api/templates/:id` - Get a single template
- `POST /api/templates` - Save a new template
- `PUT /api/templates/:id` - Update a template
- `DELETE /api/templates/:id` - Delete a template

See `server/README.md` for more details about the backend API.

## Future Enhancements

- Real simulation execution
- Advanced visualization and analytics
- Collaborative design features
- Template sharing and import/export
- Undo/redo functionality
- Component validation
- Custom node types
- Edge labels and properties
- Template versioning

## License

Created from Figma export for OEDISI project.
