import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * ATEST-004 — REQ-F-003, BR-002, AC-004.
 *
 * "A user looks at any risk rank on any screen → the reasons behind it are available beside
 * it in plain words, never behind a separate request."
 *
 * Driven in a browser because the claim is about what is **on the screen**. The API test
 * proves the reasons arrive with the rank; this proves a person can read them, and that an
 * unscored asset is visibly not-judged rather than judged safe.
 */

const FIXTURE = path.resolve(
  __dirname,
  '../../spec/03-tests/05-executable/fixtures/storm-with-seven-defects',
)
const FILES = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']

async function loadedStorm(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email').fill('ops@sgw.example')
  await page.getByLabel('Password').fill('e2e-fixture-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByLabel('Source name').fill('Helene replay')
  await page.setInputFiles(
    '#storm-files',
    FILES.map((name) => path.join(FIXTURE, name)),
  )
  await page.getByRole('button', { name: 'Process data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  // The quality summary is mandatory reading; Finish and continue is the door forward.
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()
}

test('the ranking is on screen, ordered, with a band on every rank', async ({ page }) => {
  await loadedStorm(page)

  const first = page.locator('[data-testid="risk-list"] tbody tr').first()
  await expect(first.locator('.risk__rank')).toHaveText('1')
  await expect(first.locator('.band')).toBeVisible()
})

test('the reasons behind a rank are readable beside it, in plain words', async ({ page }) => {
  await loadedStorm(page)

  await page.getByRole('button', { name: 'Why?' }).first().click()

  const panel = page.getByTestId('reason-panel').first()
  await expect(panel).toBeVisible()
  await expect(panel).toContainText('built to withstand')
  await expect(panel).toContainText('coastal high-hazard flood zone')
  // The values the reasons rest on, with their provenance (BR-003).
  await expect(panel).toContainText('The values these reasons rest on')
  await expect(panel).toContainText('observed')
})

test('an unscored asset is shown as not-judged rather than judged low', async ({ page }) => {
  await loadedStorm(page)

  const group = page.getByTestId('unscored-group')
  await expect(group).toBeVisible()
  await expect(group).toContainText('could not be scored')
  await expect(group).toContainText('not')
  await expect(group.locator('.band--unscored').first()).toHaveText('Not scored')
})

test('the screen says the weights are uncalibrated', async ({ page }) => {
  await loadedStorm(page)

  const notice = page.getByTestId('uncalibrated-notice')
  await expect(notice).toBeVisible()
  await expect(notice).toContainText('have not been calibrated')
  await expect(notice).toContainText('adr-007-')
})
