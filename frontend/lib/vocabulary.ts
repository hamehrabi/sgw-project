/**
 * The frozen vocabulary, as types (client brief §6).
 *
 * Render these strings exactly. Never "Critical", never "Standard", never "HIGH", never
 * a numeric score in a table; confidence is words and never a percentage; reason
 * strengths are never percentages and never numbers summing to 100. A component that
 * takes one of these types cannot be handed the wrong word — that is the point of the
 * types existing, and it is why every badge and label imports from here rather than
 * spelling a string of its own.
 */

export type RiskBand = 'High' | 'Medium' | 'Low'
export type DecisionAction = 'Accept' | 'Adjust' | 'Dismiss'
export type SummaryState = 'Draft' | 'Approved' | 'Sent'
export type ReasonStrength = 'Strong' | 'Moderate' | 'Slight'

export const RISK_BANDS: readonly RiskBand[] = ['High', 'Medium', 'Low']
