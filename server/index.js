import express from 'express'
import cors from 'cors'
import {
  saveTemplate,
  getTemplate,
  getAllTemplates,
  deleteTemplate,
  closeDatabase
} from './database.js'

const app = express()
const PORT = 3001

app.use(cors())
app.use(express.json())

// Get all templates
app.get('/api/templates', (req, res) => {
  try {
    const templates = getAllTemplates()
    res.json(templates)
  } catch (error) {
    console.error('Error reading templates:', error)
    res.status(500).json({ error: 'Failed to read templates' })
  }
})

// Get a single template by ID
app.get('/api/templates/:id', (req, res) => {
  try {
    const template = getTemplate(req.params.id)
    if (template) {
      res.json(template)
    } else {
      res.status(404).json({ error: 'Template not found' })
    }
  } catch (error) {
    console.error('Error reading template:', error)
    res.status(500).json({ error: 'Failed to read template' })
  }
})

// Save a template
app.post('/api/templates', (req, res) => {
  try {
    const template = req.body
    
    if (!template.id) {
      template.id = Date.now().toString()
    }
    
    if (!template.createdAt) {
      template.createdAt = new Date().toISOString()
    }

    const result = saveTemplate(template)
    res.json({ success: true, id: result.id, message: 'Template saved successfully' })
  } catch (error) {
    console.error('Error saving template:', error)
    res.status(500).json({ error: 'Failed to save template' })
  }
})

// Update a template
app.put('/api/templates/:id', (req, res) => {
  try {
    const template = req.body
    template.id = req.params.id
    
    // Try to preserve original creation date
    const existing = getTemplate(req.params.id)
    if (existing && existing.createdAt) {
      template.createdAt = existing.createdAt
    } else if (!template.createdAt) {
      template.createdAt = new Date().toISOString()
    }

    saveTemplate(template)
    res.json({ success: true, message: 'Template updated successfully' })
  } catch (error) {
    console.error('Error updating template:', error)
    res.status(500).json({ error: 'Failed to update template' })
  }
})

// Delete a template
app.delete('/api/templates/:id', (req, res) => {
  try {
    deleteTemplate(req.params.id)
    res.json({ success: true, message: 'Template deleted successfully' })
  } catch (error) {
    console.error('Error deleting template:', error)
    const errorMessage = error.message || 'Failed to delete template'
    if (errorMessage === 'Template not found') {
      res.status(404).json({ error: 'Template not found' })
    } else {
      res.status(500).json({ error: errorMessage })
    }
  }
})

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`)
  console.log('Template storage: data/templates/*.json')
})

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down server...')
  closeDatabase()
  process.exit(0)
})

process.on('SIGTERM', () => {
  console.log('\nShutting down server...')
  closeDatabase()
  process.exit(0)
})
