# Contributing (read this before your first commit)

This project uses **Spec-Driven Development (SDD)**: every feature has a written spec *before* code is written against it. The spec is the contract — if the code and the spec disagree, that's a bug in one of them, and you fix the mismatch before merging either way.

## The loop, per task

1. **Claim it.** Open the [Issues board](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues), assign yourself to the task's issue, move it to "In Progress". This is the whole collision-avoidance mechanism — an assigned issue means hands off unless you talk to the owner. See [TASKS.md](TASKS.md).
2. **Read the spec.** `specs/<number>-<name>/spec.md` has the Specification, Acceptance Criteria, and an Implementation Tasks checklist. It already names the exact files you'll touch, scoped to avoid overlapping another task's files.
3. **Branch from master.** `git checkout master && git pull && git checkout -b feature/<number>-<name>` — use the exact branch name printed at the top of the spec.
4. **Implement against the spec.** Tick the Implementation Tasks checkboxes in the spec file itself as you go, in the same commits as the code. If you find you need to deviate from the spec (a field is missing, an endpoint shape doesn't work), edit the spec file first, in its own commit, so the PR shows the decision was made deliberately, not discovered by an accident and improvised.
5. **Open a PR into `master`.** Use the PR template. Link the issue with `Closes #<n>`. Fill in which Acceptance Criteria you verified and how.
6. **Get it merged before starting your next task.** Do not stack a second feature branch on top of an unmerged one — `master` must stay in a working, demoable state at every merge, since anyone could pull it at any time to keep working.
7. **Pull `master` before branching again**, so your next branch starts from everyone else's latest merged work.

## Why one branch at a time, merged before the next

With a small team on a tight clock, the failure mode isn't "not enough parallel work" — it's two people quietly duplicating the same file, or a demo that doesn't run because three half-finished branches never got integrated. Sequencing "branch -> PR -> merge -> next branch" per person keeps `master` demoable at every point in the hackathon, so if time runs out early, whatever is merged is what you show judges.

You can still parallelize *across* people — see "Suggested parallel lanes" in [TASKS.md](TASKS.md) for which tasks have no file overlap and can run at the same time on different people's machines. The rule is: don't stack your own next task before your current one merges, and don't start a task someone else has already claimed.

## Branch naming

`feature/<spec-number>-<short-name>`, exactly matching the spec folder name, e.g. `feature/004-public-query-widget`.

## Commit messages

Plain description of what changed and why, referencing the spec number, e.g. `feat(004): add confidence badge to public widget response`.

## Before you open a PR

- [ ] All Implementation Tasks checkboxes in your spec are ticked (or the spec explains why not)
- [ ] `docker-compose up` still brings the whole stack up cleanly
- [ ] Tests you added pass locally
- [ ] You didn't touch a file another open spec lists under its own Implementation Tasks — if you had to, you flagged it in the PR description

## If two people need the same file

It happens — `main.py` router registration and `App.tsx` routing are shared touch points by nature. Whoever's PR merges second rebases onto master and resolves the (usually trivial) conflict. Don't avoid this by skipping router/route registration — an unregistered endpoint or view is worse than a two-line merge conflict.
