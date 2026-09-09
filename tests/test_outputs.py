"""Verifier.

Grading is split so that every rule stated in instruction.md has at least one check
that fails if that rule alone is wrong. Byte-level golden hashes are kept, but they
are never the *only* enforcement of a rule -- each rule also has a semantic assertion
that does not depend on filesystem iteration order or on any other rule being correct.

Axes graded:
  1. artifact exists at the documented path and is valid JSON with the documented shape
  2. entries are ordered by name                (rule: "ordered by name")
  3. per-file word counts are correct           (rule: "its words count")
  4. total_words is the sum of word counts      (rule: "sum of every word counted")
  5. formatting: 2-space indent + trailing NL   (rule: "indented by two spaces ...")
  6. the agent's program reproduces all of the above on inputs it has never seen
  7. the program is deterministic
  8. the verifier's own goldens are not reachable by the code it executes
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
SRC = APP / "src" / "summarize.py"
REPORT = APP / "out" / "report.json"
DATA = APP / "data"

# Held-out fixtures, baked into the verifier image. Never reachable from /app.
FIXTURES = Path("/fixtures")

# Scratch space owned by the sandbox user; see tests/Dockerfile.
WORK_OUT = Path("/work/out")

SANDBOX_UID = 12000
DROP_PRIVILEGES = [
    "setpriv",
    f"--reuid={SANDBOX_UID}",
    f"--regid={SANDBOX_UID}",
    "--clear-groups",
]

# SHA-256 of the report each input set must produce. Regenerate with:
#   python3 solution/src/summarize.py --data <dir> --out <tmp> && sha256sum <tmp>
EXPECTED_PRIMARY = "60fec4718722649de61a0a56094fa49cf19597bd942244b27c77cea81352ce57"

# Each held-out set isolates one rule, so a single-rule regression is attributable.
HOLDOUTS = {
    # sorted order differs from creation order and from every plausible scandir order
    "h_order": "78010904ea0a3b77bf165448e278c1ef0754ceda2926c68d95becd2fe3d9b020",
    # distinct per-file counts: total==sum is separable from total==len(files)
    "h_words": "ffec8028e09994e97e6cf406b191f9527af3204373238d89355908667f74e3b5",
    # tabs, runs of spaces, blank lines, missing trailing newline, empty file
    "h_mixed": "654f6a4877f98df4447a65a4b66efb0011c920dc9b6375278cb64d8a6393c316",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_report(data_dir):
    """Independent recomputation of the report, used for semantic assertions."""
    entries = [
        {"name": p.name, "words": len(p.read_text().split())}
        for p in sorted(Path(data_dir).glob("*.txt"), key=lambda p: p.name)
    ]
    return {"files": entries, "total_words": sum(e["words"] for e in entries)}


def run_agent_program(data_dir, out_path):
    """Runs the agent's own program, unprivileged, against a directory of our choosing."""
    return subprocess.run(
        DROP_PRIVILEGES
        + ["python3", str(SRC), "--data", str(data_dir), "--out", str(out_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )


# --------------------------------------------------------------------------
# Axis 1: the artifact exists and has the documented shape
# --------------------------------------------------------------------------

def test_report_exists():
    """The declared artifact was produced at the documented path."""
    assert REPORT.is_file(), f"{REPORT} was not created"


def test_report_is_valid_json():
    """The report parses and carries exactly the documented top-level keys."""
    data = json.loads(REPORT.read_text())
    assert set(data) == {"files", "total_words"}, (
        f"unexpected top-level keys: {sorted(data)}"
    )
    assert isinstance(data["files"], list), "'files' must be an array"
    for entry in data["files"]:
        assert set(entry) == {"name", "words"}, (
            f"each file entry must have exactly 'name' and 'words'; got {sorted(entry)}"
        )


# --------------------------------------------------------------------------
# Axes 2-5: one rule per test, on the shipped inputs.
# Each fails independently of the others.
# --------------------------------------------------------------------------

def test_entries_are_ordered_by_name():
    """Rule: entries are ordered by name.

    Asserted semantically rather than only through the golden hash, so the check does
    not depend on the order Path.glob happens to return on the build filesystem.
    """
    names = [e["name"] for e in json.loads(REPORT.read_text())["files"]]
    assert names == sorted(names), f"entries are not ordered by name: {names}"


def test_per_file_word_counts_are_correct():
    """Rule: each entry carries the word count of its file."""
    actual = {e["name"]: e["words"] for e in json.loads(REPORT.read_text())["files"]}
    wanted = {e["name"]: e["words"] for e in expected_report(DATA)["files"]}
    assert actual == wanted, f"word counts differ\n  expected {wanted}\n  actual   {actual}"


def test_total_words_is_the_sum_of_word_counts():
    """Rule: total_words holds the sum of every word counted.

    The shipped fixture set has 3 files and 16 words, so a total that counts files
    instead of words is caught here and not only by the byte comparison.
    """
    data = json.loads(REPORT.read_text())
    assert data["total_words"] == sum(e["words"] for e in data["files"]), (
        f"total_words={data['total_words']} is not the sum of the per-file counts"
    )
    assert data["total_words"] != len(data["files"]) or len(data["files"]) == 0, (
        "total_words equals the file count; it must be the word count"
    )


def test_formatting_is_two_space_indent_with_trailing_newline():
    """Rule: indented by two spaces, ends with a trailing newline."""
    raw = REPORT.read_bytes()
    assert raw.endswith(b"\n"), "report.json does not end with a trailing newline"
    assert not raw.endswith(b"\n\n"), "report.json ends with more than one newline"
    text = raw.decode()
    assert text == json.dumps(json.loads(text), indent=2) + "\n", (
        "report.json is not serialised with an indent of two spaces"
    )


def test_report_matches_approved_bytes():
    """The report is byte-identical to the approved output for the shipped inputs."""
    actual = sha256(REPORT)
    assert actual == EXPECTED_PRIMARY, (
        f"report.json does not match the approved bytes\n"
        f"  expected sha256 {EXPECTED_PRIMARY}\n  actual   sha256 {actual}"
    )


# --------------------------------------------------------------------------
# Axis 6: the program re-derives the result on unseen inputs.
# One held-out set per rule, so a single-rule regression is attributable.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(HOLDOUTS))
def test_holdout_reproduces_approved_bytes(name):
    """Re-running the agent's program on unseen inputs reproduces the approved bytes.

    This is the anti-cheat axis: it proves the report on disk was generated by the
    program rather than written by hand or pinned to the shipped fixtures.
    """
    out = WORK_OUT / f"{name}.json"
    result = run_agent_program(FIXTURES / name, out)
    assert result.returncode == 0, f"program failed on held-out set {name}:\n{result.stderr}"

    actual = sha256(out)
    assert actual == HOLDOUTS[name], (
        f"held-out set {name} did not reproduce the approved bytes\n"
        f"  expected sha256 {HOLDOUTS[name]}\n  actual   sha256 {actual}"
    )


@pytest.mark.parametrize("name", sorted(HOLDOUTS))
def test_holdout_is_semantically_correct(name):
    """The held-out result is right rule-by-rule, not merely hash-equal.

    Keeps each rule enforced on unseen data even if a golden is ever regenerated
    against a regressed reference.
    """
    out = WORK_OUT / f"sem-{name}.json"
    assert run_agent_program(FIXTURES / name, out).returncode == 0, (
        f"program failed on held-out set {name}"
    )
    data = json.loads(out.read_text())
    wanted = expected_report(FIXTURES / name)

    names = [e["name"] for e in data["files"]]
    assert names == sorted(names), f"{name}: entries not ordered by name: {names}"
    assert data["files"] == wanted["files"], f"{name}: per-file counts differ"
    assert data["total_words"] == wanted["total_words"], (
        f"{name}: total_words={data['total_words']}, expected {wanted['total_words']}"
    )
    assert out.read_bytes().endswith(b"\n"), f"{name}: missing trailing newline"


# --------------------------------------------------------------------------
# Axis 7: determinism
# --------------------------------------------------------------------------

def test_output_is_deterministic():
    """Two runs over the same inputs produce identical bytes."""
    first, second = WORK_OUT / "det-1.json", WORK_OUT / "det-2.json"
    for out in (first, second):
        assert run_agent_program(DATA, out).returncode == 0, "program failed on shipped inputs"
    assert sha256(first) == sha256(second), "program output is not deterministic"


# --------------------------------------------------------------------------
# Axis 8: the code the verifier executes cannot reach the verifier's own state.
# Separate mode isolates the verifier from the agent's container, not from the
# agent's code once the verifier itself runs it.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "target",
    ["/tests/test_outputs.py", "/logs/verifier", "/logs/verifier/reward.txt"],
)
def test_sandbox_cannot_read_verifier_state(target):
    """The unprivileged user that runs agent code cannot read goldens or the reward."""
    probe = subprocess.run(
        DROP_PRIVILEGES + ["cat", target],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert probe.returncode != 0, (
        f"sandbox uid {SANDBOX_UID} can read {target}; agent code executed by the "
        f"verifier could read or forge its own grade"
    )


def test_sandbox_cannot_write_reward():
    """The unprivileged user cannot plant its own verdict."""
    probe = subprocess.run(
        DROP_PRIVILEGES + ["sh", "-c", "echo 1 > /logs/verifier/reward.txt"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert probe.returncode != 0, (
        f"sandbox uid {SANDBOX_UID} can write the reward file"
    )


def test_fixtures_are_not_reachable_from_app():
    """Held-out fixtures live in the verifier image only, never under the artifact tree."""
    assert FIXTURES.is_dir(), "/fixtures missing from the verifier image"
    leaked = [p for p in APP.rglob("*") if p.name in HOLDOUTS]
    assert not leaked, f"held-out fixture names appear under /app: {leaked}"
