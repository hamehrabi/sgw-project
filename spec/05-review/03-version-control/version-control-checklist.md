# Version Control / GitHub Workflow Checklist

> Source: Appendix L + Ch. 15.
> GitHub-**compatible**, not GitHub-**dependent**. Use the same flow with any platform, a
> local Git repository, or a structured review folder. The habit is *controlled change*,
> not a specific website.

---

## Why AI coding needs version control discipline (Ch. 15 §15.1)

| AI coding risk | Version control response |
|---|---|
| The agent changes more files than expected | Review the diff before accepting the change. |
| The agent mixes multiple features together | Use one branch or change set per task. |
| The agent removes working behavior | Compare against the previous commit and restore safely. |
| The agent fixes a bug but breaks a requirement | Run tests and check the requirement ID before merging. |
| You forget why a file changed | Use clear commit messages linked to specs and tasks. |

> **Working rule:** do not let the agent make a large uncontrolled change and then ask you
> to trust it. Let the agent work in small steps. Review each step. Commit only the work
> you understand.

Every row applies here, because CON-008 says an agent builds every task. **The first row is the
one with no automated backstop:** no test can tell you a file appeared that nobody asked for.
Reading the changed-file list before the code is the entire control.

---

## Before work starts

- [ ] Requirement ID and task ID are known.
- [ ] The branch or working copy has a clear purpose.
- [ ] The agent has the current context pack.
- [ ] Acceptance criteria and tests are listed.
- [ ] Out-of-scope files and behaviors are named.

**Branch naming**
```
feature/REQ-AUTH-006-login-lockout
fix/REQ-TASK-004-due-date-validation
chore/TASK-012-config-cleanup
```

Applied here:
```
feature/TASK-001-signin-and-shell
feature/TASK-003-ranked-risk-list
fix/BUG-001-unscored-asset-dropped
chore/TASK-010-wire-fitness-functions
```

## During work

- [ ] Changes are small enough to review.
- [ ] Commit or change notes explain **why** the change exists.
- [ ] Tests are added or updated **with** the code.
- [ ] No unrelated formatting or dependency changes are mixed in.
- [ ] Secrets and credentials are not committed.

**Two more, specific to this workspace:**

- [ ] **The database file is not committed.** `spec/.gitignore` covers `*.db` and the scenario
      upload directory. Both hold critical-infrastructure asset locations.
- [ ] **Nothing under `01-docs/` is in the diff.** The specification is an input to every task.
      A requirement in a feature commit means either the method was inverted or the change
      belongs in `01-docs/09-change-control/spec-change-log.md` first.

**Commit message format (Ch. 15 §15.3)**
```
type(scope): action linked to requirement ID
```

| Weak commit message | Better commit message |
|---|---|
| `update login` | `feat(auth): add login validation for REQ-AUTH-002` |
| `fix bug` | `fix(api): reject missing project name for REQ-PROJ-003` |
| `tests` | `test(tasks): add due-date validation tests for REQ-TASK-004` |
| `changes` | `docs(spec): update task status rules after review` |

| Change type | Suggested message |
|---|---|
| New intent document | `docs(intent): add engineering intent for [project]` |
| Updated requirements | `docs(spec): refine task creation requirements and acceptance criteria` |
| New task file | `docs(tasks): add TASK-001 for task creation API` |
| Test plan added | `test(tasks): add acceptance and failure tests for task creation` |
| Implementation completed | `feat(tasks): implement TASK-001 task creation workflow` |
| Review notes added | `docs(review): record review results for TASK-001` |

## Pull request / review package

- [ ] Summary explains the requirement and behavior changed.
- [ ] Linked issue/task references the requirement ID.
- [ ] Test results are included.
- [ ] Security and data changes are called out clearly.
- [ ] Reviewer can see files changed, risks, assumptions, and rollback notes.

## Merge

- [ ] All checks pass — do not merge failing checks.
- [ ] Reviewer approval recorded.
- [ ] Traceability matrix updated.
- [ ] Specs updated if behavior changed.

**"All checks" means the test suite *and* the six fitness functions.** They are separate things:
the suite proves the features behave, the fitness functions prove the structure has not moved.
A gate that runs one and not the other lets FF-002 — no view imports the scoring module — decay
silently while every feature test stays green. TASK-010 wires them; until it does, that box is a
manual check, and this line says so rather than implying a gate that does not exist.

---

## Review order before merging (Ch. 15 §15.7)

1. Read the requirement and acceptance criteria again.
2. Check the list of changed files **before** reading the code.
3. Inspect the diff for unexpected deletions or unrelated edits.
4. Run or review the tests connected to the requirement.
5. Check error handling, validation, and security-sensitive paths.
6. Update the traceability matrix and specs if a documented decision changed.
7. Commit or merge only after you understand the change.

---

## Baseline repository setup (Ch. 15 §15.2)

Track more than code — track the documents that explain why the code exists.

```
git init
git status
git add 01-intent 02-specs 03-tasks 04-tests 05-reviews 06-release agent src tests ops README.md .gitignore
git commit -m "chore(project): create initial spec-driven workspace"
```

The first commit should not contain random code. It creates a clean baseline you can
return to before the AI agent starts changing files.

**That baseline is exactly what this workspace is.** Nothing has been built; `spec/` holds the
specification and nothing else. Committing it now, before TASK-001, gives the one thing a
rollback needs and nobody creates later: a known-good state that contains the intent and none of
the code.

**Branch workflow**
```
git checkout main
git pull                      # if you use a remote repository
git checkout -b feature/REQ-AUTH-006-login-lockout

# Let the agent work on one task.
# Review the files.
# Run the tests.

git status
git diff
git add src tests 02-specs
git commit -m "feat(auth): add login lockout for REQ-AUTH-006"
```

If you are not using a remote repository, use branches locally. The important habit is
**isolation, review, and traceability** — not the hosting platform.

---

## Alternative tracking methods (Ch. 4 §4.8)

| Method | Best for | How to use it |
|---|---|---|
| Simple change log | If you are not ready for Git. | Write dated entries in `05-review/change-log.md`. |
| Local Git | Version history without publishing online. | Commit after meaningful spec, task, test, or code changes. |
| Manual snapshots | A simple backup method. | Copy the project folder before major changes and label it clearly. |

The second row is the one to choose. A remote is optional here and carries a real
consideration — this workspace and its future data describe critical infrastructure, and a
hosting decision is a security decision rather than a convenience.

---

> Blueprint: blueprints/05-review/03-version-control/version-control-checklist.md
