import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * E2E-002 — REQ-F-001, REQ-F-010. Defined in
 * `spec/03-tests/02-functional/end-to-end-tests.md`.
 *
 * "An admin can drag a storm's files in and reach a rankable scenario, or a legible refusal.
 * The scenario appears alongside any others; a refusal names the file and changes nothing."
 *
 * **The "rankable" half belongs to TASK-003** and is asserted as far as the boundary allows:
 * the storm loads and its assets are readable. There is no ranking to reach yet, and standing
 * up a placeholder scorer to satisfy a browser test would anticipate the module TASK-002 must
 * not touch.
 *
 * This drives both processes for real. The failures worth catching here are the ones that
 * only appear when the two have to agree — a cookie that does not survive the proxy, a
 * multipart body the browser encodes differently from `TestClient`.
 */

const FIXTURE = path.resolve(
  __dirname,
  '../../spec/03-tests/05-executable/fixtures/storm-with-seven-defects',
)
const FILES = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']
const PASSWORD = 'e2e-fixture-password'

async function signIn(page: Page, email: string) {
  await page.goto('/')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByTestId('role')).toBeVisible()
}

async function loadTheStorm(page: Page, files = FILES) {
  await page.getByLabel('Storm name').fill('Helene replay')
  await page.setInputFiles(
    '#storm-files',
    files.map((name) => path.join(FIXTURE, name)),
  )
}

test('an admin loads a prepared storm and reaches the joined asset view', async ({ page }) => {
  await signIn(page, 'ops@sgw.example')
  await expect(page.getByTestId('role')).toHaveText('admin')

  await loadTheStorm(page)

  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('asset-table')).toBeVisible()
  // The two codes for one substation arrive as one row, all the way to the screen — once in
  // the joined view and once in the ranking, and in neither as two assets.
  await expect(
    page.getByTestId('asset-table').locator('tr', { hasText: 'SS-1042 · TX-4471' }),
  ).toHaveCount(1)
})

test('records the join could not resolve reach a person rather than being dropped', async ({
  page,
}) => {
  await signIn(page, 'ops@sgw.example')
  await loadTheStorm(page)
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })

  await expect(page.getByTestId('needs-review-count')).toContainText('2 record(s)')
  await expect(page.getByTestId('needs-review').first()).toBeVisible()
})

test('the screen states how old the data is', async ({ page }) => {
  await signIn(page, 'ops@sgw.example')
  await loadTheStorm(page)
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })

  // The fixture's forecast is issued well over six hours before it is loaded, so the
  // non-dismissible form is what should appear — and it must say the age, not just "stale".
  const banner = page.getByTestId('staleness-banner')
  await expect(banner).toBeVisible()
  await expect(banner).toContainText('old')
  await expect(banner).toContainText('6 hours')
})

test('a refusal names the file and changes nothing', async ({ page }) => {
  await signIn(page, 'ops@sgw.example')

  // manifest.json is missing: the load must fail whole and say which file.
  await loadTheStorm(page, ['assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv'])

  const refusal = page.getByTestId('upload-error')
  await expect(refusal).toBeVisible({ timeout: 30_000 })
  await expect(refusal).toContainText('manifest.json')
  await expect(page.getByTestId('asset-table')).toHaveCount(0)
  await expect(page.getByTestId('risk-list')).toHaveCount(0)
})

test('a non-admin is not offered the upload panel', async ({ page }) => {
  await signIn(page, 'dispatch@sgw.example')

  await expect(page.getByTestId('role')).toHaveText('operator')
  await expect(page.getByTestId('upload-panel')).toHaveCount(0)
  // Hiding it is for the user; the server refusing it is the security. STEST-005 calls the
  // endpoint directly for exactly that reason, and this assertion does not replace it.
})
