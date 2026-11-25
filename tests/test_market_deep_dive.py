import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from src.llm_client import InvalidLLMResponse, LLMClient
from src.market_deep_dive import BriefValidationError, generate_market_deep_dive, normalize_brief


ASSIGNMENT = {
    "story_id": 1,
    "search_query": "cloud platform terms",
    "research_question": "How could the new terms change competition?",
}
STORIES = [{
    "topic": "A cloud platform changes its terms",
    "summary": "The new terms change what customers pay.",
    "sources": [{"url": "https://example.com/story", "title": "Coverage", "source": "Example"}],
}]
RESEARCH = [{"source": "hackernews", "url": "https://example.org/research", "title": "Discussion"}]
EVIDENCE = [{"id": "s1", "kind": "original"}, {"id": "s2", "kind": "research"}]


def valid_draft():
    def point(label, source):
        return {"label": label, "text": "A short observation.", "source_ids": [source]}

    return {
        "headline": "New terms change cloud costs",
        "summary": "The platform changed its terms and customers may pay more. [s1]",
        "summary_source_ids": ["s1"],
        "signals": [point("New terms", "s1"), point("Customer reaction", "s2")],
        "impact": [point("Cloud customers", "s1")],
        "outlook": [
            {**point("Contract renewals", "s1"), "horizon": "near"},
            {**point("Business costs", "s1"), "horizon": "long"},
            {**point("Customer alternatives", "s2"), "horizon": "counter"},
        ],
    }


class DraftValidationTests(unittest.TestCase):
    def test_reports_multiple_exact_failures(self):
        draft = valid_draft()
        draft["summary"] = "x" * 301
        draft["summary_source_ids"] = ["s2"]
        draft["signals"][1]["source_ids"] = ["unknown"]
        draft["outlook"][2]["horizon"] = "other"
        with self.assertRaises(BriefValidationError) as error:
            normalize_brief(draft, EVIDENCE)
        for reason in (
            "summary exceeds 300 characters (301)",
            "summary_source_ids must cite original coverage",
            "signals[1].source_ids must include a supplied source ID",
            "outlook missing usable horizons counter",
            "outlook[2].horizon must be near, long, or counter",
        ):
            self.assertIn(reason, str(error.exception))

    def test_rejects_brief_without_research_citation(self):
        draft = valid_draft()
        draft["signals"][1]["source_ids"] = ["s1"]
        draft["outlook"][2]["source_ids"] = ["s1"]
        with self.assertRaisesRegex(BriefValidationError, "cite at least one research source"):
            normalize_brief(draft, EVIDENCE)


class DraftRepairTests(unittest.TestCase):
    def setUp(self):
        self.chat = self.enterContext(patch("src.market_deep_dive.llm_client.chat_json"))
        self.research = self.enterContext(patch("src.market_deep_dive.research_story", return_value=RESEARCH))

    def generate(self):
        return generate_market_deep_dive(STORIES, [], Path(__file__), [])

    def test_valid_first_draft_needs_no_repair(self):
        self.chat.side_effect = [ASSIGNMENT, valid_draft()]
        brief = self.generate()
        self.assertEqual(self.chat.call_count, 2)
        self.assertNotIn("[s1]", brief["summary"])
        self.assertEqual([source["id"] for source in brief["sources"]], ["s1", "s2"])
        self.assertEqual([point["horizon"] for point in brief["outlook"]], ["near", "long", "counter"])

    def test_repairs_failed_checks_with_same_evidence(self):
        draft = valid_draft()
        draft["summary_source_ids"] = []
        draft["outlook"].pop()
        self.chat.side_effect = [ASSIGNMENT, draft, valid_draft()]
        with self.assertLogs(level="INFO") as logs:
            self.assertIsNotNone(self.generate())
        self.research.assert_called_once()
        self.assertEqual(self.chat.call_count, 3)
        first = json.loads(self.chat.call_args_list[1].args[1])
        repair = json.loads(self.chat.call_args_list[2].args[1])
        self.assertEqual(repair["evidence"], first["evidence"])
        self.assertEqual(repair["previous_draft"], draft)
        for reason in ("summary_source_ids must include", "outlook missing usable horizons counter"):
            self.assertIn(reason, repair["validation_failures"])
            self.assertIn(reason, "\n".join(logs.output))
        self.assertIn("included in snapshot (draft 2/2)", "\n".join(logs.output))

    def test_invalid_json_gets_one_repair(self):
        client = LLMClient()
        with patch.object(client, "_get_client") as get_client:
            model = get_client.return_value.with_options.return_value
            response = model.chat.completions.create.return_value
            response.choices = [Mock()]
            response.choices[0].message.content = "{"
            with self.assertRaisesRegex(InvalidLLMResponse, "not valid JSON") as error:
                client.chat_json("", "", timeout=40)
        self.chat.side_effect = [ASSIGNMENT, error.exception, valid_draft()]
        with self.assertLogs(level="WARNING") as logs:
            self.assertIsNotNone(self.generate())
        repair = json.loads(self.chat.call_args.args[1])
        self.assertIn("not valid JSON", repair["validation_failures"])
        self.assertNotIn("previous_draft", repair)
        self.assertIn("not valid JSON", "\n".join(logs.output))
        self.assertEqual(self.chat.call_count, 3)

    def test_second_failure_keeps_regular_brief(self):
        draft = valid_draft()
        draft["summary"] = "x" * 301
        self.chat.side_effect = [ASSIGNMENT, {"skip": True}, draft]
        with self.assertLogs(level="WARNING") as logs:
            self.assertIsNone(self.generate())
        self.assertEqual(self.chat.call_count, 3)
        self.assertIn("draft 1/2 failed (draft returned skip=true)", logs.output[0])
        self.assertIn("draft 2/2 failed (summary exceeds 300 characters (301))", logs.output[1])
        self.assertIn("Publishing the regular brief", logs.output[1])

    def test_missing_research_skips_drafting(self):
        self.chat.side_effect = [ASSIGNMENT]
        self.research.return_value = []
        with self.assertLogs(level="INFO") as logs:
            self.assertIsNone(self.generate())
        self.chat.assert_called_once()
        self.assertIn("missing evidence of type research", logs.output[0])
