# Verifier patterns — sound vs. exploitable

The verifier exists to answer one question: **would a wrong solution fail?** Confirming
the right one passes proves nothing about that.

Source: [22.Writing Tests.md](../../../../docs/22.Writing%20Tests.md),
[31.Quality Panel Judge Guide.md](../../../../docs/31.Quality%20Panel%20Judge%20Guide.md),
[9.What Makes a Good Task.md](../../../../docs/9.What%20Makes%20a%20Good%20Task.md).

## How verification runs

1. The agent works until it stops or times out.
2. Harbor collects the paths in top-level `artifacts` from the agent's final environment.
3. A separate verifier container starts, built from `tests/Dockerfile`.
4. Collected artifacts are placed into it.
5. `tests/test.sh` runs and writes a reward.

The verifier never runs inside the agent's environment, and only ever sees declared
artifacts.

## What a good verifier legitimately does

Substantial verifier logic is expected and fine:

- **Run the agent's own program** — rebuilt from submitted source, not the delivered binary.
- **Parse its output** to check semantics.
- **Golden fixtures / byte-exact comparison** when the instruction pins the output exactly.
- **Spec-derived invariants** — compute an expected property from the task's spec and check against it.
- **Held-out ground truth** baked into `tests/Dockerfile`.
- **Perturbation / holdout re-runs** — the recommended way to prove the answer was computed.

The line is narrow: don't put a callable end-to-end solver in `tests/` that maps inputs to
the complete expected artifact, and don't hardcode a value the instruction says the agent
must read from config.

> **Rule of thumb:** if deleting `solution/` would still let the test compute the expected
> answer itself, the test is doing the solving.

## Assert at the specificity the instruction states

The deciding word is **undocumented** — a check is brittle when it pins something the
instruction never stated, not because it uses `==`.

```python
# BAD — instruction never specifies log wording; `==` grades undocumented formatting
assert open("/output/log.txt").read() == "Processing complete\n"

# BAD — too loose the other way; an agent echoing the word anywhere passes
assert "complete" in open("/output/log.txt").read().lower()

# GOOD — the instruction specifies the report schema, so assert parsed values
report = json.loads(Path("/app/output/report.json").read_text())
assert report["status"] == "complete"
assert report["records_processed"] == 1432
```

## Every rule needs an isolating case

A single wrong solution violating several rules at once — including the shipped buggy
code — only proves the verifier is not a no-op. For each rule the instruction names,
a fixture must exist whose outcome changes if **that rule alone** were inverted.

Make the fixture carrying a rule its *hard* case:

```python
# BAD — an ordering rule (timestamp, then sequence) tested only on DISTINCT timestamps.
#       A timestamp-only implementation passes and never faces the tie the rule exists for.

# GOOD
def test_ordering_breaks_ties_by_sequence():
    """Events with equal timestamps must be ordered by sequence, not file position."""
    out = run_agent_cli("reconcile", "/app/simultaneous_events.json")
    assert [e["id"] for e in out["ordered"]] == ["a", "b", "c"]
```

**Held-out data must not be the only pin.** If the visible suite would still pass when a
rule is wrong, that rule is not tested — even if a mixed held-out set happens to fail.

**Hidden inputs are fine; hidden requirements are not.** A held-out fixture may introduce
a new input, but the instruction plus that input must determine the correct output.
Unfair: passing depends on a mapping, threshold, or label existing only in a hidden corpus.

**Every documented command or mode must be invoked** by at least one test. A subcommand
the tests reference but never run can be broken or hardcoded and still pass.

## Protected ground truth — the ten mechanisms

Each Quality Panel finding is tagged with exactly one, so the fix is unambiguous:

| Mechanism | Fix |
|---|---|
| `symlink_deref` | Guard that exact read (`O_NOFOLLOW`). A guard on a different helper doesn't count |
| `chmod_follow` | uid-drop needs `--no-new-privs` or a setuid binary regains privilege |
| `colocation_walk` | Never place a golden in a tree reachable from a path handed to agent code |
| `init_forces_success` | Don't trust a compiled test binary's exit code when agent code links in; assert structured per-test results |
| `stdout_inject` | Don't parse a protected metric from a shared stream the agent also writes to |
| `label_from_basename` | No outcome words (`reject`, `invalid`, `accept`) or `request.node.name` in candidate-visible paths/args/env |
| `mutate_expected_source` | Never derive the digest/roster/threshold from the candidate's own submitted file |
| `holdout_overlap` | Held-out cases must be genuinely unseen |
| `namespace_redefine` | Don't load agent modules before fixing the meaning of assertions |
| `mutated_tests` | Reset everything persisting from solve into grading |

### The reachability bar

Before treating a finding as blocking, all three must hold:

1. Does the artifact actually reach the candidate's filesystem — or the process the
   verifier execs? Separate mode answers this for the agent container **only**.
2. Is the exact path/value genuinely *knowable* from candidate-visible material? A
   plausible guess at your verifier's internal layout is not a derivation.
3. Does no other test in the suite independently recompute the value?

An unreachable precondition is `None`, not `Minor`.

### Read protection ≠ write protection

Dropping the re-executed process to an unprivileged uid stops it **writing** somewhere it
shouldn't. It says nothing about whether it can **read** a world-readable sibling of a
path you handed it. Stage the legitimate input into its own tree; keep goldens where that
process has no read access.

## test.sh — the canonical shape

```bash
#!/bin/bash
set -uo pipefail                 # NOT set -e
mkdir -p /logs/verifier
TEST_DIR="${TEST_DIR:-/tests}"   # env vars need defaults
python -m pytest --ctrf /logs/verifier/ctrf.json "$TEST_DIR/test_outputs.py" -rA
rc=$?
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt
else echo 0 > /logs/verifier/reward.txt; fi
```

- **No `set -e`** — a failing pytest would abort before the reward is written, reclassifying
  a real test failure as an infrastructure error. Fail-fast is still fine in setup and
  solution scripts.
- **End on the `fi`** — no trailing `exit`. The script's status then reflects whether the
  reward write succeeded. pytest's rc is captured and never propagated, so a failing test
  exits zero either way; a trailing `exit 0` only masks a failed write.
- **`--ctrf` is required** and enforced by `ctrf_reporting`.

If the skeleton differs from this, the skeleton wins.

## Interpreter permissions

```python
targets = {Path(p).resolve() for p in ("/bin/bash", "/usr/bin/bash")}   # dedupe FIRST
saved = {t: t.stat().st_mode for t in targets}                          # save once
try:
    ...
finally:
    for t, mode in saved.items():
        try:
            t.chmod(mode)          # restore the SAVED mode, never a hardcoded 0755
        except OSError as e:
            errors.append(e)       # attempt all restorations, report failures
```

On merged-`/usr` images both paths are one file. Saving both then restoring in order can
record `000` and leave Bash non-executable — Harbor then cannot collect logs, even though
pytest already wrote a reward. `Path.is_symlink()` alone misses symlinks in *parent*
directories like `/bin`.

## Test hygiene

- Docstring on every test (CI-validated).
- Independent — no cross-test global state or ordering assumptions.
- Deterministic — no network, wall-clock, or unseeded randomness.
- Behavior, not implementation — don't grep source for `sorted(`.
- No latency/performance assertions; hardware-dependent, so oracles aren't reproducible.
- Identical conditions for oracle and agent — branching on `/oracle` existing is banned.
- Don't set thresholds within ~5% of oracle performance: that grades oracle mimicry, not
  problem-solving. Ask whether a fundamentally different but correct approach would pass.
