---
name: terminus3
description: Author, audit, fix, or submit a Terminus 3 (Terminal-Bench 3.0) task for Snorkel's Expert Platform — task.toml, instruction.md, environment/, solution/, tests/. Use when creating a new task, reviewing one against CI checks or the Quality Panel, fixing a failing check or a needs_revision, packaging a submission ZIP, or answering "why did my task come back".
---

# Terminus 3 task authoring

Terminus 3 is Snorkel's expert-authored dataset targeting Terminal-Bench 3.0. Each task
is a self-contained directory an AI coding agent attempts once, graded by a verifier
running in a container the agent cannot reach. Your job as author is to build tasks that
frontier agents genuinely fail — for the right reasons.

Full documentation lives in [docs/](../../../docs/), numbered by reading order. This
skill is the working reference; **the docs win on any conflict, and the Slack channel
wins over the docs** (see Precedence below).

## Non-negotiable: never ship this skill inside a submission

`CLAUDE.md`, `skills.md`, `AGENTS.md`, and `.cursor/` in a task environment are a
**High-severity** reviewer criterion — they read as incomplete AI-scaffolding cleanup and
raise task-authenticity concerns ([34.Terminus 3 Review Checklist.md:80](../../../docs/34.Terminus%203%20Review%20Checklist.md#L80),
[35.Common Errors.md:232](../../../docs/35.Common%20Errors.md#L232)).

The submission ZIP contains **exactly** these, and nothing else:

```
task.toml  instruction.md  environment/  solution/  tests/
```

`.claude/`, `docs/`, `.git/`, and any scratch files must never enter the ZIP.
`rubrics.txt` and `README.md` are added by Snorkel at packaging — you do not author or
ship either. ZIP the files **inside** the task folder, not the enclosing folder.

Related: instruction.md and solve.sh are screened for AI-generated text and **fail above
a probability threshold**. Write them yourself. Slack has warned that suspected
LLM-generated tasks can mean removal from the project and the platform. Use this skill to
check structure and catch defects — not to draft your prose.

## Run the audit first

```bash
python .claude/skills/terminus3/scripts/audit.py .
```

Deterministic checks, including the platform-only preflights `stb harbor check` does not
run. It does not replace the CLI:

```bash
stb harbor check <task-folder>          # official check suite
stb harbor run -a oracle -p <folder>    # oracle must PASS
```

## The one rule behind most send-backs

> Everything the instruction asks for is **tested**. Everything the tests enforce is
> **stated in the instruction**. The reference solution does **exactly what the
> instruction says** — no more, no less.

Almost every returned task fails because those three describe different contracts. Two
self-checks catch most of it: run a **deliberately wrong solution** against your verifier
and confirm it fails, and for **every assertion** point at the sentence in instruction.md
that requires it. Full treatment, including the 60-second pre-submit audit, in
[references/contract-sync.md](references/contract-sync.md).

The balance to hold: *omit* what a competent practitioner would just know; *pin* what
competent experts would legitimately differ on when your grader accepts one answer.
Over-trimming is how tasks become ambiguous — that is the same line
`coherent_contract` grades.

## The five gates a task passes

1. **`stb harbor check`** — structure, manifest, pinning, verifier isolation.
2. **Platform preflight** — cloud-builder Dockerfile syntax, `verifier_interpreter_permissions`. Not in the CLI.
3. **Oracle 3/3 + NOP 0/1** — the reference passes; doing nothing does not.
4. **Quality Panel** — four-axis LLM review. Minor, Major, *and* Unsure all block.
5. **Human reviewer** — the [Review Checklist](../../../docs/34.Terminus%203%20Review%20Checklist.md).

Per Slack: what looks like "platform errors" is usually the checks being tougher than
before, deliberately pushed upstream to authors.

## task.toml shape

```toml
artifacts = ["/app/output.json"]        # TOP-LEVEL. Nesting under [verifier] is
name = "your-task-name"                 # silently dropped — verifier gets nothing.

[metadata]
author_name = "anonymous"               # required; "anonymous" is fine
author_email = "anonymous"
category = "Software"                   # exactly one, Title Case, from the taxonomy
subcategory = "Databases"               # exactly one
tags = ["python", "wal", "recovery"]    # 3–6
languages = ["python"]
difficulty = "advanced"                 # frontier | advanced | core | base
expert_time_estimate_hours = 6
difficulty_explanation = "..."          # these four become the packaged README —
solution_explanation = "..."            # there is no second write-up to do
verification_explanation = "..."
relevant_experience = "..."

[verifier]
timeout_sec = 1800
environment_mode = "separate"           # explicit key REQUIRED by Terminus CI
network_mode = "no-network"             # required

[agent]
timeout_sec = 7200                      # min 1800, ceiling 18000
network_mode = "no-network"             # required

[environment]
network_mode = "public"                 # REQUIRED on every task, offline included
build_timeout_sec = 900
cpus = 2
memory_mb = 8192
storage_mb = 10240
```

Traps that cost real submissions:

- **Descriptive fields belong under `[metadata]`.** Top-level copies are not counted.
  `artifacts` stays top-level; `name` resolves in either place.
- **`[environment].network_mode = "public"` is not optional.** The image build and the
  agent harness install need the network. Closing it kills every trial *before the agent
  starts*, with `E: Unable to locate package curl` — which reads like an environment
  defect. Oracle and NOP still pass, because they install no harness. An offline task
  keeps environment public and sets `[agent]` to `"no-network"`.
- **All three phases must declare `network_mode`.** An omitted phase silently inherits
  the baseline; that is a blocking finding, not a default.
- **`"allowlist"` is not a supported value** and `allowed_hosts` is rejected with it.
  A task using it is refused at creation and reports `Oracle ran 0 trials`.
- **Top-level `network_mode` is ignored** — Harbor drops unrecognised root keys, so it
  looks right and does nothing.
- **Retired tier names** (`easy`/`medium`/`hard`) are sent back. Use the four current tiers.
- **`is_multi_container = true`** only when genuinely multi-container. The harness finds
  `environment/docker-compose.yaml` on its own; nothing in task.toml points at it.

## instruction.md

Write it the way you actually prompt a coding agent. Around 2 short paragraphs or up to
20 bullets. Give the **what**, never the **how**.

Required: absolute paths (`/app/output.json`) — enforced by check. Every file the tests
read or write must be named. No canary strings anywhere in the task. No emojis, minimal
markdown.

Rejected shapes ([14.Instruction Prompt Styling.md](../../../docs/14.Instruction%20Prompt%20Styling.md)):
step-by-step walkthroughs with solution values; "Detection Guidance" hint sections;
heavy markdown that reads like API documentation; prescriptive function signatures;
bold markers spotlighting solution details.

You cannot dodge the length limit by pushing requirements into `environment/` spec files.
Those must read like real engineering documents (an API contract, a schema) — not
polished LLM-style prompt extensions — and must not contain procedural hints.

## environment/Dockerfile

- **`tmux` and `asciinema` are mandatory.** The agent runtime cannot start a session
  without them. Missing them fails *every* trial with
  `RuntimeError: Failed to start tmux session` and `verifier_did_not_run`.
- Digest-pin every `FROM` with `@sha256:<digest>`. `FROM image:tag@sha256:<digest>` is
  the required form and is unchanged by the cloud-builder rules.
- Prefer a canonical base image ([20.Dockerfile & Image Best Practices.md](../../../docs/20.Dockerfile%20&%20Image%20Best%20Practices.md)).
  Non-canonical needs a credible justification as a Dockerfile comment, or it is blocked.
- Pin every pip/uv install with `==`. Do **not** pin apt versions.
- Never `COPY` `solution/` or `tests/` into the agent image.
- Never create or chown Harbor's reserved paths: `/logs/verifier/`, `/logs/artifacts/`,
  `/oracle/`, `/tests/`.
- No `FROM --platform=`, no bare `nproc` (reports host CPUs, not your limit).
- `environment/` ≤ 100 MiB total, no single file > 50 MiB. Ship a `.dockerignore`.
- No `--privileged`, `SYS_ADMIN`/`NET_ADMIN`, or docker-socket mounts.
- Store source as files, not `cat <<EOF` heredocs or opaque archives.

**Cloud image builder syntax** — two patterns local Docker accepts and the cloud builder
rejects, blocking at preflight on *every* Dockerfile:

```dockerfile
COPY --chown=root:root f /app/f              # BAD — named user
COPY --chown=0:0 f /app/f                    # GOOD — numeric IDs

COPY --from=golang:1.24-bookworm@sha256:… …  # BAD — tag + digest
COPY --from=golang@sha256:… …                # GOOD — digest only
COPY --from=builder …                        # GOOD — stage names are fine
```

Known Modal quirk: `COPY --chown=UID:GID dest` chowns contents only, not `dest` itself.
If a later `RUN` creates files there and hits `Permission denied`, add
`RUN chown UID:GID dest` right after the COPY. `RUN chown` is allowed.

## tests/ — the verifier

The verifier runs in its own container built from `tests/Dockerfile`, after the agent's
container is gone. It sees only the paths in top-level `artifacts`.

```bash
#!/bin/bash
set -uo pipefail                    # NOT set -e
mkdir -p /logs/verifier
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt
else echo 0 > /logs/verifier/reward.txt; fi
```

Three deliberate details: **no `set -e`** (a failing pytest would abort before the reward
is written, turning a real failure into an infrastructure error); **no trailing `exit`**
(the script's status should reflect whether the *reward write* succeeded); **`--ctrf` is
required** and enforced by the `ctrf_reporting` check.

- Bake every verifier dependency into `tests/Dockerfile`, pinned exactly. `test.sh` must
  never `pip install`, `curl`, `wget`, `npm install`, or `git clone` — that fails in
  production with `RewardNotFoundError`.
- **Create artifact landing directories** (`RUN mkdir -p /app`) or Harbor's upload fails
  in a way that looks like broken tests. Check this first when a verifier fails inexplicably.
- Every test needs a docstring (CI-validated). Tests must be independent and deterministic.
- Give env vars defaults: `TEST_DIR="${TEST_DIR:-/tests}"`.
- Identical conditions for oracle and agent — branching on `/oracle` existing is banned.
- No latency/performance assertions; they are hardware-dependent.
- Don't set performance thresholds within ~5% of the oracle — that makes the task
  "replicate the oracle" rather than solve it.

**Preserve interpreter permissions.** If the verifier changes interpreter modes, resolve
paths with `Path.resolve()`, deduplicate, save each original mode once, restore in
`try/finally`, and never hardcode `0755`. On merged-`/usr` images `/bin/bash` and
`/usr/bin/bash` are one file; saving both then restoring in order can record `000` and
leave Bash non-executable, so Harbor cannot collect logs. The
`verifier_interpreter_permissions` preflight blocks on exactly this dual-path pattern and
is **not** in `stb harbor check`.

### The verifier must reject wrong solutions

Accepting a right answer proves nothing. Before submitting, run a **deliberately wrong**
solution against your own verifier and confirm it fails. One mutant breaking several
rules at once — including the shipped buggy code — is not enough: for each named rule,
a case must exist that fails if *that rule alone* were wrong.

Legitimate and encouraged: running the agent's program (rebuilt from source), parsing its
output, golden fixtures and byte-exact comparison when the instruction pins the output,
spec-derived invariants, held-out re-runs, determinism checks.

Anti-patterns:

| Pattern | Why it fails |
|---|---|
| Ground truth from agent-writable paths | The agent edits the truth, not just the answer |
| Golden beside a path handed to agent code | A dropped uid stops writes, **not reads** of a world-readable sibling |
| Hand-staging agent trees (`copytree`) | Follows symlinks into protected fixtures; `symlinks=False` is *not* a guard |
| Grading a delivered binary unrebuilt | A hardcoded binary passes |
| Checking a proxy (count, presence, first element) | Fabricated output passes |
| Trusting exit code / shared stdout | Agent code controls that channel |
| Instruction says 1e-3, test asserts 1e-9 | A conforming solution fails |
| Feasibility-only on an optimization spec | A plan optimizing the wrong quantity passes |
| Held-out as the *only* enforcement of a rule | Hidden inputs are fine; hidden *requirements* are not |
| Reimplementing the solution in tests/ | If deleting `solution/` still lets tests compute the answer, tests are solving it |

**Separate mode protects the verifier from the agent's environment — not from agent code
the verifier itself executes.** If you rebuild and run the agent's program inside the
verifier, drop to an unprivileged uid before the exec, include `--no-new-privs`, and
*probe in a test* that the uid cannot read goldens or `/logs/verifier`.

## solution/solve.sh

Deterministic, human-written, `set -e`, derives the answer rather than echoing it. Seed
any randomness. No network calls.

**Correct, not just passing.** You write the tests and oracle together and tune until it
passes, so a green oracle mostly proves the task *runs*. A wrong oracle is worse than a
broken one: the tests encode its output as the answer key, so correct agent solutions
fail and difficulty is measured against a bad truth. Verify the oracle against the
**spec** on edge cases your fixtures skip.

## Difficulty — measured, never declared

Accuracy = mean pass@1 across GPT-5.6 and Claude Opus 5. Measured **once**: after your
task passes the quality panel, the platform runs 4 trials/model × 2 models = **8** runs,
and that tier is final. Nothing runs after acceptance — no more provisional tier, no
4-run iteration gate, no tier that can shift later.

**At least one of the 8 runs must fail**, or the task cannot proceed — it gives no
signal. Keep local-testing with `-k 4` (below); it mirrors the platform's run count, so
there's no separate shorter check to disagree with the final one. Set `difficulty` in
task.toml to your best local estimate and move on — the platform's measurement is what
gets recorded, and a mismatch isn't a defect reviewers chase.

| Tier | Accuracy |
|---|---|
| Frontier | < 20% |
| Advanced | 20 – <50% |
| Core | 50 – <80% |
| Base | 80 – <100% |

>80% is fine (that's Base). **100% across both models is not.** One model going 4/4 is
fine if the other fails at least once.

```bash
stb harbor run -m @openai/gpt-5.6 -p <folder> -k 4
stb harbor run -m @anthropic/claude-opus-5 -p <folder> -k 4
```

Run models **sequentially** — concurrent runs burn the $10/30-day key far faster. Get the
oracle passing before spending key budget, and use `stb harbor tasks start-env -p <folder> -i`
for debugging, which costs nothing.

Difficulty comes from how much must be true *simultaneously* — not from piling on
independent requirements, ambiguity, or obscure trivia. A known environment defect now
blocks acceptance even if no run happened to fail because of it.

Trial-analysis flags: `task_specification` and `reward_hacking` mean the task must
change. `difficulty_crux`, `near_miss`, `refusals`, `low_timeout` need an answer. On
`near_miss`: if runs keep failing the *same* test, that check or the instruction is
usually the problem; different tests each time is genuine near-miss.

## Quality Panel — four axes, all blocking

Automated review of the task itself, before a human sees it. Each axis sees only some
files, deliberately.

| Axis | Question | Sees |
|---|---|---|
| `coherent_contract` | Could two competent people reasonably disagree on a graded answer? | instruction, task.toml, environment, tests — **not solution** |
| `correct_reference_solution` | Does your reference satisfy the contract at the edges? | instruction, solution — **not tests** |
| `protected_ground_truth` | Can the answer be reached, forged, or inferred? | tests, environment |
| `sound_verifier` | Could a genuine attempt pass without solving? | instruction, tests — **not solution** |

**Minor, Major, and Unsure all block.** Minor is not optional polish — the severity
describes the defect, not whether the task comes back. Only `None` on every axis
auto-accepts. Unsure means the panel couldn't decide and a human will look; it usually
isn't a defect in your task.

Highest-value pre-submit passes:

- Read your **rendered** instruction.md as a stranger. Leftover `repr()` fragments,
  template junk, or internal identifiers are a real `coherent_contract` hit.
- For every rule your tests enforce, point at the sentence in instruction.md that states
  it. If it only lives in `solution/`, that's a gap.
- Grep `tests/` for outcome-revealing names — `reject`, `invalid`, `accept`,
  `request.node.name` — reaching any candidate-visible path, arg, or env var.
- Every `setpriv`/uid-drop carries `--no-new-privs`.
- No golden in the parent directory of any path passed to the agent's re-executed code.

A cited finding you can disprove is contestable — see
[36.Defending Your Submission.md](../../../docs/36.Defending%20Your%20Submission.md). Note the
docs acknowledge measured run-to-run variance in panel severities, which is legitimate
grounds to ask for a re-judge.

## Submission mechanics

```bash
stb submissions create ./<folder> -p PROJECT_ID --time MINUTES
stb submissions update ./<folder> --time MINUTES     # only in NEEDS_REVISION
stb submissions feedback SUBMISSION_ID
```

The rubric is authored in the **platform UI**, not the CLI: max cumulative 10–40 points,
at least one negative criterion, every line starts with "Agent" and ends `, ±N`, only
±1/2/3/5 (**no 4s**). Keep "Send to reviewer" unchecked until CI is clean.

Limits (Slack): **3 net-new submissions per day**, reset at 00:00 UTC by `submitted_at`
— not your local date. Revisions don't count. **One task in `needs_revision` at a time**;
new contributors are capped at 2 pending. A revision queue of 10 blocks net-new entirely.

Note: `stb` does not support Windows. On a Windows machine use WSL or a Linux/macOS box
for `stb harbor` runs; the audit script here runs anywhere Python does.

## Precedence when sources conflict

1. **Slack `#terminus-3-announcements`** — newest policy, often ahead of the docs.
2. **The published task skeleton** — if it differs from a doc, the skeleton wins.
3. **The docs** in [docs/](../../../docs/).
4. This skill.

Known Slack-over-docs deltas already folded in above: single-measurement difficulty (8
runs after the quality panel, `-k 4` locally, no provisional tier); retired tier names;
`[environment].network_mode = "public"` mandatory; cloud-builder `COPY` syntax;
submission and revision-queue limits; quality panel blocking on Minor.

## Reference files

- [references/contract-sync.md](references/contract-sync.md) — **the highest-yield read**: why tasks get sent back, and the 60-second pre-submit audit
- [references/ci-checks.md](references/ci-checks.md) — every check, failure symptom, and fix
- [references/task-toml.md](references/task-toml.md) — full field reference and taxonomy
- [references/verifier-patterns.md](references/verifier-patterns.md) — good vs. exploitable verifier code
- [scripts/audit.py](scripts/audit.py) — local deterministic audit

## Stale material in docs/others/

[ci_feedback_training.ipynb](../../../docs/others/ci_feedback_training.ipynb) documents the
**retired Terminus 1/2 GitHub-PR workflow** and tells you to *add a canary string* — the
exact opposite of current policy, where canaries are banned in every component and signal
an old skeleton. Keep its one-fix-at-a-time iteration habit; ignore its mechanics. Full
delta table in [references/ci-checks.md](references/ci-checks.md).

[example_toml.md](../../../docs/others/example_toml.md) predates the per-phase network
rule: it omits `network_mode` from `[agent]`/`[verifier]` and treats
`[environment].network_mode` as a choice. Both are now blocking. See
[references/task-toml.md](references/task-toml.md).
