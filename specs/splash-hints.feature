# FEATURE — Splash Screen Hints

**ID:** splash-hints
**Status:** Approved
**Area:** Frontend
**Tags:** @splash @hints @ui @rotation

---

## Story

> As a **player**,
> I want to see a rotating, flavourful hint on the splash screen before a session starts,
> so that waiting for the GM to boot feels engaging rather than static.

The hint replaces the old "Using Groq / Anthropic / Ollama" provider message in the splash
area. Provider configuration is already surfaced in the Header controls; this area should
carry campaign flavour instead.

---

## Background

- Given the UI has loaded
- And no session is currently active
- And character data is loaded

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — A hint from the pool is shown immediately on load
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player opens the app before booting a session

```gherkin
When  the splash screen is visible
Then  a hint element (data-testid="splash-hint") is rendered
And   its text content is one of the known hint strings from the hints pool
And   the hint is NOT the old provider-key reminder text
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Hint rotates automatically every 8 seconds
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player leaves the splash screen open

```gherkin
Given the splash screen is visible with hint H1
When  8 seconds elapse
Then  the hint changes to a new value H2
And   after another 8 seconds the hint changes again to H3
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Consecutive hints are never immediately identical
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Hint rotates while at least 2 hints exist in the pool

```gherkin
Given the hints pool contains more than one string
When  the hint rotates
Then  the new hint is always different from the immediately preceding hint
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — All shown hints come from the canonical hints pool
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Multiple rotations occur

```gherkin
When  the hint rotates several times
Then  every hint displayed is a member of the known hints array in hints.ts
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Hint fades out before changing text
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Rotation transition plays

```gherkin
When  it is time to rotate the hint
Then  the splash-hint element receives the CSS class "splash-hint--fade"
And   400 ms later the class is removed and the new hint text is visible
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — hints.ts data integrity
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Build-time data contract

```gherkin
Given the hints data module is imported
Then  the hints array contains exactly 20 entries
And   every entry is a non-empty string
And   randomHint() always returns a string that is present in the array
```

---

## Implementation Notes

- Component: `ui/src/components/SplashHint.tsx`
- Data: `ui/src/data/hints.ts`
- Rotation interval: 8 000 ms
- Fade transition: 400 ms opacity via `.splash-hint--fade` CSS class
- The old `providerHint()` helper in `App.tsx` is removed; provider config lives in the Header
