# task.toml field reference and taxonomy

Source: [10.Task Components.md](../../../../docs/10.Task%20Components.md),
[11.Task Requirements.md](../../../../docs/11.Task%20Requirements.md),
[12.Task Category Taxonomy.md](../../../../docs/12.Task%20Category%20Taxonomy.md).

## Field reference

| Field | Placement | Notes |
|---|---|---|
| `name` | top level **or** `[metadata]` | Both resolve |
| `artifacts` | **top level only** | Paths the verifier reads from the agent's final environment |
| `category` / `subcategory` | `[metadata]` | Exactly one each, Title Case, matching the taxonomy |
| `tags` | `[metadata]` | 3–6 free-form keywords |
| `languages` | `[metadata]` | Primary implementation language(s) |
| `difficulty` | `[metadata]` | `frontier` \| `advanced` \| `core` \| `base` |
| `expert_time_estimate_hours` | `[metadata]` | Expert time to author |
| `author_name` / `author_email` | `[metadata]` | Required; `"anonymous"` is fine |
| `difficulty_explanation` | `[metadata]` | The crux an agent must get right |
| `solution_explanation` | `[metadata]` | How the oracle solves it |
| `verification_explanation` | `[metadata]` | How the verifier decides |
| `relevant_experience` | `[metadata]` | Your qualifying background |
| `is_multi_container` | `[metadata]` | Optional; set `true` only when true |
| `[environment].network_mode` | | Must be `"public"` |
| `[agent].network_mode` | | `"public"` or `"no-network"` — required |
| `[verifier].network_mode` | | `"public"` or `"no-network"` — required |
| `[verifier].environment_mode` | | Must be the explicit `"separate"` |
| `[agent].timeout_sec` | | Min 1800, ceiling 18000; most 3600–5400 |
| `[verifier].timeout_sec` | | Ceiling 18000 |
| `[environment].build_timeout_sec` | | Bounded, accounts for compilation |
| `[environment].cpus/.memory_mb/.storage_mb` | | ~2 cores, ~8 GB, ~10 GB. No GPU |

`gpus`, `gpu_types`, and `docker_flags` are valid Harbor fields but not requirements —
omit them for a non-GPU task.

The four `*_explanation` fields plus `relevant_experience`, `category`, and `subcategory`
become the packaged `README.md`. There is no second write-up.

## Worked example, and one trap in it

[docs/others/example_toml.md](../../../../docs/others/example_toml.md) shows a valid
post-static-check manifest and a "what fails now" counter-example. Its useful
confirmations:

- `name` resolves at top level **or** under `[metadata]`.
- Descriptive fields under `[metadata]`; top-level copies no longer count.
- `artifacts` stays top-level — "required by separate-verifier checks, not the fields check".
- **Top-level `network_mode` fails** — Harbor ignores it, so it looks correct and does nothing.
- `expert_time_estimate_hours` may be a float (`2.0`).

⚠️ **That example predates the Aug 24 per-phase network rule.** Its `[agent]` and
`[verifier]` tables carry only `timeout_sec`, and its comment on
`[environment].network_mode` reads `"public" # or "no-network"`. Both are now wrong:

- `[environment].network_mode` **must** be `"public"` — it is not a choice.
- `[agent].network_mode` and `[verifier].network_mode` are **both required**. An omitted
  phase silently inherits the baseline and is a blocking finding.

Its `tags = ["debugging", "python"]` is also only 2 entries, below the 3–6 requirement.
Treat the file as a layout reference, not a copy-paste template.

## Changed from Terminus 2nd Edition

**Added:** `subcategory`, `tags`, `expert_time_estimate_hours`, `artifacts`,
`network_mode`, `[verifier].environment_mode`, `[environment].build_timeout_sec`.

**Removed:** `codebase_size`, `number_of_milestones`, the old subcategory list,
`allow_internet`, `junior_time_estimate_min`.

**Changed:** `difficulty` takes a Terminus 3 tier; `expert_time_estimate_min` →
`expert_time_estimate_hours`.

**Moved:** descriptive fields now live under `[metadata]`; top-level copies are not
counted by the structure check.

**Flipped:** agent timeout — 1800s was the *maximum* in Edition 2, and is the *minimum*
in Terminus 3.

## Taxonomy

Exactly one category and one subcategory, Title Case, matched exactly.

| Category | Subcategories |
|---|---|
| **Science** | Biology · Chemistry · Physics · Earth · Robotics · Math · Linguistics |
| **Software** | Algorithms · Systems · Databases · Data engineering · Frontend · Languages |
| **ML** | Training · Inference · Evaluation · Kernels |
| **Operations** | Finance · Logistics · Supply chain · Claims · Compliance · Marketing |
| **Security** | Cryptography · Reverse engineering · Forensics · AppSec |
| **Hardware** | CAD · RTL |
| **Media** | Music · Design |

**The most common tagging mistake is defaulting to Software because the task involves
writing code.** Nearly every task does. Ask instead: what must the agent *understand* to
get this right? Debugging a training loop is ML/Training. Parsing mass spectra to infer a
molecular structure is Science/Chemistry. Reserve Software for when software engineering
itself is the subject. If a task spans two, choose the domain it cannot succeed without.

**Kernels without a GPU:** tasks must not require one, but kernel work is in scope via
CPU-simulated kernels (verifier checks numerical correctness against a CPU reference) or
compile-only verification.

## Languages

Python · C · C++ · JavaScript · TypeScript · Java · Go · Rust · C#

Multi-language tasks are preferred. `languages` records the primary language the agent
works in, not every tool involved — domain toolchains (proof assistants, HDLs, CAD
scripting, query languages) are welcome in the environment without being listed.

The Edition-2 rule requiring Python tasks to be HARD no longer applies; tiers are
language-independent.

## Requirements every task satisfies

- **Novel** — not a variation of anything in Terminal-Bench 2.1/3.0 or prior Terminus
  editions. Reskinning is detected by embedding similarity; a task can be returned for
  duplication even when individually well built.
- **Multi-step** — chained commands, intermediate state, real reasoning. "At least 5
  agent steps" is a heuristic for ruling out trivial tasks, not a counted threshold. The
  real question: could an agent finish this in one shot without reacting to anything?
- **Testable** — fully specified, self-contained, deterministically graded on final state.
- **Standalone** — no human input after start; no interactive prompts.
- **No canary strings** in any component. This is a training dataset.
- **No privileged ops** — no root requirement, `--privileged`, or unsafe Docker settings.
