# CI checks, symptoms, and fixes

Errors block acceptance. Warnings should be fixed unless a reviewer approves an
exception. Re-run `stb harbor check <folder>` until clean, then measure difficulty.

Source: [28.CI Checks Reference.md](../../../../docs/28.CI%20Checks%20Reference.md),
[35.Common Errors.md](../../../../docs/35.Common%20Errors.md),
[ref4.Troubleshooting.md](../../../../docs/ref4.Troubleshooting.md).

## Where each check runs

| Layer | Runs | Covers |
|---|---|---|
| `stb harbor check` | Local + CI | Structure, manifest, pinning, verifier isolation |
| Platform preflight | Platform only, before Oracle | `check_modal_dockerfile_compat`, `verifier_interpreter_permissions` |
| Quality Panel | Platform, before human review | Four LLM axes |

Platform-only preflights are **not** in the CLI. A clean local run does not mean a clean
submit — fix those from the platform report and resubmit.

## Manifest and metadata

| Check | Rule |
|---|---|
| Required fields | Every required `task.toml` field present |
| Separate mode | Explicit `[verifier].environment_mode = "separate"`; `artifacts` top-level |
| Timeout ceiling | `[agent]`/`[verifier].timeout_sec` ≤ 18000 |
| Folder name length | Capped in hyphen-separated tokens — keep slugs short |

Harbor resolves separate mode from a combination of keys; **Terminus is stricter than
Harbor**. Harbor treats a `[verifier.environment]` table as separate even without
`environment_mode`, and defaults to *shared* when neither is set. Terminus CI rejects
both the implicit form and the shared default. `environment_mode = "shared"` plus a
`[verifier.environment]` table is invalid in Harbor itself.

The agent-timeout **minimum** of 1800s is a reviewer criterion, not a CI error — it will
come back from a human rather than the CLI.

⚠️ Nesting `artifacts` under `[verifier]` raises **no error**. The value is silently
dropped and the verifier receives nothing.

## Instructions

| Check | Rule |
|---|---|
| `check_task_absolute_path` | Absolute paths only — `/app/output.json` |
| Referenced files described | Every file tests read/write is named in instruction.md |
| Human-authored content | instruction.md and solve.sh screened for AI-generated text; fails above a probability threshold |

## Environment and Dockerfile

| Check | Blocking | Rule |
|---|---|---|
| `check_pinned_images` | ✅ | Every `FROM` digest-pinned `@sha256:` |
| `check_sanctioned_base_images` | ✅ | Final runtime base canonical, or justified in a comment |
| `check_build_context_size` | ✅ | `environment/` ≤ 100 MiB, no file > 50 MiB |
| `check_modal_dockerfile_compat` | ✅ | Numeric `COPY --chown=`; digest-only `COPY --from=` |
| Pinned pip installs | ✅ | Every pip/uv/uvx install pinned with `==` |
| Unpinned apt installs | ✅ | apt packages **without** `=version` |
| No platform pinning | ✅ | No `FROM --platform=` |
| No bare `nproc` | ✅ | Reports host CPUs, not the task's limit |
| References resolve | ✅ | COPY sources exist in the build context |
| No host bind mounts | ✅ | compose volumes must not bind-mount the host |
| Dockerfile hygiene | ⚠️ | Non-fatal warnings |

Warning-level checks can still emit **structural errors** when required files such as
`environment/` or `environment/Dockerfile` are missing.

## Verifier and tests

| Check | Blocking | Rule |
|---|---|---|
| Tests/solution absent from agent image | ✅ | Never `COPY tests/` or `solution/` |
| Verifier tooling baked in | ✅ | Installed in `tests/Dockerfile`, not `test.sh` |
| Pinned test tooling | ✅ | Exact versions |
| `ctrf_reporting` | ✅ | pytest run with `--ctrf /logs/verifier/ctrf.json` |
| No trial-time network fetches | ✅ | No `curl \| sh`, `wget \| sh`, `bash <(curl …)` in test.sh |
| `test.sh` sanity | ✅ | No system-wide or global side effects |
| Digest-pinned verifier base | ⚠️ | Every `FROM` in tests/Dockerfile pinned + sanctioned |
| `behavior_in_tests` | | Every requirement has a test |
| `behavior_in_task_description` | | Every tested behavior is in instruction.md |
| `informative_test_docstrings` | | Each test has a docstring |
| `ruff` | | Tests pass linting |

## Symptom → cause

| Symptom | Cause | Fix |
|---|---|---|
| `RuntimeError: Failed to start tmux session`, `verifier_did_not_run` on every trial | `tmux`/`asciinema` missing from the agent image | Install both explicitly |
| `E: Unable to locate package curl`, DNS failures before the agent starts | `[environment].network_mode` not `"public"` | Set it public; close `[agent]` instead |
| `RewardNotFoundError` | test.sh fetched from the network, or exited before writing reward | Bake deps in; never `exit` before the write |
| `DownloadVerifierDirError` / `Permission denied` collecting logs | Dual-path bash chmod left Bash non-executable | `Path.resolve()`, dedupe, restore once in `try/finally` |
| Verifier fails in ways that look like broken tests | Artifact landing directory missing in the verifier image | `RUN mkdir -p /app` (every declared artifact's parent) |
| `Oracle ran 0 trials` | `network_mode = "allowlist"` / `allowed_hosts` | Unsupported — task is refused at creation |
| Verifier receives nothing | `artifacts` nested under `[verifier]` | Move it top-level |
| Preflight fails on a COPY line | Named `--chown` user, or `:tag@sha256` on `--from=` | Numeric IDs; digest-only |
| Task returned as TRIVIAL | Retired tier name, or every run passed | Use current tiers; make it genuinely harder |

## ⚠️ The CI feedback training notebook is stale

[docs/others/ci_feedback_training.ipynb](../../../../docs/others/ci_feedback_training.ipynb)
describes the **retired Terminus 1/2 workflow**, not Terminus 3. Do not follow it
literally. It is still useful for the *iteration mindset* — fix one check at a time,
re-run, repeat — which [27.CI Feedback Training.md](../../../../docs/27.CI%20Feedback%20Training.md)
restates in current terms.

| Notebook says | Terminus 3 reality |
|---|---|
| **Add the canary string to `solve.sh`** | **Inverted.** Canary strings are banned in *every* component; their presence is a Medium-severity flag signalling an old skeleton |
| Clone `snorkel-ai/snorkel-tb-tasks`, branch, commit, open a PR | Submissions go through `stb submissions create` / the platform UI. There is no PR |
| `uv run stb tasks create` | `stb init NAME -p PROJECT_ID` |
| `task.yaml`, `run-tests.sh`, `solution.yaml`, `docker-compose.yaml` as standard | `task.toml`, `tests/test.sh`, `solution/solve.sh`; compose only for multi-container |
| No `tests/Dockerfile`; verifier ran in the task container | `tests/Dockerfile` is required; the verifier runs in a **separate** container |
| "This is considered an easy task" | `easy` is a retired tier — `frontier`/`advanced`/`core`/`base` |

If a task you adapted as a structural starting point carries a canary line, **remove it**.

## Acting on failures

1. Errors first — they block acceptance.
2. Then warnings — fix unless a reviewer approved an exception.
3. Re-run `stb harbor check` until clean.
4. Fix platform-only preflight findings from the platform report, then resubmit.
5. Then measure difficulty.
