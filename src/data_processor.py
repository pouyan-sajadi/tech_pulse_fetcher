
import json
from collections import Counter

def process_github_trending():
    """
    Analyzes GitHub trending data to find the distribution of programming languages,
    including total stars, stars today, and detailed repo info for frontend interaction.
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
                'stars_today': 0,
                'repositories': [] # Add list to store repo details
            }
        
        language_stats[lang]['repo_count'] += 1
        language_stats[lang]['total_stars'] += repo.get('stars', 0)
        language_stats[lang]['stars_today'] += repo.get('stars_today', 0)
        # Append detailed repo info
        language_stats[lang]['repositories'].append({
            'title': repo.get('title'),
            'description': repo.get('description'),
            'url': repo.get('url'),
            'stars': repo.get('stars'),
            'stars_today': repo.get('stars_today')
        })

    # Group less common languages into "Other"
    total_repos = len(github_data)
    other_stats = {'repo_count': 0, 'total_stars': 0, 'stars_today': 0, 'repositories': []}
    final_languages = {}

    for lang, stats in language_stats.items():
        if stats['repo_count'] / total_repos < 0.02:
            other_stats['repo_count'] += stats['repo_count']
            other_stats['total_stars'] += stats['total_stars']
            other_stats['stars_today'] += stats['stars_today']
            other_stats['repositories'].extend(stats['repositories'])
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
                    'stars_today': stats['stars_today'],
                    'repositories': stats['repositories']
                }
                for stats in final_languages.values()
            ]
        }]
    }

    # Save the processed data
    with open('processed_data/github_language_distribution.json', 'w') as f:
        json.dump(chart_data, f, indent=2)

    print("Successfully processed GitHub trending data with detailed repo info.")

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

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant that rates the relevance of product topics to a predefined list of core categories. Your response must be a JSON object where keys are the categories and values are relevance scores from 1 to 10. The categories are: {', '.join(CORE_CATEGORIES)}."},
                    {"role": "user", "content": f"Rate the relevance of the following topics to the core categories: {', '.join(product_topics)}"}
                ],
                response_format={ "type": "json_object" }
            )
            relevance_scores = json.loads(response.choices[0].message.content.strip())
            
            # Sort categories by relevance and take the top 2
            sorted_categories = sorted(relevance_scores.items(), key=lambda item: item[1], reverse=True)
            product_mapped_categories = [cat for cat, score in sorted_categories[:2] if score > 3] # Only include if score is above a threshold

            print(f"Product: {product.get('title')}, Mapped Categories: {product_mapped_categories}")
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

    # Associate products with each category (node)
    for i, node in enumerate(nodes):
        node_name = node['name']
        node['products'] = []
        for product, mapped_cats in zip(product_hunt_data, all_mapped_categories):
            if node_name in mapped_cats:
                node['products'].append({
                    'title': product.get('title'),
                    'tagline': product.get('tagline')
                })

    # Build Sankey links (co-occurrence) and associate products with each link
    links = Counter()
    link_products = {}

    for product, product_cats in zip(product_hunt_data, all_mapped_categories):
        # Generate all unique pairs of categories within a product
        for i in range(len(product_cats)):
            for j in range(i + 1, len(product_cats)):
                cat1 = product_cats[i]
                cat2 = product_cats[j]
                link_key = tuple(sorted((cat1, cat2)))
                links[link_key] += 1
                
                if link_key not in link_products:
                    link_products[link_key] = []
                link_products[link_key].append({
                    'title': product.get('title'),
                    'tagline': product.get('tagline')
                })

    sankey_links = []
    for (source_cat, target_cat), value in links.items():
        if value > 0: # Keep all links for interactivity
            link_key = tuple(sorted((source_cat, target_cat)))
            sankey_links.append({
                "source": node_to_id[source_cat],
                "target": node_to_id[target_cat],
                "value": value,
                "products": link_products.get(link_key, [])
            })

    sankey_data = {
        "nodes": nodes,
        "links": sankey_links
    }

    with open('processed_data/product_hunt_tag_connections.json', 'w') as f:
        json.dump(sankey_data, f, indent=2)

    print("Successfully processed Product Hunt data for Sankey diagram.")


def process_manifold_predictions_for_bubble_plot():
    """
    Analyzes Manifold Markets data to create data for a 2D scatter plot.
    Uses LLM to categorize predictions.
    """
    try:
        with open('fetched_data/predictions_data.json', 'r') as f:
            predictions_data = json.load(f)
    except FileNotFoundError:
        print("Error: fetched_data/predictions_data.json not found.")
        return

    CORE_PREDICTION_CATEGORIES = [
        "AI", "Blockchain/Crypto", "Science/Research", "Politics/Society",
        "Economics/Finance", "Technology (General)", "Health", "Other"
    ]

    if not openai.api_key:
        print("Error: OPENAI_API_KEY environment variable not set. Cannot process Manifold data with LLM.")
        return

    plot_data = []

    print("Analyzing Manifold predictions for category using LLM...")
    for prediction in predictions_data:
        title = prediction.get('title', '')
        description = prediction.get('description', '')
        full_text = f"Title: {title}. Description: {description}"

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant that categorizes prediction market questions into one of the following: {', '.join(CORE_PREDICTION_CATEGORIES)}. If a category is not suitable, use 'Other'. Your response must be a JSON object like {{'category': 'category_name'}}."},
                    {"role": "user", "content": f"Categorize the following prediction: {full_text}"}
                ],
                response_format={ "type": "json_object" }
            )
            llm_output = json.loads(response.choices[0].message.content.strip())
            category = llm_output.get('category', 'Other')
            
            if category not in CORE_PREDICTION_CATEGORIES:
                category = "Other"

            # New coordinate system based on user request
            x_pos = prediction.get('probability_raw', 0.5)
            y_pos = prediction.get('volume', 0)

            plot_data.append({
                "x": x_pos,
                "y": y_pos,
                "label": title,
                "category": category,
                "url": prediction.get('url', '') # Add URL for frontend
            })

        except Exception as e:
            print(f"Error processing prediction '{title}': {e}")
            plot_data.append({
                "x": 0.5, "y": 0,
                "label": title, "category": "Other"
            })

    # Structure for frontend
    final_data = {
        "datasets": [{
            "label": "Manifold Predictions",
            "data": plot_data
        }],
        "categories": CORE_PREDICTION_CATEGORIES
    }

    with open('processed_data/manifold_predictions_bubble_plot.json', 'w') as f:
        json.dump(final_data, f, indent=2)

    print("Successfully processed Manifold Markets data for scatter plot.")


if __name__ == '__main__':
    process_github_trending()
    process_rss_feeds_for_wordcloud()
    process_product_hunt_for_sankey()
    process_manifold_predictions_for_bubble_plot()
