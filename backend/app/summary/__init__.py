"""The situation summary layer (CHG-040, CHG-052).

Three parts, and the boundaries between them are the design:

- `figures`  — assembles the fixed set of figures the model may see. Reads the store.
- `draft`    — the server-side model call, and the templated fallback that needs no model.
- `verify`   — **pure.** Judges a draft against the supplied figures and nothing else.

The permitted import direction is `api → summary → store`. `verify` imports nothing from
any other module, so the check that decides whether generated text may be shown can be
tested against a string — which is how a guardrail stays testable after the thing it
guards gets more capable.
"""
