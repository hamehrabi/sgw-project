# Project Brief

> Source: Ch. 16 §16.2 — Project Brief Template.
> Plain language. Not technical. Written before requirements exist.

**Project name:** SGW Resilience Platform

**Problem you want to solve:** When a storm is one to three days away, SGW's operations
manager must decide where to place repair crews — and during the storm the dispatcher must
decide what gets repaired first. Both decisions are made well by capable people, but the facts
they need sit in four systems that do not share data, so the plan is assembled by hand and the
damage picture is held in someone's head.

**Primary users:** The operations manager, who places crews before the storm, and the
dispatcher, who orders the repairs during it.

**Main outcome:** Storm decisions are made from one current, shared set of facts. The plan
adjusts when the forecast changes instead of being rebuilt from zero, and the record of what
was decided exists afterwards.

**Must-have features:**
- A joined asset view — one record per asset, built from prepared data files, with the source and age of every value visible
- A list of assets ranked by risk, each rank carrying a plain-words reason
- A planning view for the operations manager, for placing crews before the storm
- A dispatch board for the dispatcher, showing damage and repair jobs during it

**Out-of-scope features:**
- Live connections to the four source systems — version one runs on prepared data
- Water early-warning on sensor readings
- The automatic summary writer for leadership
- The offline crew app, field photo capture, and route planning

**Known constraints:**
- An internal dashboard for a team inside one company, not a public or customer-facing product.
- Under 50 users in the first six months.
- A build horizon of about one week for version one.
- No paid third-party services.
- Certain data must not be stored; which data has not yet been named — see Q-007.

**Success signal:** The operations manager builds or adjusts a storm plan in under an hour
including after a forecast change, and the dispatcher reaches one full damage picture in under
five minutes. Both figures are carried from the source PRD (§9) rather than set in this
interview — see Q-005.

---

## Separate vision from implementation (Ch. 2 §2.2)

Write these in two columns. Do not let implementation ideas contaminate the vision.

| Vision statement (what should improve) | Implementation idea (how it might be built) |
|---|---|
| You want the operations manager to place crews on evidence rather than recollection, and to keep that plan valid when the forecast moves. | You may need one joined record per asset, a ranked risk list that re-ranks on a forecast update, and a plain-words reason beside each rank. |
| You want the dispatcher to hold one current picture of damage instead of assembling one from radio, alarms and a whiteboard. | You may need a live shared list of damage and repair jobs, and a one-click way to dismiss a false alarm. |
| You want the executive to answer a regulator with numbers instead of recollection. | You may need a time-stamped summary of outages, crews and repair estimates, and a stored record of every decision. |

---

## Raw-idea interrogation (Ch. 2 §2.1)

| Question | Answer |
|---|---|
| Who is this for? (the actual user, not the requester) | The operations manager and the dispatcher, who make the two decisions the product exists to support. The field crew lead and the executive consume its output. |
| What problem hurts enough to solve? | The facts are scattered across four systems, so the plan is rebuilt by hand every time the forecast moves and the damage picture lives in one person's head. |
| What outcome should improve? | Storm decisions made from one current shared set of facts, adjusted rather than restarted, and recorded rather than remembered. |
| What must the system **not** do? | It must not act. It recommends; a person decides. It may only read from the systems that physically control the grid and the water network, and can never send them commands. |
| What constraints already exist? | Internal dashboard, a team inside one company, under 50 users, about one week to build version one. Anything beyond that is unrecorded — see Q-003. |

---

## Problem statement formula (Ch. 2 §2.3)

> [Affected user] currently faces [difficulty], which causes [consequence].
> The system should [desired improvement].

**Your problem statement:** SGW's operations manager, dispatcher, field crew leads and
executives currently face storm decisions whose supporting facts sit in four systems that do
not share data, which causes the crew plan to be rebuilt by hand whenever the forecast shifts,
the damage picture to be assembled from radio calls and a whiteboard, and no numbers to be
ready when a regulator calls — costing longer outages, penalty fees, premium-priced emergency
crews and rising insurance. The system should bring those scattered facts into one place and
present them ranked by risk with a plain reason beside each, while people continue to make
every decision.

This statement was drawn from the source PRD rather than stated in the interview — see Q-006.

---

> Blueprint: blueprints/01-docs/01-intent/project-brief.md
