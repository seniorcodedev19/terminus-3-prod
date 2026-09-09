#!/bin/bash
# Oracle solution.
#
# What was actually wrong in /app/src/summarize.py, and how each fix is derivable from
# the spec in instruction.md rather than from guessing:
#
#   1. Ordering.   Entries were emitted in Path.glob order, which is the filesystem's
#                  directory order, not sorted order. The spec says the array is
#                  "ordered by name", so the iteration is sorted on path.name.
#
#   2. total_words. The field was set to len(entries) -- the number of files -- which
#                  coincides with the correct value only when every file holds exactly
#                  one word. The spec says it holds "the sum of every word counted",
#                  so it is sum(e["words"]).
#
#   3. Trailing newline. json.dumps() returns no terminator and the result was written
#                  as-is. The spec says the report "ends with a trailing newline".
#
# The program must keep its CLI contract (--data/--out at /app/src/summarize.py),
# because the verifier re-runs it against directories it has never seen.
#
# Harbor mounts solution/ at /solution/ and runs this script as the oracle agent.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$HERE/src/summarize.py" /app/src/summarize.py

python3 /app/src/summarize.py --data /app/data --out /app/out/report.json

sha256sum /app/out/report.json
