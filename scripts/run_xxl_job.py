#!/usr/bin/env python3
"""Trigger one XXL-Job handler through its executor HTTP endpoint."""

import argparse
import html
import json
import os
import secrets
import sys
import time
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


SUCCESS_CODE = 200


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executor-url", required=True, help="Executor base URL, for example http://10.93.1.143:9999")
    parser.add_argument("--handler", required=True, help="XXL-Job executor handler name")
    parser.add_argument("--params", required=True, help="Handler JSON parameters")
    parser.add_argument("--job-id", type=int, help="Optional XXL-Job ID; defaults to a stable ID derived from the handler")
    parser.add_argument("--access-token-env", help="Optional environment variable that contains XXL-JOB-ACCESS-TOKEN")
    parser.add_argument("--allow-insecure-http-token", action="store_true",
                        help="Allow sending an access token to an HTTP executor")
    parser.add_argument("--wait-seconds", type=float, default=1, help="Seconds to wait before reading the execution log (0-60)")
    parser.add_argument("--timeout-seconds", type=float, default=15, help="HTTP request timeout in seconds")
    return parser.parse_args()


def request_json(url, payload, timeout_seconds, access_token):
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["XXL-JOB-ACCESS-TOKEN"] = access_token
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with build_opener(NoRedirectHandler()).open(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = redact(error.read().decode("utf-8", errors="replace"), access_token)
        raise RuntimeError("HTTP {} calling {}: {}".format(error.code, url, detail))
    except URLError as error:
        raise RuntimeError("connection failed calling {}: {}".format(url, error.reason))


def redact(value, access_token):
    if access_token:
        return value.replace(access_token, "[REDACTED]")
    return value


def require_success(response, action, access_token):
    if not isinstance(response, dict) or response.get("code") != SUCCESS_CODE:
        detail = redact(json.dumps(response, ensure_ascii=False), access_token)
        raise RuntimeError("{} failed: {}".format(action, detail))


def executor_base(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("executor URL must be an http(s) base URL without query or fragment")
    return url.rstrip("/")


def read_access_token(environment_variable):
    if not environment_variable:
        return None
    access_token = os.environ.get(environment_variable)
    if not access_token:
        raise ValueError("access token environment variable is blank: {}".format(environment_variable))
    return access_token


def readable_log(log_content):
    return html.unescape(log_content).replace("<br>", "\n")


def default_job_id(handler):
    return (zlib.crc32(handler.encode("utf-8")) & 0x7fffffff) or 1


def create_log_context():
    return secrets.randbits(63) or 1, int(time.time() * 1000)


def read_log(base_url, log_id, timeout_seconds, access_token):
    log_response = request_json(
        base_url + "/log",
        {"logDateTim": log_id, "logId": log_id, "fromLineNum": 1},
        timeout_seconds,
        access_token,
    )
    require_success(log_response, "log", access_token)
    return (log_response.get("content") or {}).get("logContent", "")


def main():
    args = parse_args()
    handler = args.handler.strip()
    if not handler:
        raise ValueError("handler must not be blank")
    if not 0 <= args.wait_seconds <= 60:
        raise ValueError("wait-seconds must be between 0 and 60")
    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be positive")
    if args.job_id is not None and args.job_id <= 0:
        raise ValueError("job-id must be positive")

    params = json.loads(args.params)
    if not isinstance(params, dict):
        raise ValueError("params must be a JSON object")
    base_url = executor_base(args.executor_url)
    access_token = read_access_token(args.access_token_env)
    if access_token and urlsplit(base_url).scheme != "https" and not args.allow_insecure_http_token:
        raise ValueError("access token requires HTTPS; use --allow-insecure-http-token only for a trusted internal executor")

    require_success(request_json(base_url + "/beat", {}, args.timeout_seconds, access_token), "beat", access_token)
    log_id, log_date_time = create_log_context()
    trigger = {
        "jobId": args.job_id or default_job_id(handler),
        "executorHandler": handler,
        "executorParams": json.dumps(params, ensure_ascii=False, separators=(",", ":")),
        "executorBlockStrategy": "SERIAL_EXECUTION",
        "executorTimeout": 0,
        "logId": log_id,
        "logDateTime": log_date_time,
        "glueType": "BEAN",
        "glueSource": "",
        "glueUpdatetime": log_date_time,
        "broadcastIndex": 0,
        "broadcastTotal": 1,
    }
    require_success(request_json(base_url + "/run", trigger, args.timeout_seconds, access_token), "run", access_token)
    print("accepted: handler={}, logId={}".format(handler, log_id))

    if args.wait_seconds:
        time.sleep(args.wait_seconds)
    log_content = read_log(base_url, log_id, args.timeout_seconds, access_token)
    print("execution_log:\n{}".format(readable_log(log_content)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
