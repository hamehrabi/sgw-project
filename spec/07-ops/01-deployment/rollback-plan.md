# Rollback Plan

> Source: Ch. 23 §23.7.
> Rollback means returning to a previous safe version after a release causes problems.
> **A rollback strategy must exist before deployment begins.** If you only start thinking
> about rollback after users are affected, you are already late.
>
> Rollback planning is part of responsible deployment, not a sign of failure.

**Release:**
**Date:**

---

## 1. Last known stable version

| Item | Value |
|---|---|
| Version / tag | |
| Commit SHA | |
| Deployed on | |
| Verified working by | |

**Nothing has been deployed, so there is no last known stable version** — and that is worth
acting on rather than waiting out. The specification workspace as it stands is the natural
baseline: commit and tag it *before* TASK-001, and the first release has something to return to.
A baseline created after the first deploy is a baseline that already contains the code you might
need to remove.

## 2. Restore procedure

```
Application rollback:
1. Stop the running container.
2. Deploy the previous container image, by tag.
3. Leave the database file alone — see section 3.
4. Start the container.
5. CONFIRM BOTH decision_records TRIGGERS EXIST before declaring the rollback complete.
6. Run production smoke steps.

Estimated time to restore:  [TODO: has a rollback been rehearsed and timed? — see Q-028]
Verification after restore: smoke test, trigger check, and one ranking rendered with
                            its reasons
```

**Step 3 is the one that will be got wrong under pressure.** The store is a single file
(ADR-002), so *rolling back the data* means overwriting it — which discards every decision
recorded since the backup. **Roll back the code; leave the data alone.** Restoring data is a
different operation with a different approver, and it belongs in `backup-and-recovery.md`.

## 3. Database rollback rule

| Question | Answer |
|---|---|
| Were there schema changes in this release? | Answered per release. For the first release: yes, everything. |
| Is the down migration tested? | Required. ADR-002 records that a down migration is cheap now precisely because no production data exists, and stops being cheap later. |
| Is a backup / restore point available? | A copy of the database file and the upload directory, taken **before** migrations run. |
| If the schema cannot be reversed, what is the forward-fix plan? | Roll the code forward with a corrective migration. Never restore the data file to undo a schema change unless losing the interval is acceptable. |

> If the migration is **not** reversible, rollback becomes roll-*forward*. Document that
> explicitly — do not discover it during an incident.

**One migration is never reversed as part of a rollback: the one creating the two
`decision_records` triggers.** Dropping them to reverse a schema change removes BR-004's only
enforcement, and nothing in the test suite would report it. If a rollback appears to require
dropping a trigger, stop and treat it as a superseding-ADR decision, not a deployment step.

## 4. Health checks that trigger rollback

| Signal | Threshold | Observation window | Action |
|---|---|---|---|
| Error rate | > 2% of requests | first 30 minutes | Roll back |
| Health endpoint | any non-200 | continuous | Roll back |
| Response time on the ranking | sustained beyond the REQ-NF-001 limit | first 30 minutes | Investigate → roll back if sustained. **The limit itself is unset (Q-012)** |
| Failed sign-ins | above baseline | first 30 minutes | Roll back |
| **A ranking rendered with an item carrying no reasons** | **any occurrence** | immediate | **Roll back immediately** |
| **An `UPDATE` on `decision_records` that succeeds** | **any occurrence** | immediate | **Roll back immediately, and audit the window** |
| **An asset absent from a ranking with no UNSCORED entry** | **any occurrence** | immediate | **Roll back immediately** |

**The last three are pre-authorised, and that is the point of writing them down now.** Each is a
silent failure — no error, no exception, a screen that looks fine — and each defeats one of the
three things this product is for: a rank you can interrogate, a record nobody can edit, and a
list that does not read as safety when it is incomplete. Deciding under pressure whether a
missing asset is "really" an incident is exactly the judgement this table removes.

## 5. Ownership

| Role | Name | Contact |
|---|---|---|
| Release owner | The developer — sole owner for the prototype (Q-026) | |
| **Rollback approver** | **Self-approved for this build.** The three silent triggers in §4 need no approval | |
| On-call during window | The developer | |

**This is the prototype's honest answer, not a placeholder.** Q-026 recorded it verbatim: no real
people exist, SGW is fictional, and one person holds every role. The three silent triggers in §4
are therefore **pre-authorised by construction** — there is nobody to wait for.

**It stops being sufficient the moment a second person is involved**, and that is a production-
planning gap rather than a prototype one. The source PRD names the *operations director* as the
responsible owner for the real platform — a role, flagged in that document as to be confirmed
with the client. Naming a person here would have invented one.

## 6. Communication

```
If users are affected, send:

"[Status] We identified an issue affecting [feature] starting at [time].
We have [rolled back / are rolling back] to the previous version.
[Expected resolution]. We will update at [time]."
```

| Audience | Channel | Who sends it |
|---|---|---|
| Operators using the platform | [TODO: which channel, and who sends it? — see Q-026] | [TODO: which channel, and who sends it? — see Q-026] |
| Stakeholders | [TODO: which channel, and who sends it? — see Q-026] | [TODO: which channel, and who sends it? — see Q-026] |
| Team | [TODO: which channel, and who sends it? — see Q-026] | [TODO: which channel, and who sends it? — see Q-026] |

**One message needs to exist that the template does not cover**, and it is the one nobody wants
to write in the moment: *"a ranking you may have acted on was incomplete."* If the third trigger
in §4 fires, the people affected are not inconvenienced users — they may have placed crews
against a list with an asset missing from it. That notification is part of the rollback, not a
follow-up to it.

---

## Basic rollback strategy contents (Ch. 23 §23.7)

- [ ] The last known stable version.
- [ ] The command or manual step for restoring it.
- [ ] The database rollback rule.
- [ ] The health checks that trigger rollback.
- [ ] The person or role responsible for approving rollback.
- [ ] The communication message if users are affected.

Rows 3, 4 and 6 are written. Rows 1 and 2 need a first deploy. **Row 5 needs a name** (Q-026),
and it is the one that turns this plan from a document into something that happens.

---

## Post-rollback

- [ ] Record the incident in [`../review/debugging-specification.md`](../../05-review/04-debugging/debugging-specification.md).
- [ ] Add a regression test that would have caught it.
- [ ] Update the requirement / spec that was unclear.
- [ ] Update the agent rules if the mistake was AI-generated.
- [ ] Note what signal detected it — and what signal *should* have.

The fourth box will apply almost every time on this project: an agent writes every task
(CON-008), so a rollback caused by generated code is a rollback caused by an instruction that
was not specific enough. The fix belongs in `AGENT.md`'s *Lessons from past mistakes* as well as
in the code.

---

> Blueprint: blueprints/07-ops/01-deployment/rollback-plan.md
