/**
 * The one rule about a dismissal reason that is specific to a dismissal: how long it may be
 * (REQ-F-008, CHG-033).
 *
 * **What counts as blank is no longer here** (CHG-039). It was, and it was written as though it
 * were a fact about dismissals — `DISMISSAL_BLANK_CODEPOINTS` — while being a fact about every
 * field a person types into. Two other fields kept `String.prototype.trim()` because the shared
 * definition was filed under a name that did not look like theirs, and both let an invisible
 * character reach the server: a crew label of one U+200B into `decision_records`, where BR-004
 * means it can never be corrected, and a storm name of one U+00A0 onto the switcher a person
 * picks storms out by. The alphabet is `lib/blank.ts` now and this file re-exports the trim so
 * `DismissAlarmControl` and the browser suite keep the name they call it by.
 *
 * **The number is still here, and it is still not the rule.** The store refuses an over-length
 * reason independently. What this buys is a field that cannot grow past what a `400` would
 * refuse, and `test_the_browser_bounds_a_dismissal_reason_at_the_number_the_store_does` is what
 * fails when this copy and `dispatch.DISMISSAL_REASON_MAX` stop matching — *a rule written in
 * more than one place needs something that fails when the copies disagree*.
 */

import { trimBlank } from './blank'

/** The longest reason the server will store. Mirrored from `dispatch.DISMISSAL_REASON_MAX`. */
export const DISMISSAL_REASON_MAX = 2000

/**
 * The reason as the server will store it. The shared trim under the name this field's callers
 * already use — see `lib/blank.ts` for why the alphabet is not defined here any more.
 */
export function trimDismissalReason(value: string): string {
  return trimBlank(value)
}
