#!/bin/bash
# Verifier entrypoint. Runs in the separate verifier container.
#
# Deliberately NOT `set -e`: a failing pytest must still reach the reward write below.
set -uo pipefail

mkdir -p /logs/verifier
# The verifier executes agent-produced code, so keep the reward and the logs out of
# its reach before any test runs. test_outputs.py probes that this actually holds.
chmod 700 /logs /logs/verifier 2>/dev/null || chmod 700 /logs/verifier

# The artifact tree arrives owned by root; the sandbox user needs to read the agent's
# program in order to execute it, but nothing under /app should be writable by it.
chmod -R a+rX /app 2>/dev/null || true
chmod -R go-w /app 2>/dev/null || true

/venv/bin/python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
