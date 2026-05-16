# Project Development Rules

> This document is project-agnostic by design. Copy it into any repository and
> adapt only the project-specific placeholders: source-of-truth documents,
> verification commands, branch naming conventions, and domain boundaries.

## Operating Principles

- **Evidence before claims**: never state that something works until a fresh
  verification command proves it.
- **Root cause before fixes**: do not propose or implement a fix before the
  failing behavior is understood and reproduced.
- **Plan before implementation**: non-trivial work needs an explicit plan with
  acceptance criteria before code changes begin.
- **Tests before behavior changes**: bug fixes and new behavior start with a
  failing test whenever the project has a test harness.
- **Minimal impact**: change only the files required for the task. Avoid
  opportunistic refactors.
- **Documentation is part of the work**: workflow logs, README updates, and
  handoff notes are first-class deliverables.

## Iron Laws

These are hard constraints. Do not bypass them by arguing the task is small,
urgent, obvious, or low risk.

```text
1. No design decision without context.
2. No implementation plan without clear scope and acceptance criteria.
3. No implementation for changed behavior without a failing test, unless tests
   are impossible or explicitly out of scope.
4. No completion claim without verification evidence.
5. No bug fix without root cause analysis.
6. No project-core layer should hard-code business or customer-specific rules
   that belong in configuration, data, plugins, tools, or adapters.
```

## Source Of Truth

Every project should define its authoritative references before work begins:

- product or requirements documents
- architecture documents
- API contracts and schemas
- design assets or UX specifications
- operational runbooks
- existing code patterns and tests

When implementation conflicts with the source of truth, update the source of
truth first or document the discrepancy before changing code.

## Task Workflow

Use this workflow for non-trivial tasks: new features, bug fixes, refactors,
architecture changes, test strategy changes, or multi-file documentation work.

### Phase 0: Context And Design

Before planning or coding:

1. Read the relevant source-of-truth documents and nearby code.
2. Identify current behavior, desired behavior, constraints, and risks.
3. Ask concise clarification questions only when local context cannot answer
   something material.
4. Choose the simplest design that fits existing project patterns.
5. Record the design when the task has architectural or user-facing impact.

Small tasks may have a short design note. Large tasks should have a dedicated
design document under the project's chosen spec directory.

### Phase 1: Plan

Write a concrete checklist before implementation. The default convention is
`tasks/todo.md`; if a repository uses a different task log, use that.

The plan must include:

- objective
- files likely to change
- implementation approach
- test and verification commands
- acceptance criteria
- explicit out-of-scope items

Plan steps should be small enough to execute and verify independently. Avoid
placeholders such as `TBD`, `later`, `add validation`, or `handle edge cases`
unless the exact validation and edge cases are named.

### Phase 2: Execute

During implementation:

- Make the smallest useful change.
- Keep unrelated cleanup out of the diff.
- Follow existing naming, structure, and helper patterns.
- Update the task checklist as work progresses.
- Log meaningful deviations from the plan.
- Stop and re-plan if tests fail for unclear reasons, the scope expands, or the
  chosen design starts requiring broad special cases.

### Phase 3: Verify

Verification is not a feeling. Use this gate before claiming completion:

```text
1. IDENTIFY: what command or inspection proves the claim?
2. RUN: execute it fresh.
3. READ: inspect the complete output and exit code.
4. VERIFY: compare the output against the claim.
5. CLAIM: state the result only after the evidence supports it.
```

Common claims and required evidence:

| Claim | Required Evidence |
| --- | --- |
| Tests pass | Test command exits 0 with no unexpected failures |
| Lint is clean | Linter exits 0 or only reports accepted warnings |
| Build succeeds | Build command exits 0 |
| Bug is fixed | Regression test or reproduction now passes |
| Requirement is met | Acceptance criteria checked one by one |
| Generated artifact is valid | Open, parse, render, or otherwise inspect it |

If verification cannot be run, state why and describe the remaining risk.

## TDD Rules

For behavior changes, prefer a Red-Green-Refactor loop:

1. Write a minimal failing test for the expected behavior.
2. Run the targeted test and confirm it fails for the expected reason.
3. Implement the smallest code change that makes the test pass.
4. Re-run the targeted test.
5. Run the broader relevant test suite.
6. Refactor only while tests remain green.

Do not write tests merely to describe already-written implementation. A useful
test proves expected behavior and can fail when that behavior regresses.

If no automated test harness exists, create one when practical. If that is not
practical, document manual verification steps with exact commands, inputs, and
observed outputs.

## Systematic Debugging

For bug reports, use this sequence:

1. Read the full error message, logs, stack trace, screenshots, and reported
   steps.
2. Reproduce the failure reliably, or document what evidence is missing.
3. Inspect recent changes and relevant dependencies.
4. Trace the bad value or behavior to its source.
5. Compare against a working example in the codebase.
6. State one root-cause hypothesis.
7. Test that hypothesis with the smallest change or diagnostic.
8. Add a failing regression test.
9. Implement the fix at the root cause.
10. Verify the fix and relevant regressions.

After three failed fix attempts, stop and re-evaluate the design. Repeated
failure usually means the diagnosis or architecture is wrong.

## Domain Boundaries

Keep reusable core layers free of project-specific business knowledge.

Examples of rules that usually belong outside the core:

- customer-specific limits
- market, currency, region, plan, or product lists
- regulatory thresholds
- approval policies
- pricing, precision, and rounding rules
- business-specific user-facing phrasing

Prefer configuration, database records, plugin/tool metadata, API responses, or
adapter layers for these rules. If a tool or adapter does not expose the needed
business fact, add it there instead of hard-coding it in the core.

## Collaboration Rules

- Start from an up-to-date base branch unless the task is intentionally local.
- Use a feature branch for non-trivial changes.
- Keep commits atomic: one coherent behavior or documentation unit per commit.
- Do not rewrite shared history.
- Do not delete or overwrite other people's work without explicit agreement.
- Announce ownership of high-conflict files before large changes.
- Treat a dirty working tree as shared state. Inspect before editing and never
  revert changes you did not make unless asked.

Suggested branch prefixes:

- `feat/<task-slug>`
- `fix/<bug-slug>`
- `docs/<topic>`
- `chore/<topic>`

Suggested commit format:

```text
<type>(<scope>): <description> [task: <slug>]
```

## Subagent And Delegation Rules

Use delegated agents, reviewers, or collaborators when work can be split into
independent tasks:

- codebase exploration
- separate subsystem analysis
- independent verification
- bounded implementation with disjoint file ownership
- review of a completed draft

Delegated task prompts must be self-contained:

- goal
- context
- constraints
- files or directories in scope
- expected output format

Do not trust a delegated success report by itself. Verify the diff, commands,
and evidence independently.

## Documentation And Logs

Each project should keep lightweight persistent task records. The default
convention is:

- `tasks/todo.md` for active checklists and summaries
- `tasks/devlog.md` for durable rationale, implementation notes, and
  verification results
- `tasks/lessons.md` for patterns learned from user corrections or surprising
  failures, when that file exists or when the project chooses to create it

For non-trivial changes, log:

- **Why**: what problem the change solves
- **How**: the core implementation and files touched
- **Result**: verification commands, outputs, and remaining risks

Update `README.md` in the same change when work affects:

- setup or startup instructions
- environment variables
- dependencies
- public APIs or schemas
- major user-facing workflows
- new modules that future contributors need to understand

## Code Review Rules

Review feedback is a technical input, not a social ritual.

When receiving review:

1. Read the full feedback.
2. Restate the technical requirement if unclear.
3. Verify the claim against the codebase.
4. Accept, reject, or refine the feedback with technical reasoning.
5. Implement one item at a time.
6. Run the relevant verification after each meaningful change.

Push back when feedback breaks existing behavior, contradicts project goals, adds
unused complexity, or rests on incorrect assumptions.

## Completion Checklist

Before declaring a task complete:

- [ ] Plan checklist is updated.
- [ ] Changed behavior is covered by tests or documented manual verification.
- [ ] Relevant test, lint, build, or artifact checks were run fresh.
- [ ] Outputs and exit codes were read, not assumed.
- [ ] README or source-of-truth docs were updated when required.
- [ ] Task log includes why, how, and result.
- [ ] Remaining risks or skipped verification are stated clearly.

## Anti-Rationalization Table

| Temptation | Rule |
| --- | --- |
| "This is too small for process." | Use a smaller process, not no process. |
| "It should work." | Run the command. |
| "I'll add tests later." | Later tests rarely prove the original failure. |
| "I'll just patch symptoms first." | Find the root cause first. |
| "The agent said it passed." | Inspect the evidence yourself. |
| "The business rule probably won't change." | Put business rules where they can change. |
| "This refactor is nearby." | Do it only if the task requires it. |
| "One more quick fix attempt." | After repeated failures, re-plan. |
