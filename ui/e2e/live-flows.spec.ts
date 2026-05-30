import { test, expect, type Page } from '@playwright/test'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Switch to Anthropic / Haiku / Dev mode before booting. */
async function configureHaiku(page: Page) {
  await page.locator('.provider-btn', { hasText: 'Claude' }).click()
  await page.getByLabel('Dev').check()
  await page.getByLabel('Model').selectOption('claude-haiku-4-5-20251001')
}

/** Click Boot and wait for the session badge to appear. */
async function bootSession(page: Page) {
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.getByText(/Session 1/)).toBeVisible({ timeout: 20_000 })
}

/** Fill the input, send, then wait until the Send button re-enables (stream done). */
async function sendTurnAndWait(page: Page, text: string) {
  await page.getByRole('textbox').fill(text)
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByRole('button', { name: 'Send' })).toBeEnabled({ timeout: 60_000 })
}

// ---------------------------------------------------------------------------
// L1–L4  — shared session: boot once, send one turn, run all format checks
//
// Dev mode is ON so every %%SECTION%% marker streams through to the GM bubble,
// making them directly assertable in the DOM without log scraping.
// ---------------------------------------------------------------------------

test.describe.serial('L1-L4 — live session and response format', () => {
  let page: Page
  let sessionId = ''

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()

    // Capture the session ID from the outgoing /turn request URL before any
    // response arrives — no mocking, pure observation.
    page.on('request', req => {
      const m = req.url().match(/\/api\/sessions\/([^/]+)\/turn/)
      if (m && !sessionId) sessionId = m[1]
    })

    await page.goto('/')
    await configureHaiku(page)
    await bootSession(page)
    await sendTurnAndWait(page, 'I look around the room carefully.')
  })

  test.afterAll(async () => {
    await page.close()
  })

  // L1 — session badge confirms Haiku is active and no errors surfaced
  test('L1 — session badge shows Haiku, no error bar', async () => {
    await expect(page.getByText(/haiku/i)).toBeVisible()
    await expect(page.locator('.error-bar')).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'End Session' })).toBeVisible()
  })

  // L2 — LLM followed the format: %%NARRATIVE%% must appear in the GM bubble
  test('L2 — GM bubble contains %%NARRATIVE%%', async () => {
    await expect(
      page.locator('.bubble-gm').filter({ hasText: '%%NARRATIVE%%' }),
    ).toBeVisible()
  })

  // L3 — %%DELTAS%% section also present (both required headers = format intact)
  test('L3 — GM bubble contains %%DELTAS%%', async () => {
    await expect(
      page.locator('.bubble-gm').filter({ hasText: '%%DELTAS%%' }),
    ).toBeVisible()
  })

  // L4 — session log written to disk and accessible via API; contains the markers
  test('L4 — log API returns 200 and contains %%NARRATIVE%%', async () => {
    expect(sessionId, 'session ID was not captured from /turn request').toBeTruthy()
    const response = await page.request.get(`/api/sessions/${sessionId}/log`)
    expect(response.status()).toBe(200)
    const body = await response.text()
    expect(body).toContain('%%NARRATIVE%%')
    expect(body.length).toBeGreaterThan(50)
  })
})

// ---------------------------------------------------------------------------
// L5 — full end-session lifecycle with real LLM recap
//
// Sends one turn then triggers "Generate recap" from the dev-mode dialog.
// Asserts the session closes cleanly and the session number increments.
// ---------------------------------------------------------------------------

test('L5 — end session writes recap and returns to pre-boot', async ({ page }) => {
  await page.goto('/')
  await configureHaiku(page)
  await bootSession(page)
  await sendTurnAndWait(page, 'I greet the innkeeper.')

  // Dev mode: End Session shows a confirmation dialog
  await page.getByRole('button', { name: 'End Session' }).click()
  await expect(page.getByText('End session?')).toBeVisible()
  await page.getByRole('button', { name: 'Generate recap' }).click()

  // Recap LLM call — give it generous time
  await expect(page.getByText(/Session saved/)).toBeVisible({ timeout: 90_000 })

  // After the 1.8 s pause the app clears state and returns to pre-boot
  await expect(page.getByRole('button', { name: 'Boot Session' })).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('.error-bar')).not.toBeVisible()

  // Session number must have incremented
  await expect(page.getByLabel('Session')).toHaveValue('2')
})

// ---------------------------------------------------------------------------
// L6 — character sidebar rendered from real /api/characters (no LLM needed)
//
// Validates that the backend serves valid character JSON and the sidebar
// renders it — HP bar and party label visible on page load.
// ---------------------------------------------------------------------------

test('L6 — character sidebar renders from real /api/characters', async ({ page }) => {
  await page.goto('/')

  // At least one character avatar must appear
  await expect(page.locator('.char-icon-btn').first()).toBeVisible({ timeout: 10_000 })

  // HP bar rendered (colour driven by real HP values from the JSON)
  await expect(page.locator('.char-hp-bar').first()).toBeVisible()

  // Sidebar label present
  await expect(page.locator('.sidebar-label')).toHaveText('Party')
})
