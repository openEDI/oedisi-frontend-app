import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const DATA_DIR = path.join(__dirname, '..', 'data')
const TEMPLATES_DIR = path.join(DATA_DIR, 'templates')
const TEMPLATE_ID_PATTERN = /^[a-zA-Z0-9_-]+$/

function ensureStorageDirectories() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true })
  }

  if (!fs.existsSync(TEMPLATES_DIR)) {
    fs.mkdirSync(TEMPLATES_DIR, { recursive: true })
  }
}

function validateTemplateId(id) {
  if (!id || typeof id !== 'string') {
    throw new Error('Template id is required')
  }

  if (!TEMPLATE_ID_PATTERN.test(id)) {
    throw new Error('Invalid template id format')
  }
}

function getTemplateFilePath(id) {
  validateTemplateId(id)
  return path.join(TEMPLATES_DIR, `${id}.json`)
}

function validateTemplate(template) {
  if (!template || typeof template !== 'object') {
    throw new Error('Template payload is required')
  }

  validateTemplateId(template.id)

  if (typeof template.name !== 'string') {
    throw new Error('Template name is required')
  }

  if (typeof template.description !== 'string') {
    throw new Error('Template description is required')
  }

  if (!Array.isArray(template.nodes)) {
    throw new Error('Template nodes must be an array')
  }

  if (!Array.isArray(template.edges)) {
    throw new Error('Template edges must be an array')
  }

  if (typeof template.createdAt !== 'string') {
    throw new Error('Template createdAt is required')
  }
}

export function saveTemplate(template) {
  ensureStorageDirectories()
  validateTemplate(template)

  const targetPath = getTemplateFilePath(template.id)
  const tempPath = `${targetPath}.tmp-${process.pid}-${Date.now()}`
  const body = JSON.stringify(template, null, 2)

  fs.writeFileSync(tempPath, body, 'utf8')
  fs.renameSync(tempPath, targetPath)

  return { success: true, id: template.id }
}

export function getTemplate(id) {
  ensureStorageDirectories()
  const filePath = getTemplateFilePath(id)

  if (!fs.existsSync(filePath)) {
    return null
  }

  const raw = fs.readFileSync(filePath, 'utf8')
  return JSON.parse(raw)
}

export function getAllTemplates() {
  ensureStorageDirectories()

  const files = fs
    .readdirSync(TEMPLATES_DIR)
    .filter(fileName => fileName.endsWith('.json'))

  const templates = []

  for (const fileName of files) {
    const filePath = path.join(TEMPLATES_DIR, fileName)
    try {
      const raw = fs.readFileSync(filePath, 'utf8')
      const template = JSON.parse(raw)
      templates.push(template)
    } catch (error) {
      console.error(`Failed to parse template file ${fileName}:`, error)
    }
  }

  templates.sort((a, b) => {
    const dateA = new Date(a.createdAt || 0).getTime()
    const dateB = new Date(b.createdAt || 0).getTime()
    return dateB - dateA
  })
  
  return templates
}

export function deleteTemplate(id) {
  try {
    ensureStorageDirectories()
    const filePath = getTemplateFilePath(id)

    if (!fs.existsSync(filePath)) {
      throw new Error('Template not found')
    }

    fs.unlinkSync(filePath)
    return { success: true }
  } catch (error) {
    console.error('File delete error:', error)
    throw error
  }
}

export function closeDatabase() {
  return
}

