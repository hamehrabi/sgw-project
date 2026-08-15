# backup-and-recovery.md — Availability, Backup, Restore

> **Purpose:** what happens when you lose the data, not just the release.
> **When you use it:** before first production deploy. Reviewed quarterly.
> **Note:** `rollback-plan.md` covers reversing a **release**. This covers losing **data**.

> **A backup you have never restored is not a backup — it is a hope.**
> The restore is the feature. The backup is just its input.

---

## 1. Availability target

State it as a number, then translate it — most people agree to "three nines" without
knowing what they agreed to.

| Uptime | Downtime / year | Downtime / month |
|---|---|---|
| 99.0% | 87 h 46 min | 7 h 18 min |
| 99.9% | 8 h 46 min | 43 min |
| 99.99% | 52 min | 4 min 23 s |
| 99.999% | 5 min 35 s | 26 s |

| Item | Value |
|---|---|
| Target uptime | **99.0%** — about 7 h 18 min a month. It follows from the four-hour recovery objective below: a single container on one VM cannot promise better, and promising better would require redundancy that ADR-001 and ADR-002 deliberately do not buy. |
| Measured how | An external check on the health endpoint, one-minute interval. Not from inside the container — a process checking its own liveness reports success right up to the moment it stops. |
| Planned maintenance excluded? | Yes, announced in advance. **With one exception that is the point of this whole product: never during a storm.** A maintenance window is a business-hours decision; a hurricane is not. |
| Who is told when it is breached | [TODO: name the person — see Q-026] |

> Each extra nine costs roughly an order of magnitude more. **Pick the one the business
> will actually pay for**, not the one that sounds serious.

**99.0% is honest and it is also uncomfortable**, and the discomfort is worth stating rather
than smoothing over. Seven hours a month is fine for a tool used on ordinary days and
potentially disastrous for one used during a hurricane — the availability that matters here is
not annual, it is *availability during the twelve hours anyone actually needs it*. Version one
is a probe on prepared data, so the number is survivable. **It stops being survivable the day
this platform is used in a real storm**, and that is the revisit trigger.

## 2. RTO and RPO — the two numbers that matter

| Term | Question it answers | Your answer |
|---|---|---|
| **RTO** — Recovery Time Objective | How long may we be **down**? | **4 hours** (Round 8) |
| **RPO** — Recovery Point Objective | How much **data** may we lose? | **24 hours** (Round 8) |

Your RPO **is** your backup frequency. Nightly backups mean an RPO of 24 hours — say that
out loud to whoever owns the data before you write it down.

**Said out loud, for this system:** a 24-hour RPO means that after a restore, **up to a day of
decision records is gone.** Scenarios can be re-uploaded and rankings recomputed — those are
cheap. The decision record cannot be reconstructed from anything, and it is the artifact the
platform exists to produce for a regulator. A day of it is an acceptable loss for a probe on
prepared data. It would not be acceptable for a platform used during a real storm, which is the
same revisit trigger as the availability target.

## 3. What is backed up

| Asset | Method | Frequency | Retention | Where | Encrypted |
|---|---|---|---|---|---|
| Database file | File copy — the whole store is one file (ADR-002) | Nightly | 90 days rolling; the decision record inside it is retained indefinitely (Q-015) | Off the VM, different failure domain from the running host | Yes; key held separately |
| Uploaded scenario files | File copy | Nightly, with the database | Same | Same | Yes |
| Secrets / config | Manual export on rotation | On rotation | current + 1 | Outside the platform | Yes |
| Audit log | It is inside the database file | With the database | See Q-015 | With the database | Yes |

☐ **Not backed up on purpose:** computed risk scores — *why:* they are re-derivable from the
scenario and the scoring rule version, both of which are backed up. **This one deserves a
caveat rather than a clean tick:** re-deriving them requires the same rule *and the same
weights*, and Q-025 makes weight changes the expected activity. Every ranking records the
scoring-rule version that produced it (`ai-boundary-spec.md` §7) precisely so this remains true.
If that ever stops being recorded, risk scores must start being backed up.

**The backup being a file copy is ADR-002's dividend.** It is the reason a tighter RPO would be
cheap here — a copy on a schedule rather than a replication cluster — and the reason 24 hours is
a choice rather than a limit.

## 4. Restore procedure

```
1. Stop the application container.
2. Restore the database file and the scenario upload directory from the most recent
   backup, onto the persistent disk.
3. Start the container.
4. CONFIRM BOTH decision_records TRIGGERS EXIST. A restored file is only as good as the
   constraints it carries, and BR-004's entire enforcement is those two triggers.
5. Run the production smoke steps.
6. Confirm the most recent decision record, and record how much was lost.

Estimated restore time:   [TODO: has a restore been performed and timed? — see Q-028]
                          One rehearsal is required BEFORE the demo. Until the row in
                          §5 exists, the 4-hour objective is a hypothesis.
Verification after restore: smoke test, trigger check, newest-decision check
Who can perform it:        [TODO: name — see Q-026]
Who must approve it:       [TODO: name — see Q-026]. A restore discards every decision
                           recorded since the backup, which is evidence, not just data.
```

**Step 4 is not boilerplate.** A restored database file that has lost its triggers looks
completely healthy: every screen works, every test passes, and the decision record is silently
editable from that moment on.

## 5. Restore test log

> The one row that makes this file real.

| Date | What was restored | Into | Time taken | Result | Issues found |
|---|---|---|---|---|---|

**Empty, and that is the single most important gap in this file.** Every row above is a plan;
none of it is evidence. The restore time is a `[TODO]` because nobody has measured one, and
until somebody has, the four-hour RTO is an aspiration rather than a commitment. **Perform one
restore into a test environment before the first production deploy**, time it, and write the row.

## 6. Failure scenarios

| Scenario | Detected by | Response | Data loss | Owner |
|---|---|---|---|---|
| Single instance dies | External health check | Restart or replace the container | None | [TODO: who owns this response? — see Q-026] |
| Database file corruption | Failed queries, error alert | Restore from the most recent backup | Up to 24 h — including decision records | [TODO: who owns this response? — see Q-026] |
| A migration drops a trigger | **FF-004**, and the post-deploy trigger check | Re-apply the trigger; audit what was written meanwhile | None, but the audit guarantee lapsed for that window | [TODO: who owns this response? — see Q-026] |
| Accidental scenario delete | User report | Re-upload the prepared files; re-rank | None — scenarios are re-derivable | [TODO: who owns this response? — see Q-026] |
| Persistent disk lost | Instance fails to start | Restore both the database file and the upload directory | Up to 24 h | [TODO: who owns this response? — see Q-026] |
| Provider or region outage | External check | **Accepted.** Wait for the provider. Multi-region contradicts the single-instance decision. | None | — |
| Credential compromise | Audit log, error alert | Rotate `SESSION_SIGNING_KEY` — which signs everyone out — and restore if data was altered | Up to 24 h | [TODO: who owns this response? — see Q-026] |

**The third row does not appear in the blueprint's list and is the one most likely to happen
here.** It is not data loss and it is not downtime; it is the quiet loss of a guarantee, and it
is the only failure in this table that leaves the system fully working while being wrong.

## 7. Checklist

- [x] RTO and RPO agreed **with the business**, not chosen by engineering alone — Round 8
- [ ] Backups run automatically and **alert on failure** *(a silent backup job is the most common failure)*
- [ ] Backups live in a **different failure domain** than production
- [ ] Backups are encrypted, and the key is not stored with them
- [ ] **A restore has been performed and timed** — at least once
- [ ] Restore time is within RTO
- [ ] Someone other than the author can perform the restore
- [ ] One backup copy is offline or immutable *(ransomware)*
- [ ] Retention satisfies any legal or contractual requirement

**Eight of nine unticked, and they are not all the same kind of gap.** Rows 2 to 4 are planned
and unbuilt — they become true when the deployment is built. Rows 5 and 6 are the ones that
cannot be resolved by planning: **a restore has to be performed.** Row 7 needs a name (Q-026).
Row 9 needs a retention period (Q-015), and for a decision record that is evidence for a
regulator, "however long the disk lasts" is not an answer anybody has given.

---

> Blueprint source: this file is new to the template — added to close the
> availability / backup / recovery layer.

---

> Blueprint: blueprints/07-ops/01-deployment/backup-and-recovery.md
