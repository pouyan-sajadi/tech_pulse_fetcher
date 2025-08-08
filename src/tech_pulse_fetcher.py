
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
import time
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TechPulseFetcher:
    def __init__(self, product_hunt_token: Optional[str] = None):
        self.ph_api_url = "https://api.producthunt.com/v2/api/graphql"
        self.ph_token = product_hunt_token or os.getenv('PRODUCT_HUNT_TOKEN')
        self.github_trending_url = "https://github.com/trending"
        self.rss_feeds = {
            'TechCrunch': 'https://techcrunch.com/feed/',
            'The Verge': 'https://www.theverge.com/rss/index.xml',
            'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
            'MIT Tech Review': 'https://www.technologyreview.com/feed/',
            'Hacker News Best': 'https://hnrss.org/best'
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_product_hunt(self, limit: int = 10) -> List[Dict]:
        logging.info("Fetching Product Hunt data...")
        if not self.ph_token:
            logging.warning("No Product Hunt token found. Using fallback method...")
            return self.fetch_product_hunt_rss(limit)
        
        query = """
        query todaysPosts($first: Int!) {
          posts(order: VOTES, first: $first) {
            edges {
              node {
                id
                name
                tagline
                description
                votesCount
                commentsCount
                url
                website
                createdAt
                featuredAt
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"first": limit}
        headers = {
            'Authorization': f'Bearer {self.ph_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(self.ph_api_url, json={'query': query, 'variables': variables}, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'errors' in data:
                    logging.error(f"GraphQL errors: {data['errors']}")
                    return self.fetch_product_hunt_rss(limit)
                
                products = []
                for edge in data.get('data', {}).get('posts', {}).get('edges', []):
                    node = edge['node']
                    products.append({
                        'source': 'Product Hunt',
                        'title': node['name'],
                        'tagline': node['tagline'],
                        'description': node.get('description') or node['tagline'],
                        'url': node['url'],
                        'website': node.get('website', ''),
                        'votes': node['votesCount'],
                        'comments': node['commentsCount'],
                        'topics': [t['node']['name'] for t in node.get('topics', {}).get('edges', [])],
                        'fetched_at': datetime.now().isoformat()
                    })
                logging.info(f"Fetched {len(products)} products from Product Hunt API")
                return products
            else:
                logging.error(f"Product Hunt API error: {response.status_code}")
                return self.fetch_product_hunt_rss(limit)
        except Exception as e:
            logging.error(f"Error fetching Product Hunt: {str(e)}")
            return self.fetch_product_hunt_rss(limit)

    def fetch_product_hunt_rss(self, limit: int = 10) -> List[Dict]:
        logging.info("Using Product Hunt RSS feed as fallback...")
        try:
            feed = feedparser.parse('https://www.producthunt.com/feed')
            products = []
            for entry in feed.entries[:limit]:
                description = entry.get('description', '')
                soup = BeautifulSoup(description, 'html.parser')
                clean_description = soup.get_text().strip()
                products.append({
                    'source': 'Product Hunt (RSS)',
                    'title': entry.get('title', 'Unknown'),
                    'description': clean_description,
                    'url': entry.get('link', ''),
                    'fetched_at': datetime.now().isoformat()
                })
            return products
        except Exception as e:
            logging.error(f"Error fetching Product Hunt RSS: {str(e)}")
            return []

    def fetch_github_trending(self, limit: int = 20) -> List[Dict]:
        logging.info("Fetching GitHub trending repos...")
        try:
            response = requests.get(self.github_trending_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            repos = []
            articles = soup.find_all('article', class_='Box-row', limit=limit)
            for article in articles:
                h2 = article.find('h2', class_='h3')
                if not h2:
                    continue
                repo_link = h2.find('a')
                repo_name = repo_link.get('href', '').strip('/')
                description_p = article.find('p', class_='col-9')
                description = description_p.text.strip() if description_p else 'No description'
                language_span = article.find('span', itemprop='programmingLanguage')
                language = language_span.text.strip() if language_span else 'Unknown'
                star_link = article.find('a', href=f"{repo_link.get('href')}/stargazers")
                stars = 0
                if star_link:
                    star_text = star_link.text.strip().replace(',', '')
                    if 'k' in star_text.lower():
                        stars = int(float(star_text.lower().replace('k', '')) * 1000)
                    else:
                        try:
                            stars = int(star_text)
                        except ValueError:
                            stars = 0
                stars_today_span = article.find('span', class_='d-inline-block float-sm-right')
                stars_today = 0
                if stars_today_span and 'stars today' in stars_today_span.text:
                    try:
                        stars_today_text = stars_today_span.text.strip().split()[0].replace(',', '')
                        stars_today = int(stars_today_text)
                    except (ValueError, IndexError):
                        stars_today = 0
                repos.append({
                    'source': 'GitHub Trending',
                    'title': repo_name,
                    'description': description,
                    'url': f'https://github.com/{repo_name}',
                    'language': language,
                    'stars': stars,
                    'stars_today': stars_today,
                    'fetched_at': datetime.now().isoformat()
                })
            logging.info(f"Fetched {len(repos)} trending repos from GitHub")
            return repos
        except Exception as e:
            logging.error(f"Error fetching GitHub trending: {str(e)}")
            return []

    def fetch_rss_feeds(self, limit_per_feed: int = 5) -> List[Dict]:
        logging.info("Fetching RSS feeds...")
        all_articles = []
        for source_name, feed_url in self.rss_feeds.items():
            try:
                logging.info(f"Fetching {source_name}...")
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:limit_per_feed]:
                    description = ''
                    if hasattr(entry, 'summary'):
                        description = entry.summary
                    elif hasattr(entry, 'description'):
                        description = entry.description
                    if description:
                        soup = BeautifulSoup(description, 'html.parser')
                        description = soup.get_text().strip()
                        if len(description) > 1500:
                            description = description[:997] + '...'
                    if not description or len(description) < 50:
                        continue
                    all_articles.append({
                        'source': f'RSS - {source_name}',
                        'title': entry.get('title', 'No title'),
                        'description': description,
                        'url': entry.get('link', ''),
                        'fetched_at': datetime.now().isoformat()
                    })
                time.sleep(0.5)
            except Exception as e:
                logging.error(f"Error fetching {source_name}: {str(e)}")
                continue
        logging.info(f"Fetched {len(all_articles)} articles from RSS feeds")
        return all_articles

    def fetch_manifold_predictions(self, limit: int = 10) -> List[Dict]:
        logging.info("Fetching Manifold Markets predictions...")
        try:
            response = requests.get("https://api.manifold.markets/v0/markets", params={'limit': 200, 'sort': 'last-bet-time'})
            if response.status_code == 200:
                markets = response.json()
                tech_markets = []
                tech_keywords = ['ai', 'gpt', 'openai', 'google', 'apple', 'meta', 'tech', 'programming', 'software', 'startup', 'crypto', 'llm', 'agi', 'microsoft', 'amazon', 'tesla', 'nvidia', 'chatgpt', 'anthropic', 'claude', 'gemini', 'bard', 'twitter', 'x.com', 'spacex', 'neuralink', 'github', 'bitcoin', 'ethereum', 'blockchain', 'quantum', 'data', 'machine learning', 'neural', 'algorithm', 'compute']
                from datetime import datetime, timedelta
                seven_days_ago_ms = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
                for market in markets:
                    if market.get('outcomeType') != 'BINARY' or market.get('isResolved', False):
                        continue
                    pool = market.get('pool', {})
                    if isinstance(pool, dict):
                        total_pool = pool.get('NO', 0) + pool.get('YES', 0)
                    else:
                        continue
                    if total_pool <= 1000 or market.get('lastBetTime', 0) < seven_days_ago_ms:
                        continue
                    if not any(keyword in market.get('question', '').lower() for keyword in tech_keywords):
                        continue
                    tech_markets.append({
                        'source': 'Manifold Markets',
                        'title': market.get('question', ''),
                        'url': market.get('url', ''),
                        'probability_raw': market.get('probability', 0),
                        'volume': market.get('volume', 0),
                        'fetched_at': datetime.now().isoformat()
                    })
                tech_markets.sort(key=lambda x: x.get('volume', 0), reverse=True)
                logging.info(f"Fetched {len(tech_markets[:limit])} prediction markets from Manifold")
                return tech_markets[:limit]
            else:
                logging.error(f"Failed to fetch from Manifold: {response.status_code}")
                return []
        except Exception as e:
            logging.error(f"Error fetching Manifold markets: {str(e)}")
            return []

    def fetch_all(self) -> Dict[str, List[Dict]]:
        logging.info("Starting Tech Pulse data collection...")
        results = {
            'product_hunt': self.fetch_product_hunt(),
            'github_trending': self.fetch_github_trending(),
            'rss_articles': self.fetch_rss_feeds(),
            'predictions': self.fetch_manifold_predictions()
        }
        total_items = sum(len(v) for v in results.values())
        logging.info(f"Collection complete! Total items: {total_items}")
        return results
