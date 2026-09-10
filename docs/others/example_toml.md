# Example `task.toml` (after TBench 3.0 static-check update)

After the `task.toml` structure static-check changes:

- Keep `name` at top level **or** under `[metadata]` (both still resolve).
- Put author / explanation / taxonomy / scoring fields under **`[metadata]`** — top-level copies no longer count.
- Put resource + network fields under **`[environment]`**, including **`network_mode`**.
- Do **not** put `network_mode` at the top level (Harbor ignores it; the check fails).

## Valid example

```toml
# Top-level artifacts (required by separate-verifier checks, not the fields check)
artifacts = ["/app/output/result.json"]

name = "widget-fixer"

[metadata]
author_name = "Ada Lovelace"
author_email = "ada@example.com"
difficulty_explanation = "Requires careful debugging of a multi-module service."
solution_explanation = "Repair the broken implementation and restore expected behavior."
verification_explanation = "Pytest covers the required outputs and edge cases."
relevant_experience = "Production software engineering."
category = "Software"
subcategory = "Systems"
tags = ["debugging", "python"]
expert_time_estimate_hours = 2.0
difficulty = "base"
languages = ["python"]

[environment]
build_timeout_sec = 900
cpus = 2
memory_mb = 4096
storage_mb = 5120
network_mode = "public"   # or "no-network"

[agent]
timeout_sec = 7200

[verifier]
timeout_sec = 3600
environment_mode = "separate"
```

## What fails now (do not do this)

```toml
# BAD: descriptive fields at top level (must be under [metadata])
author_name = "Ada"
category = "Software"
subcategory = "Systems"

# BAD: Harbor ignores top-level network_mode; must be under [environment]
network_mode = "public"

[environment]
cpus = 2
```
