---
name: xxl-job-executor
description: Use when given an XXL-Job executor address, JobHandler name, and JSON parameters, and asked to trigger the handler directly or inspect its direct execution log. Not for editing schedules in an XXL-Job admin console.
---

# XXL-Job Executor

Trigger a registered BEAN handler through the executor's HTTP API. The required input is only the executor base URL, handler name, and a JSON object of handler parameters.

## Run once

An explicit user request to execute is required; composing a command or explaining parameters does not authorize a run.

```bash
python3 scripts/run_xxl_job.py \
  --executor-url "https://executor.example.com" \
  --handler "exampleHandler" \
  --params '{"key":"value"}'
```

The runner first calls `/beat`; if it is not successful it stops without calling `/run`. On success it triggers `/run` once using the standard direct-executor payload, then reads the current `/log` content for that generated log ID. It derives a stable positive job ID from the Handler unless the user gives a real `--job-id`. Do not automatically retry a run that fails or whose result is inconclusive.

For an executor protected by `XXL-JOB-ACCESS-TOKEN`, set the token through the user's secret-management flow, then pass only the environment-variable name:

```bash
python3 scripts/run_xxl_job.py \
  --executor-url "https://executor.example.com" \
  --handler "exampleHandler" \
  --params '{"key":"value"}' \
  --access-token-env "XXL_JOB_ACCESS_TOKEN"
```

Never put the token directly in the command line or log it. A missing or blank named variable stops before `/beat`.

The token path requires HTTPS by default. For a trusted internal HTTP executor, the user must explicitly request `--allow-insecure-http-token`; explain that the token will traverse the network unencrypted. Redirects are rejected so a token cannot be forwarded to another endpoint.

## Interpret the result

- `accepted` means the executor accepted the trigger, not that the business operation produced data.
- `/log` returns the current executor log, but `accepted` still means only that the executor accepted the trigger; use the service's application logs for record counts, downstream response bodies, and business-level diagnosis.
- If the executor requires an access token, ask for a permitted environment-variable name; if it does not expose the direct executor protocol, stop and report that limitation. Do not switch to the XXL admin console or invent credentials.

The parameters must be a JSON object. Keep timestamps and field names exactly as supplied; do not convert time zones or substitute defaults unless the user asks.
