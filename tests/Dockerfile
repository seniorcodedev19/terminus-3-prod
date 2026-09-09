# Verifier image. In separate mode harbor does NOT upload tests/ at verify time, so
# this image must own everything the verifier needs: the tests themselves, any held-out
# fixtures, and every tool test.sh invokes. Nothing may be installed at verify time.
FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

# Debian marks the system interpreter externally managed, so pytest goes in a venv.
# util-linux provides setpriv, which the tests use to drop privileges before running
# agent-authored code.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir pytest==8.3.5 pytest-json-ctrf==0.3.5

# If the verifier executes anything the agent produced, it is running untrusted code.
# Drop it to an unprivileged user that owns nothing outside its own scratch space.
RUN useradd --system --uid 12000 --user-group --no-create-home --shell /usr/sbin/nologin sandbox \
    && mkdir -p /work/out \
    && chown sandbox:sandbox /work/out \
    && chmod 700 /work/out

# Tests and goldens: root-only. The expected hashes live in test_outputs.py, so the
# sandbox user must not be able to read this directory at all.
COPY test.sh test_outputs.py /tests/
RUN chmod 700 /tests && chmod 600 /tests/test.sh /tests/test_outputs.py

# Held-out fixtures live OUTSIDE /tests. The agent's program is executed as the sandbox
# user and must be able to read them, so they cannot sit next to the goldens.
COPY fixtures/ /fixtures/
RUN chmod -R a+rX /fixtures

# Landing directory for the declared artifact. Every artifact path in task.toml needs
# its parent to exist here, or the upload fails with "Could not find the file ...".
RUN mkdir -p /app
