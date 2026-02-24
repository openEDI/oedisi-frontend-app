const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:3001/api'

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

async function run() {
  const testId = `smoke-${Date.now()}`
  const template = {
    id: testId,
    name: 'Smoke Test Template',
    description: 'Created by smoke test',
    nodes: [],
    edges: [],
    createdAt: new Date().toISOString(),
  }

  console.log(`Using API: ${API_BASE_URL}`)

  const createResponse = await fetch(`${API_BASE_URL}/templates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(template),
  })
  assert(createResponse.ok, `POST failed: ${createResponse.status}`)
  const createBody = await createResponse.json()
  assert(createBody.success === true, 'POST response missing success=true')
  assert(createBody.id === testId, 'POST response id mismatch')
  console.log(`✓ Created template ${testId}`)

  const listResponse = await fetch(`${API_BASE_URL}/templates`)
  assert(listResponse.ok, `GET /templates failed: ${listResponse.status}`)
  const templates = await listResponse.json()
  assert(Array.isArray(templates), 'GET /templates did not return an array')
  const found = templates.find(item => item.id === testId)
  assert(Boolean(found), 'Created template not found in list')
  console.log('✓ Listed templates and found created template')

  const deleteResponse = await fetch(`${API_BASE_URL}/templates/${testId}`, {
    method: 'DELETE',
  })
  assert(deleteResponse.ok, `DELETE failed: ${deleteResponse.status}`)
  console.log(`✓ Deleted template ${testId}`)

  const verifyDeleteResponse = await fetch(`${API_BASE_URL}/templates/${testId}`)
  assert(verifyDeleteResponse.status === 404, `Expected 404 after delete, got ${verifyDeleteResponse.status}`)
  console.log('✓ Verified deleted template returns 404')

  console.log('Smoke test passed')
}

run().catch(error => {
  console.error('Smoke test failed:', error.message)
  process.exit(1)
})
