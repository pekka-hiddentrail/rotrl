# FEATURE — [Feature Name]

**ID:** SPEC-NNN
**Status:** Draft | Review | Approved | Done
**Area:** Backend | Frontend | Content | Infrastructure
**Tags:** @ui @quality-of-life ...

---

## Story

> As a **[player / GM / developer]**,
> I want **[capability or behaviour]**,
> so that **[the value it delivers]**.

*One or two sentences of plain-English context. What problem does this solve and why does it matter here?*

---

## Background

*Preconditions that apply to all scenarios below. Delete this section if there are none.*

- Given a session has been booted with a valid session ID
- And the LLM provider is available

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — [Happy path title]
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** [What the user does in the normal case]

```gherkin
Given [the initial state or precondition]
When  [the action the user or system takes]
Then  [the observable outcome]
And   [any additional outcomes]
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — [Edge case or alternate path title]
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** [What happens in this variant]

```gherkin
Given [the initial state]
When  [the variant action or condition]
Then  [the expected outcome]
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — [Failure / error case title]
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** [What happens when something goes wrong]

```gherkin
Given [the initial state]
When  [the action that causes the failure]
Then  [the error handling behaviour]
And   [the system state after the failure]
```

---

## Out of Scope

*What this spec explicitly does NOT cover. Prevents scope creep.*

- [Thing we are not doing]
- [Thing covered by a different spec — link it]

---

## Notes

*Design decisions, open questions, links to related specs or code.*

- Related: [SPEC-NNN — Feature Name](SPEC-NNN_feature_name.md)
- See: [SPEC_INDEX.md §N](../SPEC_INDEX.md)
