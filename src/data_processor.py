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
        """
        Processes RSS feed data by making two distinct LLM calls:
        1. To generate keywords for a word cloud, including a contextual description for each.
        2. To curate the top 3-5 trending news stories.
        """
        logging.info("Processing RSS feed data for word cloud and trending news...")
        
        # --- Data Preparation ---
        all_text = " ".join([f"{article.get('title', '')} {article.get('description', '')}" for article in rss_data if article])
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
            # --- LLM Call 1: Generate Keywords with Descriptions for Word Cloud ---
            logging.info("Sending top words to LLM for keyword extraction and description generation...")
            
            word_cloud_system_prompt = {
                "role": "system",
                "content": """You are a Tech Analyst creating an interactive word cloud from daily news. Your mission is to select the most significant keywords, score their importance, and write a concise, news-driven justification for each.

**Your Rules:**
1.  **Select & Score:** Prioritize specific entities (e.g., 'Nvidia', 'Sora', 'RAG') over generic terms ('model', 'data'). Assign a `value` (1-100) based on analytical importance (frequency + specificity + buzz), not just the raw count.
2.  **Justify with `desc`:** This is the critical task. The `desc` field **MUST** justify why the keyword is in the news *today*. It is a one-sentence summary of its relevance in the source articles, not a generic definition.

    *   **Keyword:** `Gemini`
        *   **BAD (Generic):** "An advanced AI model by Google."
        *   **GOOD (News-driven):** "Featured in today's news for its 1.5 Pro update and expanded context window."

    *   **Keyword:** `Blackwell`
        *   **BAD (Generic):** "A new GPU architecture from Nvidia."
        *   **GOOD (News-driven):** "Dominating headlines as Nvidia's just-announced GPU platform, promising a major leap in AI performance."

**Output Format:**
Your entire output must be a single, valid JSON object with a `keywords` key. Adhere strictly to this format:
{
  "keywords": [
    {
      "text": "Blackwell",
      "value": 95,
      "desc": "Unveiled at the GTC conference today, with reports highlighting its 5x performance increase over the H100 model."
    },
    {
      "text": "Sora",
      "value": 88,
      "desc": "Made headlines as OpenAI announced it is now granting access to a select group of filmmakers for creative projects."
    }
  ]
}"""
            }

            word_cloud_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    word_cloud_system_prompt,
                    {"role": "user", "content": f"From the following list of words and their counts, generate the keywords JSON for the word cloud: {llm_input_words}"}
                ],
                response_format={"type": "json_object"}
            )
            word_cloud_output = json.loads(word_cloud_response.choices[0].message.content)

            # --- LLM Call 2: Curate Top News Stories ---
            logging.info("Sending summarized RSS feed data to LLM for top news curation...")
            
            # Prepare data for LLM Call 2
            summarized_rss_data = [{"title": article.get('title', ''), "description": article.get('description', '')} for article in rss_data if article]
            
            trending_news_system_prompt = {
                "role": "system",
                "content": """You are the Chief Editor of 'The Daily Signal', a prestigious daily tech newsletter. Your mission is to analyze a collection of today's tech article summaries and curate the definitive 'Top 5 Most Significant Stories'.

**Your Curation Heuristics:**
1.  **Identify Major Themes & Avoid Redundancy:** Scan all summaries to find overlapping stories. Your Top 5 should represent five *distinct* events or trends.
2.  **Rank by Impact:** Prioritize major product launches, significant research breakthroughs, and major industry shifts.
3.  **Synthesize and Summarize:** For each topic, write a new, concise `summary` explaining what happened and why it's important.
4.  **Assess `momentum`:** Based on the intensity of discussion in today's news, label the topic's momentum as `Intense` (dominating headlines), `Growing` (emerging and gaining traction), or `Steady` (important ongoing conversation).

**Output Format:**
Your entire response must be a single, valid JSON object with a single key `hot_topics`. The array should contain 3 to 5 topic objects.

```json
{
  "hot_topics": [
    {
      "topic": "The Generative Video Arms Race",
      "summary": "OpenAI's Sora model is driving intense discussion and competition, with rivals racing to release comparable text-to-video technologies.",
      "momentum": "Intense"
    },
    {
      "topic": "Nvidia's Next-Gen AI Hardware",
      "summary": "The announcement of the Blackwell GPU architecture sets a new benchmark for AI computation, aiming to solidify Nvidia's market dominance.",
      "momentum": "Intense"
    },
    {
      "topic": "The Consolidation of AI Assistants",
      "summary": "Recent acquisitions and feature integrations suggest the market for standalone AI assistants is maturing and consolidating around major tech players.",
      "momentum": "Growing"
    }
  ]
}
```"""
            }

            trending_news_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    trending_news_system_prompt,
                    {"role": "user", "content": f"Analyze the following tech news summaries and curate the hot topics JSON: {json.dumps(summarized_rss_data)}"}
                ],
                response_format={"type": "json_object"}
            )
            trending_news_output = json.loads(trending_news_response.choices[0].message.content)

            # --- Combine Outputs ---
            final_output = {
                "keywords": word_cloud_output.get("keywords", []),
                "hot_topics": trending_news_output.get("hot_topics", [])
            }
            
            logging.info("Successfully processed RSS feed data with two LLM calls.")
            return final_output

        except Exception as e:
            logging.error(f"An error occurred during LLM processing: {e}")
            return {}
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

        # Also return product details for linking/display in frontend
        product_details = []
        for product in product_hunt_data:
            product_details.append({
                "title": product.get('title', ''),
                "url": product.get('url', ''),
                "topics": product.get('topics', [])
            })

        final_product_hunt_data = {
            "sankey_data": sankey_data,
            "product_details": product_details
        }
        logging.info("Successfully processed Product Hunt data.")
        return final_product_hunt_data

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