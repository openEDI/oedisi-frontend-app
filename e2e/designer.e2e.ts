import { expect, test } from '@playwright/test'

test('Tol number renders', async ({ page }) => {
  const errors: Error[] = []
  page.on('pageerror', (error) => {
    errors.push(error)
  })
  await page.goto('/designer')

  const stateEstimator = page.getByText('WLS State Estimator')
  await stateEstimator.dragTo(page.locator('.vue-flow__pane'))
  const node = page.locator('.vue-flow__node')

  await node.click()
  await expect(page.getByRole('spinbutton', { name: 'Tol' })).toBeVisible()

  expect(errors).toEqual([])
})

test('ADMM DOPF description renders', async ({ page }) => {
  const errors: Error[] = []
  page.on('pageerror', (error) => {
    errors.push(error)
  })
  await page.goto('/designer')

  const admm = page.getByText('ADMM DOPF')
  await admm.dragTo(page.locator('.vue-flow__pane'))
  const node = page.locator('.vue-flow__node')

  await node.click()
  await expect(page.getByRole('spinbutton', { name: 'Rho Sup' })).toBeVisible()
  await expect(
    page.getByText('ADMM penalty parameter for active power injection')
  ).toBeVisible()

  expect(errors).toEqual([])
})
