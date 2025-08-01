
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
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

def process_rss_feeds_for_wordcloud():
    """
    Analyzes RSS feed data to generate a word cloud and identify hot topics.
    First, counts word frequencies, then uses LLM to extract important keywords.
    """
    try:
        with open('fetched_data/rss_feeds_data.json', 'r') as f:
            rss_data = json.load(f)
    except FileNotFoundError:
        print("Error: fetched_data/rss_feeds_data.json not found.")
        return

    all_text = " ".join([f"{article.get('title', '')} {article.get('description', '')}" for article in rss_data])

    # Basic text cleaning and tokenization
    cleaned_text = re.sub(r'[^a-zA-Z\s]', '', all_text).lower()
    words = cleaned_text.split()

    # Define a list of common English stop words (can be expanded)
    STOP_WORDS = set([
        "the", "and", "a", "an", "is", "it", "in", "of", "for", "on", "with",
        "to", "from", "by", "as", "at", "be", "this", "that", "have", "has",
        "he", "she", "it", "they", "we", "you", "i", "me", "him", "her", "us",
        "them", "my", "your", "his", "her", "its", "our", "their", "what",
        "where", "when", "why", "how", "which", "who", "whom", "whose", "am",
        "are", "was", "were", "been", "being", "do", "does", "did", "done",
        "doing", "can", "could", "would", "should", "will", "may", "might",
        "must", "had", "get", "go", "new", "just", "also", "like", "said",
        "says", "say", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "up", "down", "out", "in", "on", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "all", "any", "both", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "s", "t", "can", "will", "just",
        "don", "should", "now", "d", "ll", "m", "o", "re", "ve", "y", "ain",
        "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn", "ma",
        "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren", "won", "wouldn"
    ])

    # Filter out stop words and count frequencies
    filtered_words = [word for word in words if word not in STOP_WORDS and len(word) > 2] # Filter short words
    word_counts = Counter(filtered_words)

    # Get top N words for LLM input
    top_words = word_counts.most_common(50) # Adjust N as needed
    llm_input_words = ", ".join([f"'{word}' (count: {count})" for word, count in top_words])

    if not openai.api_key:
        print("Error: OPENAI_API_KEY environment variable not set. Cannot process RSS feeds with LLM.")
        return

    try:
        print("Sending top words to LLM for keyword importance and hot topic extraction...")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts important keywords and identifies hot topics from a list of words and their frequencies. Provide keywords as a JSON array of objects like {{'text': 'keyword', 'value': importance_score (1-100)}}. Provide hot topics as a JSON array of objects like {{'topic': 'topic_name', 'summary': 'brief_summary', 'trend': 'rising|stable|declining'}}. The importance score should be a number between 1 and 100, reflecting how significant the keyword is in the context of tech news. Focus on single words or very short phrases that represent key concepts. Do not include common words or stop words. Ensure the output is valid JSON."},
                {"role": "user", "content": f"From the following list of words and their counts, identify important keywords and hot topics. Words: {llm_input_words}"}
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


def process_product_hunt_for_sankey():
    """
    Analyzes Product Hunt data to create a Sankey diagram of product categories.
    Uses LLM to map product topics to predefined core categories.
    """
    try:
        with open('fetched_data/product_hunt_data.json', 'r') as f:
            product_hunt_data = json.load(f)
    except FileNotFoundError:
        print("Error: product_hunt_data.json not found.")
        return

    CORE_CATEGORIES = [
        "AI/ML", "Developer Tools", "Productivity", "Design", "Marketing & Sales",
        "Finance", "Education", "Health & Fitness", "Gaming", "Hardware",
        "Security", "Social", "Data & Analytics", "No-Code/Low-Code", "Other"
    ]

    if not openai.api_key:
        print("Error: OPENAI_API_KEY environment variable not set. Cannot process Product Hunt data with LLM.")
        return

    category_map = {}
    all_mapped_categories = []

    print("Mapping Product Hunt topics to core categories using LLM...")
    for product in product_hunt_data:
        product_topics = product.get('topics', [])
        if not product_topics:
            continue

        # Use LLM to map topics to core categories
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant that maps product topics to a predefined list of core categories. Your response must be a JSON array of strings, where each string is one of the following categories: {', '.join(CORE_CATEGORIES)}. If a topic does not fit, map it to 'Other'."},
                    {"role": "user", "content": f"Map the following topics to the core categories: {', '.join(product_topics)}"}
                ],
                response_format={ "type": "json_object" }
            )
            mapped_categories = json.loads(response.choices[0].message.content.strip())
            # Ensure mapped categories are valid and unique for this product
            product_mapped_categories = list(set([cat for cat in mapped_categories if cat in CORE_CATEGORIES]))
            all_mapped_categories.append(product_mapped_categories)

        except Exception as e:
            print(f"Error mapping topics for product {product.get('title')}: {e}")
            all_mapped_categories.append(["Other"])

    # Build Sankey nodes
    nodes = []
    node_to_id = {}
    for i, category in enumerate(CORE_CATEGORIES):
        nodes.append({"node": i, "name": category})
        node_to_id[category] = i

    # Build Sankey links (co-occurrence)
    links = Counter()
    for product_cats in all_mapped_categories:
        # Generate all unique pairs of categories within a product
        for i in range(len(product_cats)):
            for j in range(i + 1, len(product_cats)):
                cat1 = product_cats[i]
                cat2 = product_cats[j]
                # Ensure consistent order for links (e.g., (A,B) not (B,A))
                link_key = tuple(sorted((cat1, cat2)))
                links[link_key] += 1

    sankey_links = []
    for (source_cat, target_cat), value in links.items():
        # Only include links with a minimum co-occurrence to avoid clutter
        if value > 1:
            sankey_links.append({
                "source": node_to_id[source_cat],
                "target": node_to_id[target_cat],
                "value": value
            })

    sankey_data = {
        "nodes": nodes,
        "links": sankey_links
    }

    with open('processed_data/product_hunt_tag_connections.json', 'w') as f:
        json.dump(sankey_data, f, indent=2)

    print("Successfully processed Product Hunt data for Sankey diagram.")


if __name__ == '__main__':
    process_github_trending()
    process_rss_feeds_for_wordcloud()
    process_product_hunt_for_sankey()
