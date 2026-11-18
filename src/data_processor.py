import json
from collections import Counter
import re
import os
from urllib.parse import urlsplit
from src.llm_client import llm_client
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

class DataProcessor:
    def __init__(self):
        if not llm_client.api_key:
            logging.warning("LLM_API_KEY environment variable not set. LLM-based processing will be skipped.")

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
        2. To curate the top 5 trending news stories.
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

        if not llm_client.api_key:
            logging.error("LLM_API_KEY not set. Skipping RSS feed processing.")
            return {}

        try:
            # --- LLM Call 1: Generate Keywords with Descriptions for Word Cloud ---
            logging.info("Sending top words to LLM for keyword extraction and description generation...")
            
            word_cloud_system_prompt = {
                "role": "system",
                "content": """You are a Tech Analyst creating an interactive word cloud from daily news. Your mission is to select the most significant keywords, score their importance, and write a concise, news-driven justification for each.

**Your Rules:**
1.  **Select & Score:** Prioritize specific entities (e.g., 'Nvidia', 'Sora', 'RAG') over generic terms ('model', 'data'). Assign a `value` (1-100) based on analytical importance (frequency + specificity + buzz), not just the raw count. Choose 5 to 10 different Words or terms.
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

            word_cloud_output = llm_client.chat_json(
                system_prompt=word_cloud_system_prompt,
                user_message=f"From the following list of words and their counts, generate the keywords JSON for the word cloud: {llm_input_words}"
            )

            final_output = {
                "keywords": word_cloud_output.get("keywords", []),
                "hot_topics": self._curate_news_brief(rss_data),
            }
            
            logging.info("Successfully processed RSS feed data.")
            return final_output

        except Exception as e:
            logging.error(f"Error processing RSS feeds with LLM: {e}")
            return {}

    def _curate_news_brief(self, rss_data):
        articles_by_id = {}
        prompt_articles = []
        seen_urls = set()

        for article in rss_data:
            if not article or not isinstance(article.get("url"), str):
                continue
            url = article["url"].strip()
            if url in seen_urls:
                continue
            try:
                parsed_url = urlsplit(url)
                hostname = parsed_url.hostname
                if parsed_url.scheme not in {"https", "http"} or not hostname:
                    continue
                if parsed_url.username is not None or parsed_url.password is not None:
                    continue
            except ValueError:
                continue

            seen_urls.add(url)
            article_id = f"article-{len(articles_by_id) + 1}"
            title = article.get("title") or hostname
            source = (article.get("source") or "").removeprefix("RSS - ")
            articles_by_id[article_id] = {"title": title, "source": source, "url": url}
            prompt_articles.append({
                "id": article_id,
                "title": title,
                "description": article.get("description", ""),
            })

        if not prompt_articles:
            logging.warning("No RSS articles with usable links for the Daily News Brief.")
            return []

        logging.info("Sending RSS article summaries to the LLM for news curation...")
        response = llm_client.chat_json(
            system_prompt="""Curate up to five distinct tech news stories from the supplied articles.
Rank stories by impact and summarize what happened and why it matters in a few sentences.
Base every claim on the supplied summaries. For each story, list one to three exact article IDs
from the input that support the summary, and omit stories without supporting articles.
Return only a JSON object of this shape:
{"hot_topics":[{"topic":"Story title","summary":"What happened and why it matters",
"momentum":"Growing","source_ids":["article-1"]}]}
Use Intense, Growing, or Steady for momentum.""",
            user_message=json.dumps(prompt_articles),
        )

        proposed_stories = response.get("hot_topics")
        if not isinstance(proposed_stories, list):
            logging.warning("The news curation response did not contain a story list.")
            return []

        stories = []
        for story in proposed_stories:
            if not isinstance(story, dict):
                continue
            title = story.get("topic")
            summary = story.get("summary")
            source_ids = story.get("source_ids")
            if not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(summary, str) or not summary.strip() or not isinstance(source_ids, list):
                continue

            matched_ids = list(dict.fromkeys(
                source_id for source_id in source_ids
                if isinstance(source_id, str) and source_id in articles_by_id
            ))[:3]
            if not matched_ids:
                continue
            stories.append({
                "topic": title.strip(),
                "summary": summary.strip(),
                "momentum": story.get("momentum"),
                "sources": [articles_by_id[source_id] for source_id in matched_ids],
            })
            if len(stories) == 5:
                break

        logging.info("Retained %d news stories with RSS sources.", len(stories))
        return stories

    def process_product_hunt_for_sankey(self, product_hunt_data):
        """
        Processes Product Hunt data to generate connection data for a Nivo Sankey diagram.
        The output format is tailored for interactive charts, with product details
        embedded directly within each node.
        """
        logging.info("Processing Product Hunt data for interactive Nivo Sankey diagram...")
        CORE_CATEGORIES = ["AI/ML", "Developer Tools", "Productivity", "Design", "Marketing & Sales", "Finance", "Education", "Health & Fitness", "Gaming", "Hardware", "Security", "Social", "Data & Analytics", "No-Code/Low-Code", "Other"]
        
        if not llm_client.api_key:
            logging.error("LLM_API_KEY not set. Skipping Product Hunt processing.")
            return {}

        all_mapped_categories = []
        logging.info("Mapping Product Hunt topics to core categories using LLM...")
        for product in product_hunt_data:
            product_topics = product.get('topics', [])
            # Fallback for products with no topics to avoid errors
            if not product_topics:
                all_mapped_categories.append(['Other'])
                continue
            try:
                relevance_scores = llm_client.chat_json(
                    system_prompt=f"You are a helpful assistant that rates the relevance of product topics to a predefined list of core categories. Your response must be a JSON object where keys are the categories and values are relevance scores from 1 to 10. The categories are: {CORE_CATEGORIES}.",
                    user_message=f"Rate the relevance of the following topics to the core categories: {product_topics}"
                )
                # Rank only categories that can appear as chart nodes.
                qualified_scores = (
                    (category, score)
                    for category, score in relevance_scores.items()
                    if category in CORE_CATEGORIES
                    and isinstance(score, (int, float))
                    and 3 < score <= 10
                )
                sorted_categories = sorted(qualified_scores, key=lambda item: item[1], reverse=True)
                product_mapped_categories = [category for category, _ in sorted_categories[:2]]
                all_mapped_categories.append(product_mapped_categories or ["Other"])
            except Exception as e:
                logging.error(f"Error mapping topics for product {product.get('title')}: {e}")
                all_mapped_categories.append(["Other"])

        # 1. Create a map of core categories to the products that fall into them
        category_to_products_map = {category: [] for category in CORE_CATEGORIES}
        for i, product in enumerate(product_hunt_data):
            # Use the description, fallback to tagline
            description = product.get('description') or product.get('tagline', 'No description available.')
            product_info = {
                "title": product.get('title', 'Unknown Product'),
                "url": product.get('url', ''),
                "description": description
            }
            # Use the mapped categories from the LLM step
            mapped_categories_for_product = all_mapped_categories[i]
            for category in mapped_categories_for_product:
                if category in category_to_products_map:
                    category_to_products_map[category].append(product_info)

        # 2. Create the new, enriched nodes for the Sankey chart
        nivo_nodes = [{"id": category, "products": category_to_products_map.get(category, [])} for category in CORE_CATEGORIES]

        # 3. Create links based on co-occurrence in mapped categories
        links_counter = Counter()
        for product_cats in all_mapped_categories:
            for i in range(len(product_cats)):
                for j in range(i + 1, len(product_cats)):
                    links_counter[tuple(sorted((product_cats[i], product_cats[j])))] += 1
        
        nivo_links = []
        for (source_cat, target_cat), value in links_counter.items():
            if value > 0:
                nivo_links.append({
                    "source": source_cat,
                    "target": target_cat,
                    "value": value
                })

        # 4. Assemble the final Sankey data structure
        # This cleaner structure avoids the nested key and removes the now-redundant product_details
        sankey_data = {"nodes": nivo_nodes, "links": nivo_links}
        
        logging.info("Successfully processed Product Hunt data for Nivo with enriched nodes.")
        return sankey_data

    def process_manifold_predictions_for_bubble_plot(self, predictions_data):
        logging.info("Processing Manifold Markets data for bubble plot...")
        CORE_PREDICTION_CATEGORIES = ["AI", "Blockchain/Crypto", "Science/Research", "Politics/Society", "Economics/Finance", "Technology (General)", "Health", "Other"]
        if not llm_client.api_key:
            logging.error("LLM_API_KEY not set. Skipping Manifold processing.")
            return {}

        plot_data = []
        logging.info("Analyzing Manifold predictions for category using LLM...")
        for prediction in predictions_data:
            title = prediction.get('title', '')
            full_text = f"Title: {title}."
            try:
                llm_output = llm_client.chat_json(
                    system_prompt=f"You are a helpful assistant that categorizes prediction market questions into one of the following: {CORE_PREDICTION_CATEGORIES}. If a category is not suitable, use 'Other'. Your response must be a JSON object like {{'category': 'category_name'}}.",
                    user_message=f"Categorize the following prediction: {full_text}"
                )
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
