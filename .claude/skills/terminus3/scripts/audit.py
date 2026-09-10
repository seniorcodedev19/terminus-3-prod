#!/usr/bin/env python3
"""Audit a Terminus 3 task folder against the deterministic submission rules.

Covers the mechanical checks from the Terminus 3 docs, including the two platform-only
preflights that `stb harbor check` does not run (cloud image builder syntax and
verifier_interpreter_permissions). Does not replace `stb harbor check`, the Oracle run,
or the Quality Panel.

    python audit.py <task-folder>       # defaults to the current directory
    python audit.py <folder> --quiet    # errors only

Exit codes: 0 clean or warnings only, 1 errors found, 2 could not read the folder.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:  # 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore

TIERS = {"frontier", "advanced", "core", "base"}
RETIRED_TIERS = {"easy", "medium", "hard", "trivial"}
NET_MODES = {"public", "no-network"}
MAX_TIMEOUT = 18000
MIN_AGENT_TIMEOUT = 1800
CONTEXT_LIMIT = 100 * 1024 * 1024
FILE_LIMIT = 50 * 1024 * 1024

CATEGORIES = {
    "Science": {"Biology", "Chemistry", "Physics", "Earth", "Robotics", "Math", "Linguistics"},
    "Software": {"Algorithms", "Systems", "Databases", "Data engineering", "Frontend", "Languages"},
    "ML": {"Training", "Inference", "Evaluation", "Kernels"},
    "Operations": {"Finance", "Logistics", "Supply chain", "Claims", "Compliance", "Marketing"},
    "Security": {"Cryptography", "Reverse engineering", "Forensics", "AppSec"},
    "Hardware": {"CAD", "RTL"},
    "Media": {"Music", "Design"},
}

METADATA_FIELDS = [
    "author_name", "author_email", "category", "subcategory", "tags", "languages",
    "difficulty", "expert_time_estimate_hours", "difficulty_explanation",
    "solution_explanation", "verification_explanation", "relevant_experience",
]

SCAFFOLD_NAMES = {"CLAUDE.md", "skills.md", "AGENTS.md", "SKILL.md", ".cursor", ".claude", "copilot-instructions.md"}
BUNDLE_MEMBERS = {"task.toml", "instruction.md", "environment", "solution", "tests"}
RESERVED_PATHS = ("/logs/verifier", "/logs/artifacts", "/oracle", "/tests")
NET_FETCH = re.compile(r"\b(curl|wget|pip\s+install|uv\s+pip\s+install|uvx|npm\s+install|"
                       r"apt-get\s+install|apt\s+install|git\s+clone|cargo\s+fetch|mvn\s+dependency:get)\b")


class Report:
    def __init__(self, quiet: bool = False) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.quiet = quiet

    def add(self, level: str, where: str, msg: str) -> None:
        self.rows.append((level, where, msg))

    def error(self, where: str, msg: str) -> None:
        self.add("ERROR", where, msg)

    def warn(self, where: str, msg: str) -> None:
        self.add("WARN", where, msg)

    def info(self, where: str, msg: str) -> None:
        self.add("INFO", where, msg)

    def render(self) -> int:
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        rows = [r for r in self.rows if not (self.quiet and r[0] != "ERROR")]
        for level, where, msg in sorted(rows, key=lambda r: (order[r[0]], r[1])):
            print(f"{level:<5}  {where}: {msg}")
        errors = sum(1 for r in self.rows if r[0] == "ERROR")
        warns = sum(1 for r in self.rows if r[0] == "WARN")
        if not rows:
            print("No findings.")
        print(f"\n{errors} error(s), {warns} warning(s)")
        if errors == 0:
            print("Deterministic checks clean. Still required: stb harbor check, "
                  "Oracle run, a deliberately wrong solution, and the Quality Panel checklist.")
        return 1 if errors else 0


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_layout(root: Path, rep: Report) -> None:
    for required in ("task.toml", "instruction.md"):
        if not (root / required).is_file():
            rep.error(required, "missing")
    for required in ("environment", "solution", "tests"):
        if not (root / required).is_dir():
            rep.error(f"{required}/", "missing")

    for name in ("environment/Dockerfile", "solution/solve.sh",
                 "tests/Dockerfile", "tests/test.sh", "tests/test_outputs.py"):
        p = root / name
        if not p.is_file():
            if name == "environment/Dockerfile" and (root / "environment/docker-compose.yaml").is_file():
                continue
            rep.error(name, "missing")

    for packaged in ("rubrics.txt", "README.md"):
        if (root / packaged).exists():
            rep.warn(packaged, "added by Snorkel at packaging — do not ship it in the ZIP")

    # AI scaffolding is a High-severity reviewer criterion inside the task environment.
    for sub in ("environment", "solution", "tests"):
        d = root / sub
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.name in SCAFFOLD_NAMES:
                rep.error(f"{sub}/{p.relative_to(d)}",
                          "AI-scaffolding name inside the task bundle (High severity) — remove before submitting")

    for p in root.iterdir():
        if p.name in BUNDLE_MEMBERS or p.name in {".git", ".gitignore"}:
            continue
        if p.name in SCAFFOLD_NAMES or p.name == "docs":
            rep.info(p.name, "outside the bundle — keep it out of the submission ZIP")

    tokens = len(root.resolve().name.split("-"))
    if tokens > 5:
        rep.warn(root.resolve().name, f"folder name has {tokens} hyphen-separated tokens — the check caps this")


def check_task_toml(root: Path, rep: Report) -> dict:
    path = root / "task.toml"
    if not path.is_file():
        return {}
    if tomllib is None:
        rep.warn("task.toml", "no TOML parser (need Python 3.11+ or tomli) — manifest checks skipped")
        return {}
    try:
        data = tomllib.loads(read(path))
    except Exception as exc:
        rep.error("task.toml", f"does not parse: {exc}")
        return {}

    where = "task.toml"
    meta = data.get("metadata", {})
    verifier = data.get("verifier", {})
    agent = data.get("agent", {})
    env = data.get("environment", {})

    if "artifacts" not in data:
        rep.error(where, "no top-level `artifacts` — the verifier receives nothing")
    if "artifacts" in verifier:
        rep.error(where, "`artifacts` nested under [verifier] — silently dropped, move it top-level")
    if not data.get("name") and not meta.get("name"):
        rep.error(where, "`name` missing (top level or [metadata])")

    for field in METADATA_FIELDS:
        if field not in meta:
            rep.error(where, f"[metadata].{field} missing")
        if field in data:
            rep.warn(where, f"top-level `{field}` is not counted — move it under [metadata]")

    cat, sub = meta.get("category"), meta.get("subcategory")
    if cat is not None:
        if cat not in CATEGORIES:
            rep.error(where, f"category {cat!r} is not in the taxonomy")
        elif sub is not None and sub not in CATEGORIES[cat]:
            rep.error(where, f"subcategory {sub!r} is not valid for category {cat!r}")

    diff = meta.get("difficulty")
    if isinstance(diff, str):
        if diff.lower() in RETIRED_TIERS:
            rep.error(where, f"difficulty {diff!r} is retired — use frontier/advanced/core/base")
        elif diff not in TIERS:
            rep.error(where, f"difficulty {diff!r} is not a valid tier")

    tags = meta.get("tags")
    if isinstance(tags, list) and not (3 <= len(tags) <= 6):
        rep.error(where, f"tags has {len(tags)} entries — needs 3–6")
    if isinstance(meta.get("languages"), list) and not meta["languages"]:
        rep.error(where, "languages is empty")

    for field in ("difficulty_explanation", "solution_explanation",
                  "verification_explanation", "relevant_experience"):
        val = meta.get(field)
        if isinstance(val, str) and len(val.strip()) < 40:
            rep.warn(where, f"[metadata].{field} is very short — it becomes the packaged README")

    mode = verifier.get("environment_mode")
    if mode != "separate":
        rep.error(where, f"[verifier].environment_mode must be the explicit \"separate\" (found {mode!r})")
    if "environment" in verifier and mode == "shared":
        rep.error(where, "environment_mode=\"shared\" plus [verifier.environment] is invalid")

    if "network_mode" in data:
        rep.error(where, "top-level `network_mode` is ignored — set it per phase")
    if "allow_internet" in data or "allow_internet" in env:
        rep.error(where, "`allow_internet` is rejected — it cannot express a per-phase policy")

    if env.get("network_mode") != "public":
        rep.error(where, f"[environment].network_mode must be \"public\" (found {env.get('network_mode')!r}) — "
                         "the build and harness install need it; every trial dies before the agent starts")
    for phase, table in (("agent", agent), ("verifier", verifier)):
        nm = table.get("network_mode")
        if nm is None:
            rep.error(where, f"[{phase}].network_mode missing — an omitted phase silently inherits the baseline")
        elif nm == "allowlist":
            rep.error(where, f"[{phase}].network_mode=\"allowlist\" is unsupported — reports 'Oracle ran 0 trials'")
        elif nm not in NET_MODES:
            rep.error(where, f"[{phase}].network_mode {nm!r} is not valid")
    if "allowed_hosts" in agent or "allowed_hosts" in verifier or "allowed_hosts" in env:
        rep.error(where, "`allowed_hosts` is rejected — production sandboxes have no allowlist capability")

    at, vt = agent.get("timeout_sec"), verifier.get("timeout_sec")
    if isinstance(at, (int, float)):
        if at > MAX_TIMEOUT:
            rep.error(where, f"[agent].timeout_sec {at} exceeds the {MAX_TIMEOUT} ceiling")
        elif at < MIN_AGENT_TIMEOUT:
            rep.error(where, f"[agent].timeout_sec {at} is below the {MIN_AGENT_TIMEOUT} minimum (reviewer criterion)")
    else:
        rep.error(where, "[agent].timeout_sec missing")
    if isinstance(vt, (int, float)):
        if vt > MAX_TIMEOUT:
            rep.error(where, f"[verifier].timeout_sec {vt} exceeds the {MAX_TIMEOUT} ceiling")
    else:
        rep.error(where, "[verifier].timeout_sec missing")
    if "build_timeout_sec" not in env:
        rep.warn(where, "[environment].build_timeout_sec not set")

    if env.get("gpus"):
        rep.error(where, "Terminus 3 tasks must not require a GPU")
    return data


def join_continuations(lines: list[str]) -> list[tuple[int, str]]:
    """Collapse backslash-continued Dockerfile/shell lines, keeping the starting line number."""
    joined: list[tuple[int, str]] = []
    buf, start = "", 0
    for i, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not buf:
            start = i
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        joined.append((start, (buf + stripped).strip()))
        buf = ""
    if buf:
        joined.append((start, buf.strip()))
    return joined


def check_dockerfile(path: Path, rel: str, rep: Report, *, is_agent_image: bool) -> None:
    if not path.is_file():
        return
    lines = read(path).splitlines()
    saw_from = False
    text = "\n".join(lines)

    for i, raw in join_continuations(lines):
        line, where = raw.strip(), f"{rel}:{i}"
        if line.startswith("#"):
            continue

        if re.match(r"(?i)^FROM\s", line):
            saw_from = True
            if "--platform" in line:
                rep.error(where, "FROM --platform= pins a CPU architecture — not portable")
            if "@sha256:" not in line:
                rep.error(where, "FROM is not digest-pinned with @sha256:<digest>")
            if re.search(r"(?i):latest\b", line):
                rep.error(where, "floating `latest` tag")

        # Cloud image builder preflight (check_modal_dockerfile_compat).
        m = re.search(r"--chown=([^\s]+)", line)
        if m and not re.fullmatch(r"\d+(:\d+)?", m.group(1)):
            rep.error(where, f"COPY --chown={m.group(1)} uses names — cloud builder needs numeric IDs (0:0)")
        m = re.search(r"--from=([^\s]+)", line)
        if m:
            ref = m.group(1)
            if "@sha256:" in ref and ":" in ref.split("@")[0]:
                rep.error(where, f"COPY --from={ref} has tag+digest — drop the :tag, keep @sha256:")

        if re.search(r"\bnproc\b", line):
            rep.error(where, "bare nproc reports host CPUs, not the task's limit")
        for m in re.finditer(r"(?i)\b(?:pip3?|uv\s+pip)\s+install\b(.*?)(?=&&|;|$)", line):
            args = m.group(1)
            if "-r" in args or "requirements" in args or "." == args.strip():
                continue
            for pkg in re.findall(r"(?<![\w=./-])([A-Za-z][\w.\[\]-]*)(?=\s|$)", re.sub(r"(^|\s)-{1,2}[\w-]+(=\S+)?", " ", args)):
                if f"{pkg}==" not in args:
                    rep.error(where, f"pip install of {pkg!r} without an exact == pin")

        for m in re.finditer(r"(?i)\bapt(?:-get)?\s+install\b(.*?)(?=&&|;|$)", line):
            args = re.sub(r"(^|\s)-{1,2}[\w-]+", " ", m.group(1))
            for pkg in re.findall(r"(?<![\w.+-])([\w.+-]+)=([\w.:+~-]+)", args):
                rep.error(where, f"apt package {pkg[0]!r} pinned with =version — apt installs must be unpinned")
        if re.search(r"(?i)apt-get\s+upgrade", line):
            rep.error(where, "apt-get upgrade is not allowed")
        if re.search(r"(?i)^RUN\s+.*\bcat\s*>.*<<", line):
            rep.warn(where, "source embedded via heredoc — store files as files")
        for reserved in RESERVED_PATHS:
            if re.search(rf"(?i)^RUN\s+.*\b(mkdir|chown|chmod)\b.*{re.escape(reserved)}\b", line):
                rep.error(where, f"{reserved} is reserved by Harbor — creating/chowning it breaks the runtime mount")

    if not saw_from:
        rep.error(rel, "no FROM instruction")

    if is_agent_image:
        for tool in ("tmux", "asciinema"):
            if not re.search(rf"\b{tool}\b", text):
                rep.error(rel, f"{tool} not installed — the agent runtime cannot start a session without it")
        if re.search(r"(?im)^COPY\s+(--[\w=:.]+\s+)*(\./)?(tests|solution)/", text):
            rep.error(rel, "copies tests/ or solution/ into the agent image")
        if re.search(r"(?im)^COPY\s+(--[\w=:.]+\s+)*\.\s", text):
            rep.warn(rel, "COPY . — narrow it, or ensure .dockerignore excludes tests/ and solution/")


def check_instruction(root: Path, rep: Report) -> None:
    path = root / "instruction.md"
    if not path.is_file():
        return
    text = read(path)
    rel = "instruction.md"

    for frag in ("REPLACE", "TODO", "<placeholder>", "repr(", "object at 0x"):
        if frag in text:
            rep.error(rel, f"leftover template/debug fragment {frag!r} — a coherent_contract finding")
    if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", text):
        rep.warn(rel, "contains emoji — instructions should read like a human prompt")

    paths = re.findall(r"`([^`\n]+)`", text)
    rels = [p for p in paths
            if ("/" in p and not p.startswith(("/", "http", "-", "--")) and not p.startswith("~"))
            and not re.match(r"^[\w.-]+\s", p)]
    for p in dict.fromkeys(rels):
        rep.warn(rel, f"`{p}` looks like a relative path — instructions must use absolute paths")

    words = len(text.split())
    if words > 700:
        rep.warn(rel, f"{words} words — aim for ~2 short paragraphs or up to 20 bullets")
    if len(re.findall(r"(?m)^#{2,}\s", text)) > 6:
        rep.warn(rel, "heavy markdown structure reads like documentation, not a human prompt")
    if re.search(r"(?im)^\s*(step\s*\d|first,|then,|next,|finally,)", text):
        rep.warn(rel, "looks like a step-by-step walkthrough — give the what, not the how")
    if re.search(r"(?i)\b(hint|guidance|look for|tip:)\b", text):
        rep.warn(rel, "possible hints section — instructions must not give away the approach")


def tests_missing_docstrings(text: str) -> list[tuple[str, int]]:
    """Find test functions whose body does not open with a docstring.

    Balances parentheses so a multi-line signature is followed to its real `:`, and never
    scans past the end of one function into the next.
    """
    missing: list[tuple[str, int]] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"[ \t]*def (test_\w+)\s*\(", line)
        if not m:
            continue
        depth, end = 0, None
        for j in range(i, len(lines)):
            for ch in lines[j]:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            if depth <= 0:
                end = j
                break
        if end is None:
            continue
        for k in range(end + 1, len(lines)):
            body = lines[k].strip()
            if not body or body.startswith("#"):
                continue
            if not body.startswith(('"""', "'''", '"', "'", 'r"""', "r'''")):
                missing.append((m.group(1), i + 1))
            break
    return missing


def check_tests(root: Path, rep: Report, artifacts: list) -> None:
    sh = root / "tests/test.sh"
    if sh.is_file():
        text, rel = read(sh), "tests/test.sh"
        if re.search(r"(?m)^\s*set\s+-[a-z]*e", text):
            rep.error(rel, "`set -e` aborts before the reward is written — a real failure becomes an infra error")
        if "--ctrf" not in text:
            rep.error(rel, "pytest must run with --ctrf /logs/verifier/ctrf.json (ctrf_reporting check)")
        if "/logs/verifier/reward.txt" not in text:
            rep.error(rel, "never writes /logs/verifier/reward.txt")
        else:
            if not re.search(r"echo\s+0\s*>\s*/logs/verifier/reward\.txt", text):
                rep.error(rel, "no failure path writing 0 to reward.txt — causes RewardNotFoundError")
        if re.search(r"(?m)^\s*exit\s+\d*\s*$", text.split("reward.txt")[-1]):
            rep.warn(rel, "trailing exit after the reward write masks a failed write")
        for line_no, line in join_continuations(text.splitlines()):
            if line.lstrip().startswith("#"):
                continue
            m = NET_FETCH.search(line)
            if m:
                rep.error(f"{rel}:{line_no}",
                          f"trial-time network fetch `{m.group(0)}` — bake it into tests/Dockerfile")
        if re.search(r"\$\{?TEST_DIR\}?", text) and "TEST_DIR:-" not in text:
            rep.warn(rel, "TEST_DIR used without a ${TEST_DIR:-/tests} default")
        if re.search(r"(?i)if\s*\[\s*-d\s+[\"']?/oracle", text):
            rep.error(rel, "branches on /oracle — oracle and agent must run identical conditions")

    py = sorted((root / "tests").rglob("*.py")) if (root / "tests").is_dir() else []
    for p in py:
        text, rel = read(p), f"tests/{p.relative_to(root / 'tests')}"

        for i, line in enumerate(text.splitlines(), 1):
            if "request.node.name" in line:
                rep.error(f"{rel}:{i}", "test identity leaks via request.node.name (label_from_basename)")
            if re.search(r"copytree\s*\(", line):
                rep.error(f"{rel}:{i}", "hand-staging an agent tree — copytree follows symlinks; "
                                        "symlinks=False is not a guard")
            for word in ("reject", "invalid", "accept"):
                if re.search(rf"['\"][^'\"]*\b{word}\b[^'\"]*['\"]", line) and re.search(r"(?i)(path|dir|env|arg)", line):
                    rep.warn(f"{rel}:{i}", f"outcome word {word!r} in a candidate-visible path/arg — use a neutral id")
            if re.search(r"(?i)\bassert\b.*\b(p50|p95|p99|latency|elapsed|duration)\b", line):
                rep.warn(f"{rel}:{i}", "latency/performance assertion — hardware-dependent, not reproducible")
            if re.search(r"\bsetpriv\b", line) and "--no-new-privs" not in text:
                rep.error(f"{rel}:{i}", "setpriv without --no-new-privs — a setuid binary can regain privilege")
            if re.search(r"(?i)open\(['\"]/app/.*\)\.read\(\).*expected|expected.*=.*['\"]/app/", line):
                rep.warn(f"{rel}:{i}", "ground truth read from an agent-writable path")

        # verifier_interpreter_permissions: the dual-path restore pattern.
        if "/bin/bash" in text and "/usr/bin/bash" in text and re.search(r"(?i)chmod|st_mode", text):
            if "resolve()" not in text:
                rep.error(rel, "saves/restores both /bin/bash and /usr/bin/bash without Path.resolve() dedup — "
                               "blocking platform preflight (verifier_interpreter_permissions)")
            if re.search(r"chmod\(\s*0o?755\s*\)", text):
                rep.error(rel, "restores a hardcoded 0755 instead of each saved mode")

        for name, line_no in tests_missing_docstrings(text):
            rep.error(f"{rel}:{line_no}", f"{name} has no docstring (informative_test_docstrings)")

    dockerfile = root / "tests/Dockerfile"
    if dockerfile.is_file():
        text = read(dockerfile)
        for art in artifacts or []:
            if not isinstance(art, str):
                continue
            parent = art.rstrip("/").rsplit("/", 1)[0] or "/"
            if parent != "/" and not re.search(rf"mkdir\s+-p[^\n]*{re.escape(parent)}", text):
                rep.error("tests/Dockerfile",
                          f"no landing directory for artifact {art} — add `RUN mkdir -p {parent}` or the upload fails")
        if not re.search(r"(?i)\bpytest\b", text):
            rep.warn("tests/Dockerfile", "pytest not installed in the verifier image")
        if re.search(r"(?i)pip\s+install", text) and "==" not in text:
            rep.error("tests/Dockerfile", "verifier dependencies must be pinned to exact versions")


def check_canary(root: Path, rep: Report) -> None:
    """Canary strings are banned in every component — they signal an older task skeleton."""
    pattern = re.compile(r"(?i)(terminal-bench-canary|canary\s+GUID|BENCHMARK DATA SHOULD NEVER)")
    for sub in ("environment", "solution", "tests"):
        d = root / sub
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix in {".png", ".jpg", ".gz", ".zip", ".pdf"}:
                continue
            try:
                text = read(p)
            except OSError:
                continue
            m = pattern.search(text)
            if m:
                line = text[:m.start()].count("\n") + 1
                rep.error(f"{sub}/{p.relative_to(d)}:{line}",
                          "canary string — banned in every component; remove it (older-skeleton indicator)")
    for name in ("instruction.md", "task.toml"):
        p = root / name
        if p.is_file():
            m = pattern.search(read(p))
            if m:
                rep.error(name, "canary string — banned in every component; remove it")


def check_reward_channel(root: Path, rep: Report) -> None:
    """The reward must be written only by the verifier, after grading."""
    for p in sorted((root / "tests").rglob("*.py")) if (root / "tests").is_dir() else []:
        text, rel = read(p), f"tests/{p.relative_to(root / 'tests')}"
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if re.search(r"reward\.txt", line) and re.search(r"(?i)\b(open|write_text|chmod)\b", line):
                rep.warn(f"{rel}:{i}",
                         "test code touching reward.txt — the reward belongs to test.sh, written after grading")
            if re.search(r"(?i)\b(Popen|subprocess\.run|check_call)\b", line) and "wait" not in text:
                if re.search(r"(?i)\b(start_new_session|daemon|&\s*['\"]?\s*$)", line):
                    rep.warn(f"{rel}:{i}",
                             "agent-spawned process may outlive grading and overwrite the reward")


def check_solution(root: Path, rep: Report) -> None:
    path = root / "solution/solve.sh"
    if not path.is_file():
        return
    text, rel = read(path), "solution/solve.sh"
    if not re.search(r"(?m)^\s*set\s+-[a-z]*e", text):
        rep.warn(rel, "no `set -e` — the oracle should fail fast")
    if re.search(r"(?i)\b(curl|wget)\s+https?://", text):
        rep.error(rel, "network fetch in the oracle — endpoints change and break the task")
    if re.search(r"\bnproc\b", text):
        rep.error(rel, "bare nproc reports host CPUs, not the task's limit")
    if re.search(r"random\.(?!seed)", text) and "seed" not in text:
        rep.warn(rel, "randomness without a seed — the oracle must be deterministic")


def check_context_size(root: Path, rep: Report) -> None:
    env = root / "environment"
    if not env.is_dir():
        return
    total = 0
    for p in env.rglob("*"):
        if not p.is_file():
            continue
        size = p.stat().st_size
        total += size
        if size > FILE_LIMIT:
            rep.error(f"environment/{p.relative_to(env)}", f"{size / 1048576:.1f} MiB exceeds the 50 MiB file limit")
    if total > CONTEXT_LIMIT:
        rep.error("environment/", f"{total / 1048576:.1f} MiB exceeds the 100 MiB build-context limit")
    if not (env / ".dockerignore").is_file():
        rep.warn("environment/.dockerignore", "missing — required for all non-trivial tasks")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", default=".", help="task folder (default: current directory)")
    ap.add_argument("--quiet", action="store_true", help="errors only")
    args = ap.parse_args()

    root = Path(args.folder).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    rep = Report(quiet=args.quiet)
    print(f"Auditing {root}\n")

    check_layout(root, rep)
    data = check_task_toml(root, rep)
    check_instruction(root, rep)
    check_dockerfile(root / "environment/Dockerfile", "environment/Dockerfile", rep, is_agent_image=True)
    check_dockerfile(root / "tests/Dockerfile", "tests/Dockerfile", rep, is_agent_image=False)
    check_tests(root, rep, data.get("artifacts") or [])
    check_solution(root, rep)
    check_canary(root, rep)
    check_reward_channel(root, rep)
    check_context_size(root, rep)

    return rep.render()


if __name__ == "__main__":
    sys.exit(main())
