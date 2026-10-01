# Backend API Server

This FastAPI server provides REST APIs for storing flowchart templates, managing uploaded distribution models, and launching OEDISI simulations.

## Features

- Store templates as JSON files in the `data` folder
- Upload and inspect GDM, CIM, OpenDSS, and CYME distribution models
- Convert supported distribution models to OpenDSS through Ditto
- Resolve managed model IDs to run-local Feeder artifacts
- RESTful API endpoints for CRUD operations
- CORS enabled for frontend integration
- Automatic data directory creation

## API Endpoints

- `GET /api/templates` - Get all templates
- `GET /api/templates/:id` - Get a single template by ID
- `POST /api/templates` - Save a new template
- `PUT /api/templates/:id` - Update an existing template
- `DELETE /api/templates/:id` - Delete a template

Managed models:

- `POST /api/models/upload` - Upload and convert a model
- `GET /api/models` - List the current user's models
- `GET /api/models/:id` - Get model metadata and conversion status
- `GET /api/models/:id/inspection` - Get the component inventory and topology
- `GET /api/models/:id/components` - Search and paginate model components
- `GET /api/models/:id/topology` - Get read-only topology data
- `GET /api/models/:id/source/download` - Download the original source
- `GET /api/models/:id/artifacts/opendss/download` - Download the generated OpenDSS artifact
- `PATCH /api/models/:id` - Update display metadata
- `DELETE /api/models/:id` - Delete a model and its artifacts

## Running the Server

### Development

Run the server separately:
```bash
npm run dev:server
```

Or run both frontend and backend together:
```bash
npm run dev:all
```

The server will run on `http://localhost:3001`

## Data Storage

Templates are stored as individual JSON files in: `data/templates/`

Models are stored under `data/models/{user}/{model_id}/`. Each model keeps its
original source files, conversion metadata, an OpenDSS artifact, and a derived
inspection manifest. Simulation templates store only the model ID; the backend
materializes the OpenDSS artifact inside the run directory when a Feeder run is
built.

Storage model:
- Each template is one file named `{id}.json`
- Files contain full template JSON payloads
- Templates are listed by reading all JSON files and sorting by `createdAt` (newest first)

Each template document contains:
- `id`: Unique identifier
- `name`: Template name
- `description`: Template description
- `nodes`: Array of node objects
- `edges`: Array of edge/connection objects
- `createdAt`: ISO timestamp
