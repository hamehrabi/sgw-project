/**
 * What counts as blank, for the whole browser half (CHG-037, CHG-039).
 *
 * **This file used to be `lib/dismissal.ts` and it used to be about one field.** CHG-037 tied
 * three copies of this alphabet together — the schema, `store/dispatch.py`, and the browser —
 * after a dismissal reason of one no-break space was answered `201` and stored. The tie held.
 * What it did not do was reach the other fields a person types into, and each of those went on
 * using `String.prototype.trim()`:
 *
 *   - `PlacementForm`'s crew label. JavaScript's `trim()` removes U+FEFF and does **not** remove
 *     U+200B, Python's `str.strip()` removes neither, and SQLite's one-argument `trim()` strips
 *     spaces alone — so `POST .../placements` with a crew of one zero-width space was answered
 *     `201` and written into `decision_records`, which BR-004 forbids correcting.
 *   - `ScenarioUploadPanel`'s storm name and source note. `trim()` removes U+00A0 and the
 *     server's six-ASCII alphabet did not, so a storm named U+00A0 was stored and the switcher
 *     rendered a row with no visible label.
 *
 * In both, this layer was the **strictest** of the three, which is why nothing on screen ever
 * looked wrong: the button stayed disabled and only a caller reaching the API met the hole.
 * `AGENT.md` records that shape — *a rule that exists in several layers is only as strong as its
 * weakest layer, and only as visible as its strictest one*.
 *
 * **None of this is the enforcement** (ADR-002). The store refuses a blank value independently,
 * in `char(...)` in migrations 015 and 016. What this buys is a field that cannot offer an
 * action whose only possible answer is a refusal, and one definition of blank that a test can
 * fail on when a copy moves.
 */

/**
 * The alphabet, mirrored from `store/blanks.BLANK_CODEPOINTS`, in the same order.
 *
 * **This array has exactly one home in the browser half and
 * `test_one_alphabet_decides_what_is_blank_in_every_layer` is what says so** — it counts the
 * homes before it compares any of them, and two would be a failure even if both were right,
 * because two copies that agree today are two copies.
 *
 * The six ASCII ones, the four information separators, Unicode's `White_Space` additions, and
 * the two invisibles that are *not* `White_Space` and are exactly what somebody types when they
 * want a field to look filled in: U+200B and U+FEFF.
 */
export const BLANK_CODEPOINTS = [
  0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001,
  0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x200b, 0x2028, 0x2029,
  0x202f, 0x205f, 0x3000, 0xfeff,
]

const CLASS = BLANK_CODEPOINTS.map((point) => `\\u{${point.toString(16)}}`).join('')
const ENDS = new RegExp(`^[${CLASS}]+|[${CLASS}]+$`, 'gu')

/**
 * The value as the server will store it — trimmed with the shared alphabet, nothing else done
 * to it.
 *
 * **It enforces no bound**, and that is deliberate wherever it is used: a value one character
 * too long is a `400` the person has to be shown with what they typed still in front of them
 * (FTEST-005), not a button that silently will not press. Absence is the only thing this layer
 * refuses to send, and only because sending it could not succeed.
 */
export function trimBlank(value: string): string {
  return value.replace(ENDS, '')
}

/** True when the value is made of nothing anybody could see. The reason a button is disabled. */
export function isBlank(value: string): boolean {
  return trimBlank(value).length === 0
}
