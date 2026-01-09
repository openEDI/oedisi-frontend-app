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

Templates are stored in a single Couchbase Lite database file: `data/templates.cblite2`

The database uses a Couchbase Lite-compatible structure:
- All templates are stored as documents in the `kv_default` table
- Each template is stored with a key format: `template:{id}`
- Template data is stored as JSON in the `body` column

Each template document contains:
- `id`: Unique identifier
- `name`: Template name
- `description`: Template description
- `nodes`: Array of node objects
- `edges`: Array of edge/connection objects
- `createdAt`: ISO timestamp

The `.cblite2` file is a SQLite database that follows Couchbase Lite's document storage format, making it compatible with Couchbase Lite tools and clients.

