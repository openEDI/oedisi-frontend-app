import Database from 'better-sqlite3'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const DATA_DIR = path.join(__dirname, '..', 'data')
const DB_PATH = path.join(DATA_DIR, 'templates.cblite2')

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true })
}

// Initialize database
let db = null

export function getDatabase() {
  if (!db) {
    db = new Database(DB_PATH)
    initializeDatabase(db)
  }
  return db
}

function initializeDatabase(database) {
  // Create documents table (Couchbase Lite compatible structure)
  // Using TEXT for body to store JSON strings (better-sqlite3 handles conversion)
  database.exec(`
    CREATE TABLE IF NOT EXISTS kv_default (
      key TEXT PRIMARY KEY,
      version BLOB,
      flags INTEGER,
      expiration INTEGER,
      body TEXT,
      deleted INTEGER DEFAULT 0
    );
    
    CREATE INDEX IF NOT EXISTS idx_kv_default_deleted ON kv_default(deleted);
    CREATE INDEX IF NOT EXISTS idx_kv_default_expiration ON kv_default(expiration);
  `)
}

export function saveTemplate(template) {
  const db = getDatabase()
  const stmt = db.prepare(`
    INSERT OR REPLACE INTO kv_default (key, body, deleted, flags)
    VALUES (?, ?, 0, 0)
  `)
  
  const body = JSON.stringify(template)
  stmt.run(`template:${template.id}`, body)
  
  return { success: true, id: template.id }
}

export function getTemplate(id) {
  const db = getDatabase()
  const stmt = db.prepare(`
    SELECT body FROM kv_default 
    WHERE key = ? AND deleted = 0
  `)
  
  const row = stmt.get(`template:${id}`)
  if (row) {
    return JSON.parse(row.body)
  }
  return null
}

export function getAllTemplates() {
  const db = getDatabase()
  const stmt = db.prepare(`
    SELECT body FROM kv_default 
    WHERE key LIKE 'template:%' AND deleted = 0
  `)
  
  const rows = stmt.all()
  const templates = rows.map(row => JSON.parse(row.body))
  
  // Sort by creation date (newest first)
  templates.sort((a, b) => {
    const dateA = new Date(a.createdAt || 0).getTime()
    const dateB = new Date(b.createdAt || 0).getTime()
    return dateB - dateA
  })
  
  return templates
}

export function deleteTemplate(id) {
  try {
    const db = getDatabase()
    
    // First check if template exists
    const checkStmt = db.prepare(`
      SELECT key FROM kv_default 
      WHERE key = ? AND deleted = 0
    `)
    
    const existing = checkStmt.get(`template:${id}`)
    if (!existing) {
      throw new Error('Template not found')
    }
    
    // Hard delete the template (remove from database)
    const stmt = db.prepare(`
      DELETE FROM kv_default 
      WHERE key = ?
    `)
    
    const result = stmt.run(`template:${id}`)
    
    if (result.changes === 0) {
      throw new Error('Failed to delete template - no rows affected')
    }
    
    return { success: true }
  } catch (error) {
    console.error('Database delete error:', error)
    throw error
  }
}

export function closeDatabase() {
  if (db) {
    db.close()
    db = null
  }
}

