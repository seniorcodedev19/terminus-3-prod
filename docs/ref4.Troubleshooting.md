Solutions to common issues you might encounter.

Installation Issues
Installing harbor fails with 403 Forbidden
That install method is retired — the old Harbor promptfix wheel URL no longer serves. Install the Snorkel CLI instead:

bash

Copy
uv tool install snorkelai-stb \
  --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html \
  --python ">=3.12"
See the Quick Start or CLI User Guide. (A 403 when upgrading stb is different — that's a temporarily rotated link; retry later.)

Docker Issues
"Cannot connect to Docker daemon"
Cause: Docker Desktop isn't running.

Fix:

Start Docker Desktop
Wait for it to fully initialize (check menu bar icon)
Try again
"Permission denied" on Docker socket
Fix (macOS):

bash

Copy
sudo chmod 666 /var/run/docker.sock
Or enable in Docker Desktop:

Settings → Advanced
Enable "Allow the default Docker socket to be used"
Fix (Linux):

bash

Copy
sudo usermod -aG docker $USER
# Log out and back in
Container won't build
Check:

Dockerfile syntax is valid
Base image exists
All COPY source files exist
Debug:

bash

Copy
cd <task-folder>
docker build -t test . 2>&1 | tail -50
Container starts but commands fail
Enter interactive mode to debug:

bash

Copy
stb harbor tasks start-env -p <task-folder> -i
Then run commands manually to find the issue.

CI / Check Issues
Checks pass locally but fail in PR
Common causes:

Python version mismatch

Check CI logs for version used
Test locally with same version
Missing dependency

Ensure all imports are in requirements
Path differences

Use absolute paths everywhere
Environment variables

Don't rely on local env vars
"pinned_dependencies" failure
Fix: Add exact versions to all pip (or npm, etc.) installs. Make sure every Docker base image (and any pulled image: lines in docker-compose.yaml) includes an immutable @sha256:<digest> pin.

dockerfile

Copy
# Before
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm
RUN pip install numpy pandas

# After
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:<digest>
RUN pip install numpy==1.26.4 pandas==2.1.0
"check_task_absolute_path" failure
Fix: Change relative paths to absolute in instruction.md:

Before:

markdown

Copy
Edit config/settings.json
After:

markdown

Copy
Edit `/app/config/settings.json`
"informative_test_docstrings" failure
Fix: Add docstrings to all test functions:

python

Copy
def test_output_exists():
    """Verify the output file is created at /output/result.json."""
    assert Path("/output/result.json").exists()
Agent Issues
API key not working
AI credentials are managed by the stb CLI — you don't set OPENAI_API_KEY / OPENAI_BASE_URL manually.

Check:

You're logged in with current credentials:
bash

Copy
stb login
stb keys refresh
Your stored credentials are still valid:
bash

Copy
stb keys verify
If stb keys refresh fails with "Maximum refresh limit reached," you've hit the cap — ask an admin in Slack to reset it.
Agent times out
Possible causes:

Task timeout too short (increase in task.toml)
Solution is inefficient
Environment is slow to start
Task is too complicated
Fix:

toml

Copy
# In task.toml
[agent]
timeout_sec = 1200.0  # Increase from default
Agent passes too often
Your task is too easy. Make it harder by:

Adding more steps
Using niche knowledge
Creating debugging scenarios
Adding edge cases
Platform Issues
Can't log in
Clear browser cache and cookies
Try incognito/private mode
Verify email address is correct
Try different browser
Contact Slack if still failing
Upload fails
Check file size (< 100MB)
Ensure ZIP structure is correct
Try a different browser
Check internet connection
Session expires frequently
Enable "Remember me" on login
Check browser isn't blocking cookies
Disable interfering extensions
Getting Help
Before asking:
✅ Read the error message carefully
✅ Search this documentation (⌘K)
✅ Check Slack for similar issues
✅ Try the suggested fix
When asking:
Include:

What you're trying to do
What's happening instead
Full error message
What you've already tried
Bad:

"It's not working"

Good:

"When I run stb harbor run -a oracle, I get FileNotFoundError: /app/data/input.csv. The file exists in my task folder and is included in the Dockerfile COPY command. Full error: [paste]"

Where to ask:
Slack: #terminus-3-submissions
Payment issues: Reach out to Snorkel