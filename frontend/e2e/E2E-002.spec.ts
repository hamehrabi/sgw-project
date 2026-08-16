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
  await page.getByLabel('Source name').fill('Helene replay')
  await page.setInputFiles(
    '#storm-files',
    files.map((name) => path.join(FIXTURE, name)),
  )
  if (files.length === FILES.length) {
    await page.getByRole('button', { name: 'Process data' }).click()
  }
}

test('an admin loads a prepared storm and reaches the ranked view', async ({ page }) => {
  await signIn(page, 'ops@sgw.example')
  await expect(page.getByTestId('role')).toHaveText('admin')

  await loadTheStorm(page)

  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()
  // The two codes for one substation arrive as one row, all the way to the screen — one
  // asset in the ranking, never two. (CHG-062 removed the joined table; the ranking
  // caption carries the same codes, so the claim moved rather than died.)
  await expect(
    page.locator('[data-testid="risk-list"] .row__codes', { hasText: 'SS-1042 · TX-4471' }),
  ).toHaveCount(1)
})

test('records the join could not resolve reach a person rather than being dropped', async ({
  page,
}) => {
  await signIn(page, 'ops@sgw.example')
  await loadTheStorm(page)
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  await page.getByTestId('finish-continue').click()

  // CHG-062 removed the joined table and its count line; the flag lives on the ranking
  // rows themselves now, one badge per record the join withheld.
  await expect(page.getByTestId('needs-review')).toHaveCount(2)
  await expect(page.getByTestId('needs-review').first()).toBeVisible()
})

test('the screen states how old the data is', async ({ page }) => {
  await signIn(page, 'ops@sgw.example')
  await loadTheStorm(page)
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  await page.getByTestId('finish-continue').click()

  // The fixture's forecast is issued well over six hours before it is loaded, so the
  // non-dismissible form is what should appear — and it must say the age, not just "stale".
  const banner = page.getByTestId('staleness-banner')
  await expect(banner).toBeVisible()
  await expect(banner).toContainText('old')
  await expect(banner).toContainText('6 hours')
})

test('an incomplete set is named on screen and never offered for processing', async ({
  page,
}) => {
  await signIn(page, 'ops@sgw.example')

  // manifest.json is missing. Three real uploads failed with the server's 422 before
  // the staging list existed; now the absence is guidance before the POST — the file
  // is named as Missing, and Process data is not offered. The server still refuses an
  // incomplete upload independently (FTEST-001) — this is the courtesy, not the rule.
  await loadTheStorm(page, ['assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv'])

  const staged = page.getByTestId('staged-files')
  await expect(staged.locator('li', { hasText: 'manifest.json' })).toContainText('Missing')
  await expect(page.getByTestId('process-data')).toBeDisabled()
  await expect(page.getByTestId('risk-list')).toHaveCount(0)
})

test('a non-admin is not offered the upload panel', async ({ page }) => {
  await signIn(page, 'dispatch@sgw.example')

  await expect(page.getByTestId('role')).toHaveText('operator')
  await expect(page.getByTestId('upload-panel')).toHaveCount(0)
  // Hiding it is for the user; the server refusing it is the security. STEST-005 calls the
  // endpoint directly for exactly that reason, and this assertion does not replace it.
})
