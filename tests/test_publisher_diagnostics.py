import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import mock_open, patch

import main as publisher


class PublisherDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.summary = Path(self.enterContext(TemporaryDirectory())) / "summary.md"
        self.enterContext(patch.dict(os.environ, {
            "GITHUB_RUN_ID": "321",
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "LAST30DAYS_CHECKOUT_OUTCOME": "failure",
        }, clear=True))
        fetcher = self.enterContext(patch.object(publisher, "TechPulseFetcher"))
        fetcher.return_value.fetch_all.return_value = {"rss_articles": [{}]}
        processor = self.enterContext(patch.object(publisher, "DataProcessor"))
        processor.return_value.process_rss_feeds_for_wordcloud.return_value = {"hot_topics": [{"topic": "Example"}]}
        self.enterContext(patch.object(publisher.os, "makedirs"))
        self.enterContext(patch.object(publisher, "open", mock_open(), create=True))

    def test_unavailable_research_publishes_regular_snapshot_and_explains_omission(self):
        with patch.object(publisher, "save_data_to_supabase", return_value="2026-11-25T14:31:00Z") as save, self.assertLogs(level="INFO") as logs:
            publisher.main()

        save.assert_called_once_with({"news_word_cloud": {"hot_topics": [{"topic": "Example"}]}})
        self.assertIn('| deep_dive | fallback | research_script_unconfigured |', self.summary.read_text())
        self.assertIn('| publish | published |', self.summary.read_text())
        combined = "\n".join(logs.output)
        self.assertIn('"run_id": "321"', combined)
        self.assertIn('"research_checkout": "failure"', combined)
        self.assertIn('"has_market_deep_dive": false', combined)
        self.assertIn('"snapshot_created_at": "2026-11-25T14:31:00Z"', combined)

    def test_ranked_launch_metadata_reaches_snapshot_without_chart_output(self):
        launches = [{
            "title": "Example", "url": "https://www.producthunt.com/posts/example",
            "daily_rank": 1, "points": 42, "topics": ["AI Agents"], "leaderboard_date": "2026-11-25",
        }]
        publisher.TechPulseFetcher.return_value.fetch_all.return_value = {"product_hunt": launches}
        chart = publisher.DataProcessor.return_value.process_product_hunt_for_sankey
        chart.return_value = {}

        with patch.object(publisher, "save_data_to_supabase", return_value="2026-11-25T14:31:00Z") as save:
            publisher.main()

        chart.assert_called_once_with(launches)
        save.assert_called_once_with({
            "product_hunt_tag_connections": {},
            "product_hunt_leaderboard": {"date": "2026-11-25", "launches": [{
                "title": "Example", "url": "https://www.producthunt.com/posts/example",
                "rank": 1, "points": 42, "tags": ["AI Agents"],
            }]},
        })

    def test_missing_publish_configuration_fails_workflow_and_writes_summary(self):
        with (
            patch.object(publisher, "SUPABASE_URL", None),
            patch.object(publisher, "SUPABASE_KEY", None),
            patch.object(publisher, "create_client") as create_client,
            self.assertLogs(level="WARNING"),
            self.assertRaises(SystemExit) as exit_error,
        ):
            publisher.main()

        self.assertEqual(exit_error.exception.code, 1)
        create_client.assert_not_called()
        self.assertIn('| publish | failed | MissingPublishConfiguration |', self.summary.read_text())

    def test_missing_inserted_snapshot_fails_workflow(self):
        with (
            patch.object(publisher, "SUPABASE_URL", "https://example.invalid"),
            patch.object(publisher, "SUPABASE_KEY", "offline-test"),
            patch.object(publisher, "create_client") as create_client,
            self.assertLogs(level="WARNING"),
            self.assertRaises(SystemExit),
        ):
            insert = create_client.return_value.table.return_value.insert
            insert.return_value.execute.return_value.data = []
            publisher.main()

        insert.return_value.execute.assert_called_once_with()
        self.assertIn('| publish | failed | UnconfirmedSnapshotInsert |', self.summary.read_text())
