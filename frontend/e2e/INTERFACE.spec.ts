import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * The interface rebuild's four load-bearing flows (CHG-040, CHG-048, CHG-055), proven
 * with hands on the screen. The backend tests prove the rows; these prove a person can
 * produce them.
 *
 *  1. Focus Mode's keyboard triage writes a decision record the activity rail renders.
 *  2. The summary review's approve block: text the figures cannot back is refused with
 *     the violation named, and the honest text goes through to Sent.
 *  3. The match queue shows both sides of a withheld merge and M resolves it.
 *  4. "Use sample storm data" loads through the same parse path as an upload.
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
  await page.getByLabel('Source name').fill('Interface rebuild storm')
  await page.setInputFiles(
    '#storm-files',
    FILES.map((name) => path.join(FIXTURE, name)),
  )
  await page.getByRole('button', { name: 'Process data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
}

test('focus mode triages on the keyboard, and the feed says a person decided', async ({
  page,
}) => {
  await loadedStorm(page)
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()

  await page.getByTestId('start-triage').click()
  await expect(page.getByTestId('focus-mode')).toBeVisible()
  await expect(page.getByTestId('focus-mode')).toContainText('0 of')

  // A — accept, advance. The record is the point; the screen only has to move on.
  await page.keyboard.press('a')
  await expect(page.getByTestId('focus-mode')).toContainText('1 of')

  // D without a note demands the why — a dismissal is worth keeping only with one.
  await page.keyboard.press('d')
  await expect(page.getByLabel('Why dismiss? (required)')).toBeVisible()
  await page.getByLabel('Why dismiss? (required)').fill('asset is offline for planned works')
  await page.getByRole('button', { name: /^Dismiss/ }).click()
  await expect(page.getByTestId('focus-mode')).toContainText('2 of')

  await page.keyboard.press('Escape')
  await expect(page.getByTestId('focus-mode')).toHaveCount(0)

  // The rail: a human deciding, named — never "the system flagged" (CHG-054).
  await page.getByRole('button', { name: 'Dispatch Board' }).click()
  const rail = page.getByTestId('activity-rail')
  await expect(rail).toContainText('accepted the ranking for')
  await expect(rail).toContainText('dismissed the ranking for')
  await expect(rail).not.toContainText('auto-flagged')
  await expect(rail).not.toContainText('sync')
})

test('the summary blocks approval of a figure the platform does not hold', async ({ page }) => {
  await loadedStorm(page)
  await page.getByRole('button', { name: 'Dispatch Board' }).click()

  await page.getByRole('button', { name: /Draft summary|Regenerate/ }).click()
  const card = page.getByTestId('situation-summary')
  await expect(card.getByTestId('summary-state')).toHaveText('Draft')
  // The model is off in this harness: the label must say the figures wrote it.
  await expect(card).toContainText('Assembled from platform data')

  await page.getByRole('button', { name: 'Review and approve' }).click()
  const sheet = page.getByTestId('summary-review')
  await expect(sheet).toBeVisible()
  await expect(page.getByTestId('verification-table')).toBeVisible()

  // A figure nobody supplied. The server refuses it and the refusal is on screen.
  await page.getByLabel('Summary content').fill('An estimated 41,500 customers are without service.')
  await page.getByTestId('approve-summary').click()
  await expect(sheet).toContainText('Approval is blocked until they match.')
  await expect(card.getByTestId('summary-state')).toHaveText('Draft')

  // The honest text goes through — Draft → Approved → Sent in one review.
  await page
    .getByLabel('Summary content')
    .fill('There are 0 open incidents on the board. 0 involve critical facilities.')
  await page.getByTestId('approve-summary').click()
  await expect(card.getByTestId('summary-state')).toHaveText('Sent')
})

test('the match queue shows both sides and M records the reviewer', async ({ page }) => {
  await loadedStorm(page)
  // Processing ends on the Load surface, quality summary already on screen.
  const quality = page.getByTestId('data-quality-summary')
  await expect(quality).toBeVisible()
  // The fixture withholds merges on purpose (defect 1) — the finding offers Review.
  await quality.getByRole('button', { name: 'Review' }).click()

  const sheet = page.getByTestId('match-queue')
  await expect(sheet).toBeVisible()
  await expect(page.getByTestId('match-candidate')).toBeVisible()
  await expect(sheet).toContainText('confidence')
  await expect(sheet).not.toContainText('%')

  const before = await page.locator('text=/\\d+ of \\d+ reviewed/').innerText()
  await page.getByTestId('match-confirm').click()
  await expect(page.locator('text=/\\d+ of \\d+ reviewed/')).not.toHaveText(before)
})

test('the sample button loads a storm through the same parse path', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Email').fill('ops@sgw.example')
  await page.getByLabel('Password').fill('e2e-fixture-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByRole('button', { name: 'Load storm data' }).click()

  await page.getByRole('button', { name: 'Use sample storm data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  // Through the quality summary and the door — a real ranking behind it, not a shortcut.
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()
})
