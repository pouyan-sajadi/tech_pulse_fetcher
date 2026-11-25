import asyncio
import json
import unittest

import httpx
from unittest.mock import AsyncMock, patch

from src import product_hunt as ph
from src.tech_pulse_fetcher import TechPulseFetcher


DAY = "2026-11-25"


def row(slug="one", topics=None):
    return {
        "name": "Product profile",
        "categories": [{"name": "Developer Tools"}] if topics is None else topics,
        "launches": [{"name": "Launch", "tagline": "A useful tool", "points": 14,
                      "url": f"https://www.producthunt.com/posts/{slug}?ref=mcp"}],
    }


def board(*rows):
    return {"status": "ok", "data": {"period": {"date": DAY}, "results": list(rows)}}


class LeaderboardTest(unittest.TestCase):
    def test_ranked_launches_keep_order_and_real_categories(self):
        rows = [None, row("two"), row("empty", []), row("two"), row("one")]
        result = ph.leaderboard_products(board(*rows), DAY, 10)
        self.assertEqual([ph.launch_slug(p["url"]) for p in result], ["two", "one"])
        self.assertEqual(result[0]["title"], "Launch")
        self.assertEqual(result[0]["description"], "A useful tool")
        self.assertEqual(result[0]["topics"], ["Developer Tools"])
        self.assertEqual(result[0]["points"], 14)
        self.assertNotIn("votes", result[0])

    def test_invalid_day_and_outer_errors(self):
        for payload, reason in [(board(), "wrong_period"), ({"status": "error"}, "tool_error"),
                                ({"status": "ok", "data": {}}, "invalid_response")]:
            with self.subTest(reason=reason), self.assertRaisesRegex(ph.SourceError, reason):
                ph.leaderboard_products(payload, "2026-11-24", 10)

    def test_unusable_products_are_excluded(self):
        invalid = row()
        invalid["launches"][0]["url"] = "https://example.org/posts/one"
        self.assertEqual(ph.leaderboard_products(board(invalid, row("two", [])), DAY, 10), [])


class GraphQLTest(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_query_and_normalization(self):
        def respond(request):
            self.assertEqual(request.headers["Authorization"], "Bearer test")
            body = json.loads(request.content)
            self.assertEqual(body["variables"], {"first": 10})
            self.assertIn("posts(order: VOTES", body["query"])
            return httpx.Response(200, json={"data": {"posts": {"edges": [None, {"node": {
                "name": "Example", "url": "https://www.producthunt.com/products/app/launches/v2",
                "description": "Full description", "votesCount": 17, "commentsCount": 2,
                "topics": {"edges": [{"node": {"name": "Design"}}]},
            }}]}}})

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch.object(ph.httpx, "AsyncClient", return_value=client):
            outcome = await ph.attempt(ph.fetch_graphql, "test", "https://api.producthunt.com/v2/api/graphql", 10)
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(len(outcome.items), 1)
        product = outcome.items[0]
        self.assertEqual((product["votes"], product["topics"], product["description"]),
                         (17, ["Design"], "Full description"))

    async def test_graphql_errors_do_not_log_provider_messages(self):
        response = httpx.Response(200, json={"errors": [{"message": "private service detail"}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response))
        with patch.object(ph.httpx, "AsyncClient", return_value=client):
            outcome = await ph.attempt(ph.fetch_graphql, "dummy", "https://api.producthunt.com/v2/api/graphql", 10)
        self.assertEqual((outcome.status, outcome.items), ("graphql_error", []))


class SourceSelectionTest(unittest.TestCase):
    def fetch(self, mcp, graphql, rss):
        async def resolve(value):
            if isinstance(value, Exception):
                raise value
            return value

        both_started = set()
        async def source(name, outcome, *args):
            both_started.add(name)
            await asyncio.sleep(0)
            self.assertEqual(both_started, {"mcp", "graphql"})
            return await resolve(outcome)

        async def primary(*args):
            return await source("mcp", mcp, *args)

        async def comparison(*args):
            return await source("graphql", graphql, *args)

        with patch.object(ph, "fetch_leaderboard", primary), patch.object(ph, "fetch_graphql", comparison), \
             patch.object(ph, "read_feed", AsyncMock(return_value=rss)) as read_feed, self.assertLogs(level="INFO") as logs:
            result = TechPulseFetcher("dummy").fetch_product_hunt()
        event = json.loads(next(line.split("product_hunt_comparison ")[1] for line in logs.output
                                if "product_hunt_comparison " in line))
        return result, event, read_feed.await_count

    def test_mcp_is_only_selected_batch_and_same_launch_is_counted(self):
        a = [{"url": "https://www.producthunt.com/posts/one?ref=mcp"}]
        b = [{"url": "https://www.producthunt.com/products/parent/launches/one?ref=api"}]
        result, event, rss_calls = self.fetch(a, b, [])
        self.assertIs(result, a)
        self.assertEqual((event["selected"], event["shared_launches"], rss_calls), ("mcp", 1, 0))

    def test_single_mcp_row_survives_graphql_failure(self):
        mcp = [{"url": "https://www.producthunt.com/posts/one"}]
        result, event, rss_calls = self.fetch(mcp, ph.SourceError("missing_token"), [])
        self.assertIs(result, mcp)
        self.assertEqual(event["providers"]["graphql"]["status"], "missing_token")
        self.assertEqual(rss_calls, 0)

    def test_invalid_or_timed_out_mcp_uses_graphql(self):
        graphql = [{"url": "https://www.producthunt.com/posts/one"}]
        for failure, status in [(TimeoutError(), "timeout"), ([], "no_usable_products"),
                                (ph.SourceError("tool_error"), "tool_error")]:
            with self.subTest(status=status):
                result, event, rss_calls = self.fetch(failure, graphql, [])
                self.assertIs(result, graphql)
                self.assertEqual((event["selected"], event["providers"]["mcp"]["status"], rss_calls),
                                 ("graphql", status, 0))

    def test_rss_used_once_only_after_both_failed(self):
        for rss in [[{"source": "RSS"}], []]:
            with self.subTest(rss=rss):
                result, event, rss_calls = self.fetch([], [], rss)
                self.assertEqual(result, rss)
                self.assertEqual(event["selected"], "rss" if rss else None)
                self.assertEqual(rss_calls, 1)
