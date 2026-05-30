/**
 * Splash-screen hints shown randomly before a session starts.
 * Mix of party flavour, world lore, PF1e mechanics, and tool tips.
 */
export const hints: string[] = [
  // ── Party ───────────────────────────────────────────────────────────────
  "Yanyeeku's two fox tails sway with restless energy — in kitsune tradition, each tail is a mark of growing power.",
  "Vanx hails from the Shackles, where 'savage technologist' means shoot first and philosophise later.",
  "Ani is Emberkin — when excitement surges through her, fire burns visibly beneath her skin. Approach with warmth.",
  "Both Yanyeeku and Vanx worship Cayden Cailean, the god of freedom, ale, and accidental heroism.",
  "Ani worships Irori, the god of self-perfection. Her fists are her holy symbol.",

  // ── World lore ──────────────────────────────────────────────────────────
  "Sandpoint is built directly atop Thassilonian catacombs. The locals know, and mostly try not to think about it.",
  "The ancient empire of Thassilon was ruled by seven Runelords, each embodying one of the seven mortal sins.",
  "The Sihedron Rune — a seven-pointed star — is the unified symbol of Thassilonian sin magic. Seeing it is rarely a good omen.",
  "Varisia is a frontier land. The ruins beneath your boots predate most living nations.",
  "Desna, goddess of dreams and stars, is beloved across Varisia. Her symbol is a butterfly; her followers trust in luck and wandering.",
  "Pharasma judges every mortal soul after death. There is no afterlife, good or bad, without her verdict.",

  // ── PF1e mechanics ──────────────────────────────────────────────────────
  "Flanking two allies on opposite sides of an enemy grants +2 to attack rolls. Positioning wins fights.",
  "Aid Another lets you sacrifice your action to give an ally +2 to their next attack roll or +2 AC. Teamwork is free damage.",
  "A readied action lets you interrupt an enemy's turn. Declare the trigger clearly before their movement.",
  "Knowledge checks identify creature types and reveal their weaknesses — even a partial result is information the GM can use.",
  "Charging gives +2 to attack but −2 AC until your next turn. Only commit if you can see the fight through.",
  "Taking 10 on a skill check (when not under threat) is almost always better than rolling and hoping.",
  "Combat manoeuvres — trip, disarm, grapple — compare CMB vs CMD. Landing one can completely change a fight's momentum.",
  "A full-attack action only applies if you haven't moved. If you need to close the gap, you get one attack — choose wisely.",

  // ── Tool tips ───────────────────────────────────────────────────────────
  "Use the active speaker button in the sidebar to speak as a specific character. The GM will address them directly.",
]

/** Return a randomly selected hint each call. */
export function randomHint(): string {
  return hints[Math.floor(Math.random() * hints.length)]
}
