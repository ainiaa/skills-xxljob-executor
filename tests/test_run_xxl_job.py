import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_xxl_job.py"
SPEC = spec_from_file_location("run_xxl_job", SCRIPT)
RUNNER = module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class ExecutorHandler(BaseHTTPRequestHandler):
    responses = {}
    requests = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        self.__class__.requests.append({
            "path": self.path,
            "payload": json.loads(body),
            "headers": dict(self.headers.items()),
        })
        response = self.__class__.responses[self.path]
        if isinstance(response, list):
            response = response.pop(0)
        status_code = 200
        headers = {"Content-Type": "application/json"}
        if isinstance(response, tuple):
            status_code, headers, response = response
        self.send_response(status_code)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        pass


class RedirectTargetHandler(BaseHTTPRequestHandler):
    requests = []

    def record_request(self):
        self.__class__.requests.append(dict(self.headers.items()))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"code":200}')

    def do_POST(self):
        self.record_request()

    def do_GET(self):
        self.record_request()

    def log_message(self, format, *args):
        pass


class RunXxlJobTest(unittest.TestCase):
    def setUp(self):
        ExecutorHandler.requests = []
        ExecutorHandler.responses = {
            "/beat": {"code": 200},
            "/run": {"code": 200},
            "/log": {"code": 200, "content": {"logContent": "ReturnT [code=200]"}},
        }
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ExecutorHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.executor_url = "http://127.0.0.1:{}".format(self.server.server_port)
        RedirectTargetHandler.requests = []
        self.redirect_target = ThreadingHTTPServer(("127.0.0.1", 0), RedirectTargetHandler)
        self.redirect_thread = threading.Thread(target=self.redirect_target.serve_forever)
        self.redirect_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.redirect_target.shutdown()
        self.redirect_thread.join()
        self.redirect_target.server_close()

    def run_script(self, extra_args=None, environment=None, handler="exampleHandler"):
        command = [
            sys.executable, str(SCRIPT),
            "--executor-url", self.executor_url,
            "--handler", handler,
            "--params", '{"accountNos":["acct_1"],"startTime":1,"endTime":2}',
            "--wait-seconds", "0",
        ]
        if extra_args:
            command.extend(extra_args)
        process_environment = os.environ.copy()
        if environment:
            for key, value in environment.items():
                if value is None:
                    process_environment.pop(key, None)
                else:
                    process_environment[key] = value
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=process_environment,
        )

    def test_triggers_handler_with_json_params_and_reads_execution_log(self):
        result = self.run_script()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("accepted", result.stdout)
        self.assertIn("ReturnT [code=200]", result.stdout)
        self.assertEqual(["/beat", "/run", "/log"], [request["path"] for request in ExecutorHandler.requests])
        run_payload = ExecutorHandler.requests[1]["payload"]
        self.assertEqual("exampleHandler", run_payload["executorHandler"])
        self.assertEqual({"accountNos": ["acct_1"], "startTime": 1, "endTime": 2},
                         json.loads(run_payload["executorParams"]))

    def test_uses_nonzero_stable_job_id_when_job_id_is_not_supplied(self):
        first_result = self.run_script()
        second_result = self.run_script()

        self.assertEqual(0, first_result.returncode, first_result.stderr)
        self.assertEqual(0, second_result.returncode, second_result.stderr)
        job_ids = [ExecutorHandler.requests[index]["payload"]["jobId"] for index in (1, 4)]
        self.assertGreater(job_ids[0], 0)
        self.assertEqual(job_ids[0], job_ids[1])

    def test_uses_explicit_job_id_when_supplied(self):
        result = self.run_script(extra_args=["--job-id", "9001"])

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(9001, ExecutorHandler.requests[1]["payload"]["jobId"])

    def test_trims_handler_before_sending_to_executor(self):
        result = self.run_script(handler="  exampleHandler  ")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("exampleHandler", ExecutorHandler.requests[1]["payload"]["executorHandler"])

    def test_creates_distinct_log_ids_when_clock_millisecond_is_the_same(self):
        with patch.object(RUNNER.time, "time", return_value=1789372800.123), \
                patch.object(RUNNER.secrets, "randbits", side_effect=[101, 102]):
            first_log_id, first_log_date_time = RUNNER.create_log_context()
            second_log_id, second_log_date_time = RUNNER.create_log_context()

        self.assertEqual((101, 1789372800123), (first_log_id, first_log_date_time))
        self.assertEqual((102, 1789372800123), (second_log_id, second_log_date_time))

    def test_reads_available_log_once_when_xxl_job_reports_is_end_false(self):
        ExecutorHandler.responses["/log"] = {
            "code": 200,
            "content": {"logContent": "first line\nsecond line", "toLineNum": 3, "isEnd": False},
        }

        result = self.run_script()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("first line\nsecond line", result.stdout)
        self.assertEqual(["/beat", "/run", "/log"],
                         [request["path"] for request in ExecutorHandler.requests])

    def test_stops_without_triggering_when_executor_is_not_healthy(self):
        ExecutorHandler.responses["/beat"] = {"code": 500, "msg": "offline"}

        result = self.run_script()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("beat failed", result.stderr)
        self.assertEqual(["/beat"], [request["path"] for request in ExecutorHandler.requests])

    def test_sends_access_token_from_named_environment_variable_to_all_executor_calls(self):
        result = self.run_script(
            extra_args=["--access-token-env", "XXL_JOB_ACCESS_TOKEN", "--allow-insecure-http-token"],
            environment={"XXL_JOB_ACCESS_TOKEN": "test-access-token"},
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            ["test-access-token", "test-access-token", "test-access-token"],
            [request["headers"].get("Xxl-Job-Access-Token") for request in ExecutorHandler.requests],
        )

    def test_rejects_http_when_an_access_token_is_requested_without_explicit_override(self):
        result = self.run_script(
            extra_args=["--access-token-env", "XXL_JOB_ACCESS_TOKEN"],
            environment={"XXL_JOB_ACCESS_TOKEN": "test-access-token"},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("requires HTTPS", result.stderr)
        self.assertEqual([], ExecutorHandler.requests)

    def test_does_not_echo_access_token_in_executor_error(self):
        ExecutorHandler.responses["/run"] = {"code": 500, "msg": "test-access-token"}

        result = self.run_script(
            extra_args=["--access-token-env", "XXL_JOB_ACCESS_TOKEN", "--allow-insecure-http-token"],
            environment={"XXL_JOB_ACCESS_TOKEN": "test-access-token"},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("test-access-token", result.stdout + result.stderr)
        self.assertEqual(["/beat", "/run"], [request["path"] for request in ExecutorHandler.requests])

    def test_does_not_follow_redirect_for_an_access_token_request(self):
        ExecutorHandler.responses["/beat"] = (
            302,
            {"Location": "http://127.0.0.1:{}/redirected".format(self.redirect_target.server_port)},
            {},
        )

        result = self.run_script(
            extra_args=["--access-token-env", "XXL_JOB_ACCESS_TOKEN", "--allow-insecure-http-token"],
            environment={"XXL_JOB_ACCESS_TOKEN": "test-access-token"},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], RedirectTargetHandler.requests)
        self.assertEqual(["/beat"], [request["path"] for request in ExecutorHandler.requests])

    def test_stops_before_network_when_named_access_token_environment_variable_is_missing(self):
        result = self.run_script(
            extra_args=["--access-token-env", "XXL_JOB_ACCESS_TOKEN_MISSING_FOR_TEST"],
            environment={"XXL_JOB_ACCESS_TOKEN_MISSING_FOR_TEST": None},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("access token environment variable is blank", result.stderr)
        self.assertEqual([], ExecutorHandler.requests)


if __name__ == "__main__":
    unittest.main()
