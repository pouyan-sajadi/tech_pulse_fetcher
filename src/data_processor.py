
import json
from collections import Counter

def process_github_trending():
    """
    Analyzes GitHub trending data to find the distribution of programming languages,
    including total stars and stars today.
    """
    try:
        with open('fetched_data/github_trending_data.json', 'r') as f:
            github_data = json.load(f)
    except FileNotFoundError:
        print("Error: github_trending_data.json not found.")
        return

    language_stats = {}

    for repo in github_data:
        lang = repo.get('language', 'Unknown')
        if lang == 'Unknown':
            continue

        if lang not in language_stats:
            language_stats[lang] = {
                'repo_count': 0,
                'total_stars': 0,
                'stars_today': 0
            }
        
        language_stats[lang]['repo_count'] += 1
        language_stats[lang]['total_stars'] += repo.get('stars', 0)
        language_stats[lang]['stars_today'] += repo.get('stars_today', 0)

    # Group less common languages into "Other"
    total_repos = len(github_data)
    other_stats = {'repo_count': 0, 'total_stars': 0, 'stars_today': 0}
    final_languages = {}

    for lang, stats in language_stats.items():
        if stats['repo_count'] / total_repos < 0.02:
            other_stats['repo_count'] += stats['repo_count']
            other_stats['total_stars'] += stats['total_stars']
            other_stats['stars_today'] += stats['stars_today']
        else:
            final_languages[lang] = stats

    if other_stats['repo_count'] > 0:
        final_languages['Other'] = other_stats

    # Prepare data for the pie chart
    chart_data = {
        "labels": list(final_languages.keys()),
        "datasets": [{
            "label": "GitHub Trending Languages",
            "data": [stats['repo_count'] for stats in final_languages.values()],
            "backgroundColor": ["#3572A5", "#F1E05A", "#00ADD8", "#DEA584", "#89E051", "#B07219", "#CCCCCC"],
            "hoverData": [
                {
                    'total_stars': stats['total_stars'],
                    'stars_today': stats['stars_today']
                }
                for stats in final_languages.values()
            ]
        }]
    }

    # Save the processed data
    with open('processed_data/github_language_distribution.json', 'w') as f:
        json.dump(chart_data, f, indent=2)

    print("Successfully processed GitHub trending data with star counts.")

import os
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

def process_rss_feeds_for_wordcloud():
    """
    Analyzes RSS feed data to generate a word cloud and identify hot topics using an LLM.
    """
    try:
        with open('fetched_data/rss_feeds_data.json', 'r') as f:
            rss_data = json.load(f)
    except FileNotFoundError:
        print("Error: rss_feeds_data.json not found.")
        return

    all_text = " ".join([f"{article.get('title', '')} {article.get('description', '')}" for article in rss_data])

    if not openai.api_key:
        print("Error: OPENAI_API_KEY environment variable not set. Cannot process RSS feeds with LLM.")
        return

    try:
        print("Sending RSS data to LLM for keyword and hot topic extraction...")
        response = openai.chat.completions.create(
            model="gpt-4o", # Using gpt-4o as a capable model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts keywords and identifies hot topics from tech news articles. Provide keywords with their importance score (1-10) and hot topics with a brief summary and a trend indicator (rising, stable, declining)."},
                {"role": "user", "content": f"Extract keywords and hot topics from the following text. Provide keywords as a JSON array of objects like {{'text': 'keyword', 'value': importance_score}}. Provide hot topics as a JSON array of objects like {{'topic': 'topic_name', 'summary': 'brief_summary', 'trend': 'rising|stable|declining'}}. Combine all keywords from the text. Text: {all_text}"}
            ],
            response_format={ "type": "json_object" }
        )
        
        llm_output = json.loads(response.choices[0].message.content)
        word_cloud_data = llm_output.get('keywords', [])
        hot_topics_data = llm_output.get('hot_topics', [])

        processed_data = {
            "word_cloud": word_cloud_data,
            "hot_topics": hot_topics_data
        }

        with open('processed_data/news_word_cloud.json', 'w') as f:
            json.dump(processed_data, f, indent=2)

        print("Successfully processed RSS feed data for word cloud and hot topics.")

    except Exception as e:
        print(f"Error processing RSS feeds with LLM: {e}")


if __name__ == '__main__':
    process_github_trending()
    process_rss_feeds_for_wordcloud()
