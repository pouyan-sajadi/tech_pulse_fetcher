"""Run-scoped diagnostics shared by the market deep dive and its publisher."""

from contextlib import contextmanager
import json
import logging
import os
import re
from time import monotonic
from uuid import uuid4


class MarketDiagnostics:
    def __init__(self):
        self.run_id = os.getenv("GITHUB_RUN_ID") or uuid4().hex
        self.run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
        self.events = []

    def record(self, stage, outcome, **details):
        event = {"stage": stage, "outcome": outcome, **details}
        self.events.append(event)
        level = logging.WARNING if outcome in {"failed", "rejected", "fallback"} else logging.INFO
        logging.log(level, "market_deep_dive %s", json.dumps({
            "run_id": self.run_id, "run_attempt": self.run_attempt, **event,
        }))

    @contextmanager
    def stage(self, name, **details):
        started = monotonic()
        try:
            yield details
        except Exception as error:
            details.update(outcome="failed", error_type=type(error).__name__)
            for attribute, field in (("status_code", "http_status"), ("returncode", "exit_code")):
                value = getattr(error, attribute, None)
                if type(value) is int:
                    details[field] = value
            code = getattr(error, "code", None)
            if isinstance(code, str) and re.fullmatch(r"[0-9A-Z]{5}|PGRST[0-9]{3}", code):
                details["error_code"] = code
            raise
        finally:
            self.record(name, details.pop("outcome", "ok"), elapsed_ms=round((monotonic() - started) * 1000), **details)

    def write_summary(self):
        path = os.getenv("GITHUB_STEP_SUMMARY")
        if not path:
            return
        try:
            with open(path, "a", encoding="utf-8") as output:
                output.write("## Market Deep Dive\n\n")
                output.write("| Stage | Outcome | Reason | Time (ms) |\n| --- | --- | --- | ---: |\n")
                for event in self.events:
                    stage = event["stage"]
                    if "attempt" in event:
                        stage += f" {event['attempt']}"
                    reason = event.get("reason", event.get("error_type", ""))
                    elapsed = event.get("elapsed_ms", "")
                    output.write(f"| {stage} | {event['outcome']} | {reason} | {elapsed} |\n")
                output.write("\nSearch the job log for `market_deep_dive` for the full structured events.\n")
        except OSError as error:
            self.record("summary", "failed", error_type=type(error).__name__)
