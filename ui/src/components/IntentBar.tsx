interface IntentState {
  npc: string | null
  npc_trigger: string | null
  skill: string | null
  skill_trigger: string | null
  location: string | null
  location_npcs: string[]
}

interface Props {
  intent: IntentState | null
  lastInput: string
  streaming: boolean
}

export default function IntentBar({ intent, lastInput, streaming }: Props) {
  const hasInput = lastInput.length > 0

  return (
    <div className="intent-bar" title="Intent detection — what context was injected for the last player input">
      <span className="intent-bar-label">intent</span>

      {!hasInput && (
        <span className="intent-idle">—</span>
      )}

      {hasInput && (
        <span className="intent-input" title={lastInput}>
          "{lastInput.length > 52 ? lastInput.slice(0, 52) + '…' : lastInput}"
        </span>
      )}

      {hasInput && (
        <span className="intent-sep">→</span>
      )}

      {/* Still streaming — waiting for context event */}
      {hasInput && !intent && streaming && (
        <span className="intent-detecting">detecting…</span>
      )}

      {/* Streaming done but no context event received (backend not restarted?) */}
      {hasInput && !intent && !streaming && (
        <span className="intent-no-event">no event — restart backend?</span>
      )}

      {/* Context event received */}
      {hasInput && intent && (
        <>
          {intent.npc ? (
            <span className="intent-tag intent-npc">
              <span className="intent-tag-kind">npc</span>
              <span className="intent-tag-name">{intent.npc}</span>
              {intent.npc_trigger && (
                <span className="intent-tag-trigger">"{intent.npc_trigger}"</span>
              )}
            </span>
          ) : (
            <span className="intent-tag intent-none-tag">no npc</span>
          )}

          {intent.skill ? (
            <span className="intent-tag intent-skill">
              <span className="intent-tag-kind">skill</span>
              <span className="intent-tag-name">{intent.skill}</span>
              {intent.skill_trigger && (
                <span className="intent-tag-trigger">"{intent.skill_trigger}"</span>
              )}
            </span>
          ) : (
            <span className="intent-tag intent-none-tag">no skill</span>
          )}

          {intent.location && (
            <span className="intent-tag intent-location">
              <span className="intent-tag-kind">loc</span>
              <span className="intent-tag-name">{intent.location}</span>
              {intent.location_npcs.length > 0 && (
                <span className="intent-tag-trigger">{intent.location_npcs.join(', ')}</span>
              )}
            </span>
          )}
        </>
      )}
    </div>
  )
}
