# Keeping instruction, tests, and solution in sync

Source: [docs/others/Instruction-Tests-Solution-Guidelines-8-13-26.pdf](../../../../docs/others/Instruction-Tests-Solution-Guidelines-8-13-26.pdf)
— the "additional guidelines" PDF shared in `#terminus-3-announcements`, describing the
patterns behind almost every task sent back for revision.

> **Almost every task that gets sent back fails for one underlying reason: the
> instruction, the tests, and the reference solution don't describe the same contract.**

The single rule the whole document is about:

> Everything the instruction asks for is **tested**. Everything the tests enforce is
> **stated in the instruction**. Your reference solution does **exactly what the
> instruction says** — no more, no less.

Sections 1–4 stop an *honest* solution from failing review. Sections 5–6 stop a
*dishonest* one from passing; the PDF is explicit that integrity holes are **one of the
largest sources of blocking send-backs, not a footnote**.

## 1. Test everything the instruction requires — not just the happy path

By far the most common issue: the verifier checks only *part* of what the instruction
demands, so a wrong or incomplete solution still passes.

| Trap | Example |
|---|---|
| **Unchecked output fields** | Instruction requires `bill_id` on each reversal; tests check only amount and account, so a blank `bill_id` passes |
| **Hard-codable config** | A tolerance fixed at 50 in every case — hardcoding 50 passes. Vary it across cases |
| **Untested failure modes** | Every holdout input has zero rejections, so an implementation that never rejects anything passes |
| **Indistinguishable strategies** | No case separates "minimize the largest job" from "minimize the number of jobs" |

**Self-check:** write a deliberately wrong or incomplete solution and run it against your
tests. Do they fail it? If not, coverage has a hole.

## 2. Make the reference solution obey its own contract

Second most common. The oracle quietly does something the instruction doesn't sanction,
or skips something it states.

- **Undocumented constraints** the solution adds — rejecting codes longer than 64 chars
  when the contract allows any length.
- **Silently skipped requirements** — the contract says count malformed rows; the
  solution drops them without counting.
- **Edge-case bugs** — integer overflow, non-atomic file replacement, off-by-one at boundaries.

**Self-check:** read the instruction as a contract, then read `solve.sh` line by line
against it. Nothing extra, nothing missing.

## 3. Pin down anything that changes the answer

If a choice materially changes the graded output but the instruction leaves it open,
reasonable solutions diverge and your grader accepts only one. That is a send-back.

- Undefined **method or model** — which estimator? which distribution?
- Undefined **precedence** when two rules both apply — which error wins?
- Undefined **tie-breaks, ordering, or schema** for a required output.

**Fix:** either specify the choice, or make grading accept every valid interpretation.

> **The nuance — this is the flip side of "don't over-explain."** Omit things that are
> unambiguous domain standards a competent practitioner would just know. Pin things where
> competent experts would legitimately differ and your grader only accepts one answer.
> **Over-trimming is how tasks become ambiguous.**

This is the same tension the Quality Panel's `coherent_contract` axis measures: a rule
whose only home is your reference's source code is a gap, but a domain standard spelled
out in tedious detail is the hint-giving the styling guide rejects.

## 4. Don't let the verifier enforce unstated rules

- **Tolerance mismatch** — instruction says ±1e-3, verifier demands 1e-9; a correct
  solution fails.
- **Brittle exact-golden matches** baking in incidental artifacts (an off-by-one, a
  leftover row) that were never part of the contract.
- **Unstated structural rules** — rejecting a file layout, duplicate key, or output shape
  the docs never prohibit.

**Self-check:** for every assertion, point to the sentence in the instruction that
requires it. No sentence → add it to the instruction, or drop the assertion.

## 5. Keep ground truth out of the agent's reach

- **Store goldens in the verifier only** — in the `tests/` image. Never in a directory the
  agent can read: not beside the inputs, not in `/app`.
- **Grade against a pristine, verifier-owned copy.** Don't recompute the expected result
  from files the agent could modify — an agent can swap in an easier input (truncate it,
  replace it) so your recomputed expectation matches its incomplete output.
- **Make held-out cases genuinely independent.** If hidden cases are re-serialized copies
  of visible data, an agent memorizes results by ID and skips building a real solution.
- **Don't leak the label in names or metadata** — no folder named for the defect it contains.
- **Watch symlink-following when staging agent files** — a planted link pulls protected
  files into readable space.

**Self-check:** could a lazy agent pass by reading or editing a file instead of solving?

## 6. Grade robustly — treat agent output as untrusted

Everything the agent produces is adversarial text.

- **Parse defensively** — don't let agent-controlled strings slip into the fields your
  grader reads and forge a correct-looking result.
- **Reward real behavior**, not text the agent shapes to look right. Execute its program
  and check outcomes rather than trusting what it reports.
- **Protect the reward channel.** The reward is written *only by the verifier, only after
  it grades the output*. Two specific vectors the PDF calls out: **a process the agent
  started can outlive the run and overwrite reward.txt after you write it**, and agent
  code invoked during grading can write it directly. Keep the reward path out of reach,
  and make sure no agent-spawned process is still alive when the reward is written.

**Self-check:** can the agent fake a pass — by spoofing parsed text, or by writing the
reward itself, including via a process it left running?

## The 60-second pre-submit audit

- [ ] Every requirement in the instruction has a corresponding test.
- [ ] A deliberately wrong/incomplete solution **fails** your tests.
- [ ] Tests distinguish a correct approach from a plausible-but-wrong one — no two strategies produce identical graded output.
- [ ] No test case lets a hardcoded value pass — configs and inputs vary across cases.
- [ ] Every failure/rejection case in the instruction is actually tested.
- [ ] `solve.sh` does exactly what the instruction says — no undocumented shortcuts, no skipped requirements.
- [ ] Any choice that changes the output is pinned (method, precedence, tie-breaks, schema) — or grading accepts all valid answers.
- [ ] Tolerances in the instruction match the verifier.
- [ ] Every test assertion traces back to a sentence in the instruction.
- [ ] Answers, goldens, and labels are not readable, editable, or inferable from the agent's side.
- [ ] Held-out cases require the general solution — not memorizable from visible data.
- [ ] The verifier doesn't follow symlinks when staging agent files, and grades against a pristine copy the agent never touched.
- [ ] The grader can't be spoofed by agent-controlled output text.
- [ ] The reward is written only by the verifier after grading — no agent-controlled code or lingering process can set it.
