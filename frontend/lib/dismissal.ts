/**
 * The two rules about a dismissal reason that the browser has to agree with the server about
 * (REQ-F-008, CHG-033, CHG-037).
 *
 * **This file exists because the same rule was written in three places and the three
 * disagreed.** The schema enumerated six ASCII whitespace characters, `store/dispatch.py`
 * repeated the same six, and this layer used `String.prototype.trim()`, which is Unicode-aware
 * — so a reason of U+00A0, U+2003, U+200B or U+FEFF left the button disabled
 * here and was answered `201` and stored by the server. The strictest of the three definitions
 * was the browser's, which is the layer ADR-002 says enforcement must never live in, and it is
 * exactly why nobody could see the hole: only a caller reaching the API ever met it.
 *
 * **Neither number nor alphabet is the rule and neither must be read as one.** The store refuses
 * a blank or over-length reason independently; what this buys is a field that cannot grow past
 * what a `400` would refuse and a button that is not offered for an action whose only possible
 * answer is a refusal. `test_one_alphabet_decides_what_is_blank_in_every_layer` and
 * `test_the_browser_bounds_a_dismissal_reason_at_the_number_the_store_does` read this file and
 * require both copies to match the server's — *a rule written in more than one place needs
 * something that fails when the copies disagree*.
 *
 * It is its own module rather than part of `lib/api.ts` so the browser suite can import the
 * same two values instead of repeating them a fourth time as literals.
 */

/** The longest reason the server will store. Mirrored from `dispatch.DISMISSAL_REASON_MAX`. */
export const DISMISSAL_REASON_MAX = 2000

/**
 * What counts as blank. Mirrored from `dispatch.BLANK_CODEPOINTS`, in the same order.
 *
 * The six ASCII ones, the four information separators, Unicode's `White_Space` additions, and
 * the two invisibles that are *not* `White_Space` and are exactly what somebody types when they
 * want a reason field to look filled in: U+200B and U+FEFF.
 */
export const DISMISSAL_BLANK_CODEPOINTS = [
  0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001,
  0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x200b, 0x2028, 0x2029,
  0x202f, 0x205f, 0x3000, 0xfeff,
]

const CLASS = DISMISSAL_BLANK_CODEPOINTS.map((point) => `\\u{${point.toString(16)}}`).join('')
const ENDS = new RegExp(`^[${CLASS}]+|[${CLASS}]+$`, 'gu')

/**
 * The reason as the server will store it — trimmed with the shared alphabet, nothing else done
 * to it.
 *
 * **It does not enforce the bound**, and that is deliberate: a reason one character too long is
 * a `400` a dispatcher has to be shown, with what they typed still in front of them (FTEST-005),
 * not a button that silently will not press. Absence is the only thing this layer refuses to
 * send, and only because sending it could not succeed.
 */
export function trimDismissalReason(value: string): string {
  return value.replace(ENDS, '')
}
