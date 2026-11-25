import logging
import json
import os
from datetime import datetime, timedelta, timezone
from src.tech_pulse_fetcher import TechPulseFetcher
from src.data_processor import DataProcessor
from src.market_deep_dive import generate_market_deep_dive
from src.market_diagnostics import MarketDiagnostics
from src.product_hunt import top_daily_launches
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def recent_market_briefs():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    today = datetime.now(timezone.utc).date()
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = (
        supabase.table("tech_pulses")
        .select("created_at,pulse_data")
        .gte("created_at", f"{today - timedelta(days=7)}T00:00:00Z")
        .lt("created_at", f"{today}T00:00:00Z")
        .order("created_at", desc=True)
        .limit(25)
        .execute()
    )

    by_day = {}
    for row in response.data:
        day = row["created_at"][:10]
        if day in by_day:
            continue
        pulse = row.get("pulse_data")
        if isinstance(pulse, str):
            try:
                pulse = json.loads(pulse)
            except json.JSONDecodeError:
                continue
        if not isinstance(pulse, dict):
            continue
        news = pulse.get("news_word_cloud") or {}
        topics = news.get("hot_topics", []) if isinstance(news, dict) else []
        headlines = [
            item["topic"][:160] for item in topics
            if isinstance(item, dict) and isinstance(item.get("topic"), str)
        ][:5] if isinstance(topics, list) else []
        lead = pulse.get("market_deep_dive")
        if isinstance(lead, dict) and isinstance(lead.get("headline"), str):
            headlines.insert(0, lead["headline"][:160])
        if headlines:
            by_day[day] = headlines
    return [{"date": day, "headlines": headlines} for day, headlines in by_day.items()]


class MissingPublishConfiguration(RuntimeError):
    """Publishing requires Supabase credentials."""


class UnconfirmedSnapshotInsert(RuntimeError):
    """Supabase did not return the inserted snapshot."""


def save_data_to_supabase(data: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise MissingPublishConfiguration("Set SUPABASE_URL and SUPABASE_KEY to publish the snapshot.")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.table("tech_pulses").insert({"pulse_data": json.dumps(data)}).execute()
    if not response.data:
        raise UnconfirmedSnapshotInsert("Supabase returned no inserted snapshot.")
    return response.data[0].get("created_at")


def run_pulse(diagnostics):
    with diagnostics.stage("collect") as event:
        fetched_data = TechPulseFetcher().fetch_all()
        event.update(rss_articles=len(fetched_data.get("rss_articles") or []))

    with diagnostics.stage("prepare"):
        processor = DataProcessor()
        processed_data = {}
        if fetched_data.get('github_trending'):
            processed_data['github_language_distribution'] = processor.process_github_trending(fetched_data['github_trending'])
        if fetched_data.get('rss_articles'):
            processed_data['news_word_cloud'] = processor.process_rss_feeds_for_wordcloud(fetched_data['rss_articles'])
        if fetched_data.get('product_hunt'):
            launches = fetched_data['product_hunt']
            if leaderboard := top_daily_launches(launches):
                processed_data['product_hunt_leaderboard'] = leaderboard
            processed_data['product_hunt_tag_connections'] = processor.process_product_hunt_for_sankey(launches)
        if fetched_data.get('predictions'):
            processed_data['manifold_predictions_bubble_plot'] = processor.process_manifold_predictions_for_bubble_plot(fetched_data['predictions'])

    stories = processed_data.get("news_word_cloud", {}).get("hot_topics", [])
    research_script = os.getenv("LAST30DAYS_SCRIPT")
    checkout = os.getenv("LAST30DAYS_CHECKOUT_OUTCOME") or "unknown"
    diagnostics.record("preflight", "ok", hot_topics=len(stories), research_checkout=checkout)
    if not stories:
        diagnostics.record("deep_dive", "skipped", reason="no_hot_topics")
    elif not research_script:
        diagnostics.record("deep_dive", "fallback", reason="research_script_unconfigured")
    else:
        with diagnostics.stage("history") as event:
            try:
                briefs = recent_market_briefs()
            except Exception as error:
                briefs = []
                event.update(outcome="fallback", reason="history_unavailable", error_type=type(error).__name__)
            event.update(prior_days=len(briefs))
        try:
            deep_dive = generate_market_deep_dive(
                stories, briefs, research_script, fetched_data["rss_articles"], diagnostics=diagnostics,
            )
        except Exception as error:
            diagnostics.record("deep_dive", "fallback", reason="generation_failed", error_type=type(error).__name__)
        else:
            if deep_dive:
                processed_data["market_deep_dive"] = deep_dive
            diagnostics.record("deep_dive", "generated" if deep_dive else "omitted")

    if processed_data:
        with diagnostics.stage("local_snapshot"):
            os.makedirs("processed_data", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"processed_data/tech_pulse_processed_{timestamp}.json"
            with open(file_path, "w", encoding="utf-8") as output:
                json.dump(processed_data, output, indent=4)

    with diagnostics.stage("publish", has_market_deep_dive="market_deep_dive" in processed_data) as event:
        if not processed_data:
            event.update(reason="no_snapshot_data")
            raise RuntimeError("No Tech Pulse snapshot data to publish.")
        created_at = save_data_to_supabase(processed_data)
        if isinstance(created_at, str):
            event.update(snapshot_created_at=created_at)
        event.update(outcome="published")


def main():
    diagnostics = MarketDiagnostics()
    diagnostics.record("workflow", "started", trigger=os.getenv("GITHUB_EVENT_NAME") or "local")
    try:
        with diagnostics.stage("workflow") as event:
            run_pulse(diagnostics)
            event.update(outcome="completed")
    except Exception:
        raise SystemExit(1) from None
    finally:
        diagnostics.write_summary()

if __name__ == "__main__":
    main()
