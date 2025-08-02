import json
from collections import Counter
import re
import os
import openai
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class DataProcessor:
    def __init__(self):
        if not openai.api_key:
            logging.warning("OPENAI_API_KEY environment variable not set. LLM-based processing will be skipped.")

    def process_github_trending(self, github_data):
        logging.info("Processing GitHub trending data...")
        language_stats = {}
        for repo in github_data:
            lang = repo.get('language', 'Unknown')
            if lang == 'Unknown':
                continue
            if lang not in language_stats:
                language_stats[lang] = {'repo_count': 0, 'total_stars': 0, 'stars_today': 0, 'repositories': []}
            language_stats[lang]['repo_count'] += 1
            language_stats[lang]['total_stars'] += repo.get('stars', 0)
            language_stats[lang]['stars_today'] += repo.get('stars_today', 0)
            language_stats[lang]['repositories'].append({
                'title': repo.get('title'),
                'description': repo.get('description'),
                'url': repo.get('url'),
                'stars': repo.get('stars'),
                'stars_today': repo.get('stars_today')
            })

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
        logging.info("Successfully processed GitHub trending data.")
        return chart_data

    def process_rss_feeds_for_wordcloud(self, rss_data):
        logging.info("Processing RSS feed data for word cloud...")
        all_text = " ".join([f"{article.get('title', '')} {article.get('description', '')}" for article in rss_data])
        cleaned_text = re.sub(r'[^a-zA-Z\s]', '', all_text).lower()
        words = cleaned_text.split()
        STOP_WORDS = set(["the", "and", "a", "an", "is", "it", "in", "of", "for", "on", "with", "to", "from", "by", "as", "at", "be", "this", "that", "have", "has", "he", "she", "it", "they", "we", "you", "i", "me", "him", "her", "us", "them", "my", "your", "his", "her", "its", "our", "their", "what", "where", "when", "why", "how", "which", "who", "whom", "whose", "am", "are", "was", "were", "been", "being", "do", "does", "did", "done", "doing", "can", "could", "would", "should", "will", "may", "might", "must", "had", "get", "go", "new", "just", "also", "like", "said", "says", "say", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "up", "down", "out", "in", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "d", "ll", "m", "o", "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren", "won", "wouldn"])
        filtered_words = [word for word in words if word not in STOP_WORDS and len(word) > 2]
        word_counts = Counter(filtered_words)
        top_words = word_counts.most_common(50)
        llm_input_words = ", ".join([f"'{word}' (count: {count})" for word, count in top_words])

        if not openai.api_key:
            logging.error("OPENAI_API_KEY not set. Skipping RSS feed processing.")
            return {}

        try:
            logging.info("Sending top words to LLM for keyword importance and hot topic extraction...")
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts important keywords and identifies hot topics from a list of words and their frequencies. Provide keywords as a JSON array of objects like {'text': 'keyword', 'value': importance_score (1-100)}. Provide hot topics as a JSON array of objects like {'topic': 'topic_name', 'summary': 'brief_summary', 'trend': 'rising|stable|declining'}. The importance score should be a number between 1 and 100, reflecting how significant the keyword is in the context of tech news. Focus on single words or very short phrases that represent key concepts. Do not include common words or stop words. Ensure the output is valid JSON."},
                    {"role": "user", "content": f"From the following list of words and their counts, identify important keywords and hot topics. Words: {llm_input_words}"}
                ],
                response_format={ "type": "json_object" }
            )
            llm_output = json.loads(response.choices[0].message.content)
            logging.info("Successfully processed RSS feed data.")
            return llm_output
        except Exception as e:
            logging.error(f"Error processing RSS feeds with LLM: {e}")
            return {}

    def process_product_hunt_for_sankey(self, product_hunt_data):
        logging.info("Processing Product Hunt data for Sankey diagram...")
        CORE_CATEGORIES = ["AI/ML", "Developer Tools", "Productivity", "Design", "Marketing & Sales", "Finance", "Education", "Health & Fitness", "Gaming", "Hardware", "Security", "Social", "Data & Analytics", "No-Code/Low-Code", "Other"]
        if not openai.api_key:
            logging.error("OPENAI_API_KEY not set. Skipping Product Hunt processing.")
            return {}

        all_mapped_categories = []
        logging.info("Mapping Product Hunt topics to core categories using LLM...")
        for product in product_hunt_data:
            product_topics = product.get('topics', [])
            if not product_topics:
                continue
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": f"You are a helpful assistant that rates the relevance of product topics to a predefined list of core categories. Your response must be a JSON object where keys are the categories and values are relevance scores from 1 to 10. The categories are: {CORE_CATEGORIES}."},
                        {"role": "user", "content": f"Rate the relevance of the following topics to the core categories: {product_topics}"}
                    ],
                    response_format={ "type": "json_object" }
                )
                relevance_scores = json.loads(response.choices[0].message.content.strip())
                sorted_categories = sorted(relevance_scores.items(), key=lambda item: item[1], reverse=True)
                product_mapped_categories = [cat for cat, score in sorted_categories[:2] if score > 3]
                all_mapped_categories.append(product_mapped_categories)
            except Exception as e:
                logging.error(f"Error mapping topics for product {product.get('title')}: {e}")
                all_mapped_categories.append(["Other"])

        nodes = []
        node_to_id = {}
        for i, category in enumerate(CORE_CATEGORIES):
            nodes.append({"node": i, "name": category})
            node_to_id[category] = i

        links = Counter()
        for product_cats in all_mapped_categories:
            for i in range(len(product_cats)):
                for j in range(i + 1, len(product_cats)):
                    links[tuple(sorted((product_cats[i], product_cats[j])))] += 1

        sankey_links = []
        for (source_cat, target_cat), value in links.items():
            if value > 0:
                sankey_links.append({
                    "source": node_to_id[source_cat],
                    "target": node_to_id[target_cat],
                    "value": value
                })

        sankey_data = {"nodes": nodes, "links": sankey_links}
        logging.info("Successfully processed Product Hunt data.")
        return sankey_data

    def process_manifold_predictions_for_bubble_plot(self, predictions_data):
        logging.info("Processing Manifold Markets data for bubble plot...")
        CORE_PREDICTION_CATEGORIES = ["AI", "Blockchain/Crypto", "Science/Research", "Politics/Society", "Economics/Finance", "Technology (General)", "Health", "Other"]
        if not openai.api_key:
            logging.error("OPENAI_API_KEY not set. Skipping Manifold processing.")
            return {}

        plot_data = []
        logging.info("Analyzing Manifold predictions for category using LLM...")
        for prediction in predictions_data:
            title = prediction.get('title', '')
            full_text = f"Title: {title}."
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": f"You are a helpful assistant that categorizes prediction market questions into one of the following: {CORE_PREDICTION_CATEGORIES}. If a category is not suitable, use 'Other'. Your response must be a JSON object like {{'category': 'category_name'}}."},
                        {"role": "user", "content": f"Categorize the following prediction: {full_text}"}
                    ],
                    response_format={ "type": "json_object" }
                )
                llm_output = json.loads(response.choices[0].message.content.strip())
                category = llm_output.get('category', 'Other')
                if category not in CORE_PREDICTION_CATEGORIES:
                    category = "Other"
                plot_data.append({
                    "x": prediction.get('probability_raw', 0.5),
                    "y": prediction.get('volume', 0),
                    "label": title,
                    "category": category,
                    "url": prediction.get('url', '')
                })
            except Exception as e:
                logging.error(f"Error processing prediction '{title}': {e}", exc_info=True)
                plot_data.append({"x": 0.5, "y": 0, "label": title, "category": "Other"})

        final_data = {
            "datasets": [{
                "label": "Manifold Predictions",
                "data": plot_data
            }],
            "categories": CORE_PREDICTION_CATEGORIES
        }
        logging.info("Successfully processed Manifold Markets data.")
        return final_data