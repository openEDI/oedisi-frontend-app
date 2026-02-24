# Backend API Server

This Express.js server provides a REST API for storing and managing flowchart templates as JSON files in the `data` folder.

## Features

- Store templates as JSON files in the `data` folder
- RESTful API endpoints for CRUD operations
- CORS enabled for frontend integration
- Automatic data directory creation

## API Endpoints

- `GET /api/templates` - Get all templates
- `GET /api/templates/:id` - Get a single template by ID
- `POST /api/templates` - Save a new template
- `PUT /api/templates/:id` - Update an existing template
- `DELETE /api/templates/:id` - Delete a template

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

