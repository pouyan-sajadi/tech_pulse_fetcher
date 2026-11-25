"""Collect one ranked Product Hunt feed for the dashboard and compare the providers."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import feedparser
import httpx
from bs4 import BeautifulSoup
from mcp import Client

MCP_URL = "https://mcp.producthunt.com/mcp"
SOURCE_TIMEOUT = 15
POSTS_QUERY = """
query todaysPosts($first: Int!) {
  posts(order: VOTES, first: $first) {
    edges { node {
      name tagline description votesCount commentsCount url website
      topics { edges { node { name } } }
    } }
  }
}
"""

# The SDK logs the negotiated session ID at INFO. Only log source outcomes here.
logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)


class SourceError(Exception):
    """A fixed diagnostic code safe to include in the workflow log."""


@dataclass
class Outcome:
    items: list[dict]
    status: str
    elapsed_ms: int


def product_hunt_path(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in {"producthunt.com", "www.producthunt.com"}:
            return None
    except ValueError:
        return None
    return parsed.path


def launch_slug(url):
    # GraphQL links to /products/<product>/launches/<launch>, MCP to /posts/<launch>.
    match = re.fullmatch(r"/(?:posts|products/[^/]+/launches)/([a-z0-9_-]+)/?", product_hunt_path(url) or "", re.I)
    return match[1].lower() if match else None


def named_topics(nodes):
    if not isinstance(nodes, list):
        return []
    return list(dict.fromkeys(node["name"].strip() for node in nodes
                              if isinstance(node, dict) and isinstance(node.get("name"), str)
                              and node["name"].strip()))


def text_field(value):
    return value.strip() if isinstance(value, str) else ""


def leaderboard_products(payload, day, limit):
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise SourceError("tool_error")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise SourceError("invalid_response")
    if not isinstance(data.get("period"), dict) or data["period"].get("date") != day:
        raise SourceError("wrong_period")

    products = []
    seen = set()
    for row in data["results"]:
        if not isinstance(row, dict):
            continue
        topics = named_topics(row.get("categories"))
        launches = row.get("launches")
        if not topics or not isinstance(launches, list) or not launches:
            continue
        launch = launches[0]
        if not isinstance(launch, dict):
            continue
        slug = launch_slug(launch.get("url"))
        title = text_field(launch.get("name"))
        tagline = text_field(launch.get("tagline")) or text_field(row.get("tagline"))
        if not slug or slug in seen or not title or not tagline:
            continue
        products.append({
            "source": "Product Hunt (MCP)", "title": title, "url": launch["url"],
            "tagline": tagline, "description": tagline, "website": text_field(row.get("website_url")),
            "topics": topics, "points": launch.get("points"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
        seen.add(slug)
        if len(products) == limit:
            break
    return products


async def fetch_leaderboard(day, limit):
    async with Client(MCP_URL) as client:
        result = await client.call_tool("get_product_leaderboard", {"date": day, "limit": min(limit, 25)})
    if result.is_error:
        raise SourceError("tool_error")
    return leaderboard_products(result.structured_content, day, limit)


async def fetch_graphql(token, url, limit):
    if not token:
        raise SourceError("missing_token")
    async with httpx.AsyncClient(timeout=SOURCE_TIMEOUT) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {token}"},
                                     json={"query": POSTS_QUERY, "variables": {"first": limit}})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("errors"):
        raise SourceError("graphql_error")
    edges = payload["data"]["posts"]["edges"]
    if not isinstance(edges, list):
        raise SourceError("invalid_response")
    products = []
    for edge in edges:
        node = edge.get("node") if isinstance(edge, dict) else None
        if not isinstance(node, dict):
            continue
        title, url = text_field(node.get("name")), text_field(node.get("url"))
        if not title or not product_hunt_path(url):
            continue
        topics = node.get("topics")
        topic_edges = topics.get("edges") if isinstance(topics, dict) else None
        topic_nodes = [t.get("node") for t in topic_edges if isinstance(t, dict)] if isinstance(topic_edges, list) else []
        tagline = text_field(node.get("tagline"))
        products.append({
            "source": "Product Hunt", "title": title, "url": url,
            "tagline": tagline, "description": text_field(node.get("description")) or tagline,
            "website": text_field(node.get("website")), "votes": node.get("votesCount"),
            "comments": node.get("commentsCount"), "topics": named_topics(topic_nodes),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return products[:limit]


async def read_feed(limit):
    async with httpx.AsyncClient(timeout=SOURCE_TIMEOUT, follow_redirects=True) as client:
        response = await client.get("https://www.producthunt.com/feed")
    response.raise_for_status()
    products = []
    for entry in feedparser.parse(response.content).entries[:limit]:
        title, url = text_field(entry.get("title")), text_field(entry.get("link"))
        if title and product_hunt_path(url):
            products.append({
                "source": "Product Hunt (RSS)", "title": title, "url": url,
                "description": BeautifulSoup(entry.get("description", ""), "html.parser").get_text().strip(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
    return products


async def attempt(fetch, *args):
    start = monotonic()
    items = []
    try:
        async with asyncio.timeout(SOURCE_TIMEOUT):
            items = await fetch(*args)
        status = "ok" if items else "no_usable_products"
    except SourceError as error:
        status = str(error)
    except (TimeoutError, httpx.TimeoutException):
        status = "timeout"
    except httpx.HTTPStatusError as error:
        status = f"http_{error.response.status_code}"
    except Exception as error:
        status = type(error).__name__
    return Outcome(items, status, round((monotonic() - start) * 1000))


async def fetch_rss(limit):
    return (await attempt(read_feed, limit)).items


async def collect_product_hunt(token, graphql_url, limit):
    if limit <= 0:
        return []
    day = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    mcp, graphql = await asyncio.gather(
        attempt(fetch_leaderboard, day, limit), attempt(fetch_graphql, token, graphql_url, limit),
    )
    providers = {"mcp": mcp, "graphql": graphql}
    if not (mcp.items or graphql.items):
        providers["rss"] = await attempt(read_feed, limit)

    selected = next((name for name, result in providers.items() if result.items), None)
    log = {
        "pacific_day": day, "selected": selected,
        "providers": {name: {"status": r.status, "count": len(r.items), "elapsed_ms": r.elapsed_ms}
                      for name, r in providers.items()},
    }
    if mcp.items and graphql.items:
        a = [slug for item in mcp.items if (slug := launch_slug(item["url"]))]
        b = [slug for item in graphql.items if (slug := launch_slug(item["url"]))]
        log.update(shared_launches=len(set(a) & set(b)), mcp_launches=a, graphql_launches=b)
    logging.info("product_hunt_comparison %s", json.dumps(log, sort_keys=True))
    return providers[selected].items if selected else []
