import fs from 'node:fs'
import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * TASK-009 done criterion 11 — a person switches between two loaded storms, in a real browser.
 *
 * REQ-F-010 and US-002: *"I want to keep several storms loaded and switch between them, so that
 * I can compare or re-run **without destroying the one I have**."* The API-level test of the
 * same requirement is `test_ITEST-005_scenarios_never_blend.py`; it proves the rows. This proves
 * the screen, and `AGENT.md` carries a standing rule that a claim about a screen needs a browser
 * case — three criteria about screens in this repository were satisfied by reading source
 * before the review that made it a rule.
 *
 * **The failure it is written against has no visible symptom**, which is the whole reason it is
 * asserted rather than noticed. `security-review.md` §4: *"a missing scope here is a correctness
 * bug — two storms blended into one ranking would look entirely plausible."* Storm A's rows
 * under storm B's name look exactly like storm B. So every case below names **both** storms:
 * what must be on screen, and what must not.
 *
 * **The two fixtures share no asset code**, which is what makes the second half assertable at
 * all. `storm-for-the-planning-flow` was not used here for exactly that reason — its asset codes
 * are identical to `storm-with-seven-defects`, so a blend between those two would be invisible
 * on screen and the test would pass through it.
 *
 * **This file only ever reads `storm-with-a-forecast-change`.** `ATEST-005.spec.ts` owns that
 * fixture's revision pointer and says so in its own header; one backend and one database serve
 * the whole browser run, and this spec runs after it. Nothing here applies a forecast change or
 * asserts a revision number.
 */

const FIXTURES = path.resolve(__dirname, '../../spec/03-tests/05-executable/fixtures')
const FILES = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']

/** The two storms, and the codes that tell them apart on a screen. */
const HELENE = {
  fixture: 'storm-with-seven-defects',
  name: 'Helene replay',
  note: 'NOAA 2024 replay pack',
  code: 'SS-1042',
}
const TRACK = {
  fixture: 'storm-with-a-forecast-change',
  name: 'Track shift',
  note: 'Forecast-change rehearsal',
  code: 'SS-ALPHA',
}

async function signIn(page: Page, email = 'ops@sgw.example') {
  await page.goto('/')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill('e2e-fixture-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByTestId('role')).toBeVisible()
}

/**
 * Load one storm through the panel. Identical content resolves to the storm already loaded
 * (§5, replace in place), so this is idempotent across the whole browser run and this file
 * behaves the same whether it runs alone or after the four specs before it.
 */
async function load(page: Page, storm: typeof HELENE) {
  await page.getByRole('button', { name: 'Load storm data' }).click()
  await page.getByLabel('Source name').fill(storm.name)
  await page.setInputFiles(
    '#storm-files',
    FILES.map((name) => path.join(FIXTURES, storm.fixture, name)),
  )
  await page.getByRole('button', { name: 'Process data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
}

async function chooseStorm(page: Page, name: string) {
  await page.getByTestId('scenario-switcher-toggle').click()
  await page.getByTestId('scenario-option').filter({ hasText: name }).click()
}

/** Everything a person can read of a storm's data, in one place. */
async function screenText(page: Page): Promise<string> {
  return page.getByTestId('scenario-data').innerText()
}

async function bothStormsLoaded(page: Page) {
  await signIn(page)
  await load(page, HELENE)
  await load(page, TRACK)
}

/**
 * A storm no other spec loads, so this file can say what its source note is.
 *
 * An identical re-load resolves to the storm already there and does **not** change its note
 * (§5, replace in place) — so for the two fixtures above, whichever spec loaded them first
 * decided what their note says, and a `.fill()` here would be a value nothing reads. Patching
 * the manifest changes the content, which is what makes it a different storm (CHG-031).
 */
function anUnsharedStorm(): { name: string; mimeType: string; buffer: Buffer }[] {
  const dir = path.join(FIXTURES, 'storm-for-the-planning-flow')
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'))
  manifest.scenario_id = 'STORM-SWITCHER-REHEARSAL'
  manifest.storm_name = 'Switcher rehearsal'
  return FILES.map((name) => ({
    name,
    mimeType: name.endsWith('.json') ? 'application/json' : 'text/csv',
    buffer:
      name === 'manifest.json'
        ? Buffer.from(JSON.stringify(manifest, null, 2))
        : fs.readFileSync(path.join(dir, name)),
  }))
}

test('the source note the switcher shows is a human sentence, never a digest', async ({
  page,
}) => {
  /**
   * `database-design.md` §3 defines `source_note` as *which prepared dataset this is, and
   * where it came from*, and until migration 013 that column held a SHA-256 digest while
   * the note was discarded (CHG-031). The panel asks one question now — the source name —
   * and states its own fallback note; what CHG-031 protects is still asserted: the column
   * reaches the screen as words a reader can use, and nothing hex-shaped stands in for it.
   */
  await signIn(page)
  await page.getByRole('button', { name: 'Load storm data' }).click()
  await page.getByLabel('Source name').fill('Switcher rehearsal')
  await page.setInputFiles('#storm-files', anUnsharedStorm())
  await page.getByRole('button', { name: 'Process data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })

  await page.getByTestId('scenario-switcher-toggle').click()
  const option = page.getByTestId('scenario-option').filter({ hasText: 'Switcher rehearsal' })

  await expect(option).toHaveCount(1)
  await expect(option).toContainText('uploaded via the panel')
  await expect(option).not.toContainText(/[0-9a-f]{64}/)
})

test('the switcher lists every loaded storm, with what the component spec says it shows', async ({
  page,
}) => {
  await bothStormsLoaded(page)

  // Read from the API in the same browser context, so the assertion is "the screen shows what
  // the server said" rather than "the screen shows what this test happens to expect".
  const listed = await (await page.request.get('/api/v1/scenarios')).json()
  expect(listed.items.length).toBeGreaterThanOrEqual(2)

  await page.getByTestId('scenario-switcher-toggle').click()
  const options = page.getByTestId('scenario-option')
  await expect(options).toHaveCount(listed.items.length)

  for (const item of listed.items) {
    const option = options.filter({ hasText: item.name }).first()
    // name, source note, loaded date — `frontend-component-spec.md`'s three fields.
    await expect(option).toContainText(item.name)
    await expect(option).toContainText(item.source_note)
    await expect(option).toContainText(new Date(item.loaded_at).getFullYear().toString())
  }
})

test('switching to another storm replaces every panel with that storm', async ({ page }) => {
  await bothStormsLoaded(page)

  await chooseStorm(page, HELENE.name)

  await expect(page.getByTestId('risk-list')).toBeVisible()
  const showing = await screenText(page)
  expect(showing).toContain(HELENE.code)
  // The half with no visible symptom: none of the other storm is here.
  expect(showing).not.toContain(TRACK.code)
})

test('switching back replaces it again, and neither storm leaks into the other', async ({
  page,
}) => {
  await bothStormsLoaded(page)
  await chooseStorm(page, HELENE.name)
  await expect(page.getByTestId('risk-list')).toContainText(HELENE.code)

  await chooseStorm(page, TRACK.name)

  await expect(page.getByTestId('risk-list')).toContainText(TRACK.code)
  const showing = await screenText(page)
  expect(showing).toContain(TRACK.code)
  expect(showing).not.toContain(HELENE.code)
})

test('the storm being left is gone from the screen before the next one arrives', async ({
  page,
}) => {
  /**
   * The blend as it would actually happen: not a wrong query, but the previous storm's rows
   * left standing under the new storm's name for as long as the reads take. During a storm
   * that is a ranking somebody could place a crew against.
   *
   * **Every scenario-scoped read is held**, not only the asset table's, because the panels
   * differ in how they fail to clear. The ranking shows a loading state on its own — the
   * read sets it before the request goes out — so the assertion that actually needs the screen
   * to be *cleared* is about the panel rendered from the scenario itself: `StalenessBanner`
   * is drawn from `scenario`, and a `scenario` left standing puts the storm being left's
   * age above the storm being entered's name (CHG-062 removed the revision control this
   * comment used to name alongside it).
   */
  await bothStormsLoaded(page)
  await chooseStorm(page, TRACK.name)
  await expect(page.getByTestId('risk-list')).toContainText(TRACK.code)
  await expect(page.getByTestId('staleness-banner')).toBeVisible()

  let release: (() => void) | null = null
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  const anyScenarioRead = '**/api/v1/scenarios/*{,/**}'
  await page.route(anyScenarioRead, async (route) => {
    await held
    await route.fallback()
  })

  await chooseStorm(page, HELENE.name)

  // Mid-switch: the ranking says it is loading, and nothing of Track shift is underneath.
  await expect(page.getByTestId('risk-list-loading')).toBeVisible()
  await expect(page.getByTestId('staleness-banner')).toHaveCount(0)
  expect(await screenText(page)).not.toContain(TRACK.code)

  release!()
  await page.unroute(anyScenarioRead)
  await expect(page.getByTestId('risk-list')).toContainText(HELENE.code)
  await expect(page.getByTestId('staleness-banner')).toBeVisible()
})

test('a read that was still in flight when the storm changed never reaches the screen', async ({
  page,
}) => {
  /**
   * The other way one storm's rows land under another storm's name, and the one no query scope
   * can prevent: the request for the storm being left is already on the wire. Let it come back
   * last and it paints over the storm that is now selected — a ranking and an asset table
   * belonging to a storm nobody is looking at, with nothing on screen saying so.
   *
   * Helene's ranking read is held, the reader switches to Track shift, and Helene's response
   * is then released **after** Track shift's has already arrived. The last switch has to win, not
   * the last response.
   */
  await bothStormsLoaded(page)

  let release: (() => void) | null = null
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  let firstAssetRead = true
  await page.route('**/api/v1/scenarios/*/risks*', async (route) => {
    if (firstAssetRead) {
      firstAssetRead = false
      await held
    }
    await route.fallback()
  })

  await chooseStorm(page, HELENE.name)
  await expect(page.getByTestId('risk-list-loading')).toBeVisible()
  await chooseStorm(page, TRACK.name)
  await expect(page.getByTestId('risk-list')).toContainText(TRACK.code)

  // Helene's answer arrives now, long after the reader moved on.
  release!()

  // It must never appear. Given time to, if it were going to.
  await expect(page.getByTestId('risk-list')).toContainText(TRACK.code)
  await page.waitForTimeout(500)
  const showing = await screenText(page)
  expect(showing).toContain(TRACK.code)
  expect(showing).not.toContain(HELENE.code)
  await page.unroute('**/api/v1/scenarios/*/risks*')
})

test('the empty state reads "no storm loaded yet" and points an admin at the upload panel', async ({
  page,
}) => {
  /**
   * `frontend-component-spec.md`: *"The empty state reads 'no storm loaded yet' and points an
   * admin at the upload panel. **It must never render as a scenario with no risk.**"*
   *
   * Reached by intercepting the list rather than by emptying the database: one database serves
   * the whole browser run, and a spec that deleted every storm to reach one state would take
   * the other four specs with it.
   */
  await page.route('**/api/v1/scenarios', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  await signIn(page)

  const switcher = page.getByTestId('scenario-switcher')
  await expect(switcher).toContainText('No storm loaded yet')
  await expect(switcher).toContainText('Load a prepared storm')
  // Never a storm with nothing in it: there is no ranking and no board on screen to be
  // read as "nothing is at risk".
  await expect(page.getByTestId('risk-list')).toHaveCount(0)
})

test('a non-admin is told there is no storm without being pointed at a panel they cannot use', async ({
  page,
}) => {
  await page.route('**/api/v1/scenarios', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  await signIn(page, 'dispatch@sgw.example')

  const switcher = page.getByTestId('scenario-switcher')
  await expect(page.getByTestId('role')).toHaveText('operator')
  await expect(switcher).toContainText('No storm loaded yet')
  await expect(switcher).not.toContainText('Load a prepared storm')
})

test('a storm with no ranking behind it is labelled as one, never offered as a ranked storm', async ({
  page,
}) => {
  /**
   * *"It must never render as a scenario with no risk"* — `frontend-component-spec.md`'s rule
   * for this component, and CHG-027's argument one component over: a storm whose current
   * revision has no order behind it is one click from an empty screen, and an empty screen in
   * this product reads as safety.
   *
   * The list is intercepted rather than engineered in the database: every storm is ranked at
   * load, so the state exists in the response's vocabulary and not in the browser run's data —
   * and a screen rule is worth testing at the screen. The API half is asserted against real rows
   * in `test_ITEST-005_scenarios_never_blend.py`.
   */
  await page.route('**/api/v1/scenarios', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      json: {
        total: 2,
        items: [
          {
            scenario_id: 'SC-ranked',
            name: 'A ranked storm',
            source_note: 'note one',
            loaded_at: '2026-08-16T09:00:00Z',
            forecast_revision: 0,
            forecast_issued_at: '2026-08-16T06:00:00Z',
            data_age_hours: 3,
            stale: false,
            asset_count: 8,
            ranked: true,
          },
          {
            scenario_id: 'SC-unranked',
            name: 'An unranked storm',
            source_note: 'note two',
            loaded_at: '2026-08-16T09:00:00Z',
            forecast_revision: 4,
            forecast_issued_at: '2026-08-16T06:00:00Z',
            data_age_hours: 3,
            stale: false,
            asset_count: 8,
            ranked: false,
          },
        ],
      },
    })
  })
  await signIn(page)

  await page.getByTestId('scenario-switcher-toggle').click()
  const unranked = page.getByTestId('scenario-option').filter({ hasText: 'An unranked storm' })
  const ranked = page.getByTestId('scenario-option').filter({ hasText: 'A ranked storm' })

  await expect(unranked).toContainText('not ranked yet')
  // The haystack beside it: a storm that *is* ranked says so, so "not ranked yet" means
  // something rather than being printed on every row.
  await expect(ranked).toContainText('ranked at revision 0')
  await expect(ranked).not.toContainText('not ranked yet')
})

test('a list that could not be read says so and offers a retry, and never reads as empty', async ({
  page,
}) => {
  /**
   * The error state, and the reason it is not allowed to borrow the empty one's words: *no
   * storm loaded* and *we could not find out which storms are loaded* are different facts, and
   * only one of them means an admin should go and load something.
   */
  let attempts = 0
  await page.route('**/api/v1/scenarios', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    attempts += 1
    if (attempts === 1) {
      return route.fulfill({
        status: 500,
        json: { code: 'internal_error', message: 'Something went wrong.' },
      })
    }
    return route.fallback()
  })
  await signIn(page)

  const switcher = page.getByTestId('scenario-switcher')
  await expect(switcher).toContainText('could not read')
  await expect(switcher).not.toContainText('No storm loaded yet')

  await switcher.getByRole('button', { name: 'Retry' }).click()

  await expect(page.getByTestId('scenario-switcher-toggle')).toBeVisible()
})

test('the switcher shows progress while the list is being read, never a blank frame', async ({
  page,
}) => {
  let release: (() => void) | null = null
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  await page.route('**/api/v1/scenarios', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await held
    return route.fallback()
  })
  await signIn(page)

  await expect(page.getByTestId('scenario-switcher')).toContainText('Reading the loaded storms')

  release!()
  await expect(page.getByTestId('scenario-switcher-toggle')).toBeVisible()
})
