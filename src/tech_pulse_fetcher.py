"""
tech_pulse_fetcher.py - UPDATED WITH PRODUCT HUNT API
Fetches data from Product Hunt API, GitHub Trending, and Tech RSS feeds
"""

import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
import time
import os

class TechPulseFetcher:
    def __init__(self, product_hunt_token: Optional[str] = None):
        # Product Hunt API endpoint
        self.ph_api_url = "https://api.producthunt.com/v2/api/graphql"
        self.ph_token = product_hunt_token or os.getenv('PRODUCT_HUNT_TOKEN')
        
        # GitHub trending URL
        self.github_trending_url = "https://github.com/trending"
        
        # Curated tech RSS feeds that provide good summaries
        self.rss_feeds = {
            'TechCrunch': 'https://techcrunch.com/feed/',
            'The Verge': 'https://www.theverge.com/rss/index.xml',
            'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
            'MIT Tech Review': 'https://www.technologyreview.com/feed/',
            'Hacker News Best': 'https://hnrss.org/best'  # HN RSS with descriptions
        }
        
        # Headers for web scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_product_hunt(self, limit: int = 10) -> List[Dict]:
        """
        Fetch top products from Product Hunt using their GraphQL API
        """
        print("🚀 Fetching Product Hunt data...")
        
        if not self.ph_token:
            print("⚠️  No Product Hunt token found. Using fallback method...")
            return self.fetch_product_hunt_rss(limit)
        
        # GraphQL query for today's posts
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
                user {
                  name
                  username
                }
                makers {
                  name
                  username
                }
              }
            }
          }
        }
        """
        
        variables = {
            "first": limit
        }
        
        headers = {
            'Authorization': f'Bearer {self.ph_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(
                self.ph_api_url,
                json={'query': query, 'variables': variables},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"❌ GraphQL errors: {data['errors']}")
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
                        'makers': [m.get('name', 'Unknown') for m in node.get('makers', [])],
                        'hunter': node.get('user', {}).get('name', 'Unknown'),
                        'created_at': node['createdAt'],
                        'featured_at': node.get('featuredAt'),
                        'fetched_at': datetime.now().isoformat()
                    })
                
                print(f"✅ Fetched {len(products)} products from Product Hunt API")
                return products
            else:
                print(f"❌ Product Hunt API error: {response.status_code}")
                print(f"Response: {response.text}")
                return self.fetch_product_hunt_rss(limit)
                
        except Exception as e:
            print(f"❌ Error fetching Product Hunt: {str(e)}")
            return self.fetch_product_hunt_rss(limit)

    def fetch_product_hunt_rss(self, limit: int = 10) -> List[Dict]:
        """
        Fallback: Use Product Hunt's RSS feed
        """
        print("📡 Using Product Hunt RSS feed as fallback...")
        try:
            # Product Hunt RSS feed
            feed = feedparser.parse('https://www.producthunt.com/feed')
            
            products = []
            for entry in feed.entries[:limit]:
                # Parse the description to extract more info
                description = entry.get('description', '')
                soup = BeautifulSoup(description, 'html.parser')
                clean_description = soup.get_text().strip()
                
                products.append({
                    'source': 'Product Hunt (RSS)',
                    'title': entry.get('title', 'Unknown'),
                    'tagline': clean_description[:1000] + '...' if len(clean_description) > 1000 else clean_description,
                    'description': clean_description,
                    'url': entry.get('link', ''),
                    'votes': 0,  # Not available in RSS
                    'comments': 0,
                    'published': entry.get('published', ''),
                    'fetched_at': datetime.now().isoformat()
                })
            
            return products
            
        except Exception as e:
            print(f"❌ Error fetching Product Hunt RSS: {str(e)}")
            return []

    def fetch_github_trending(self, limit: int = 10) -> List[Dict]:
        """
        Scrape GitHub trending repositories
        """
        print("🔥 Fetching GitHub trending repos...")
        
        try:
            response = requests.get(self.github_trending_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            repos = []
            articles = soup.find_all('article', class_='Box-row', limit=limit)
            
            for article in articles:
                # Extract repository info
                h2 = article.find('h2', class_='h3')
                if not h2:
                    continue
                    
                repo_link = h2.find('a')
                repo_name = repo_link.get('href', '').strip('/')
                
                # Get description
                description_p = article.find('p', class_='col-9')
                description = description_p.text.strip() if description_p else 'No description'
                
                # Get language
                language_span = article.find('span', itemprop='programmingLanguage')
                language = language_span.text.strip() if language_span else 'Unknown'
                
                # Get stars and forks
                stats = article.find_all('a', class_='Link--muted')
                stars = 0
                stars_today = 0
                
                for stat in stats:
                    text = stat.text.strip()
                    if 'star' in text.lower():
                        stars_text = text.replace(',', '').split()[0]
                        try:
                            stars = int(stars_text)
                        except:
                            stars = 0
                
                # Get stars today (if available)
                star_today_span = article.find('span', class_='d-inline-block')
                if star_today_span and 'stars today' in star_today_span.text:
                    try:
                        stars_today = int(star_today_span.text.split()[0].replace(',', ''))
                    except:
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
            
            print(f"✅ Fetched {len(repos)} trending repos from GitHub")
            return repos
            
        except Exception as e:
            print(f"❌ Error fetching GitHub trending: {str(e)}")
            return []

    def fetch_rss_feeds(self, limit_per_feed: int = 5) -> List[Dict]:
        """
        Fetch articles from tech RSS feeds
        Only includes feeds that provide descriptions/summaries
        """
        print("📰 Fetching RSS feeds...")
        
        all_articles = []
        
        for source_name, feed_url in self.rss_feeds.items():
            try:
                print(f"  📡 Fetching {source_name}...")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:limit_per_feed]:
                    # Get description/summary
                    description = ''
                    if hasattr(entry, 'summary'):
                        description = entry.summary
                    elif hasattr(entry, 'description'):
                        description = entry.description
                    
                    # Clean HTML from description
                    if description:
                        soup = BeautifulSoup(description, 'html.parser')
                        description = soup.get_text().strip()
                        # Limit description length
                        if len(description) > 1000:
                            description = description[:997] + '...'
                    
                    # Skip if no description
                    if not description or len(description) < 50:
                        continue
                    
                    article = {
                        'source': f'RSS - {source_name}',
                        'title': entry.get('title', 'No title'),
                        'description': description,
                        'url': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'author': entry.get('author', 'Unknown'),
                        'tags': [tag['term'] for tag in entry.get('tags', [])],
                        'fetched_at': datetime.now().isoformat()
                    }
                    
                    all_articles.append(article)
                
                # Small delay to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ Error fetching {source_name}: {str(e)}")
                continue
        
        print(f"✅ Fetched {len(all_articles)} articles from RSS feeds")
        return all_articles
 
        """
        Alternative: Try the search endpoint
        """
        print("🎯 Trying alternative Manifold endpoint...")
        
        try:
            # Try the search endpoint with tech terms
            tech_terms = ['AI', 'GPT', 'tech', 'Google', 'Microsoft']
            all_markets = []
            
            for term in tech_terms[:2]:  # Just try first 2 to avoid rate limits
                response = requests.get(
                    f"https://manifold.markets/api/v0/search-markets",
                    params={
                        'term': term,
                        'filter': 'open',
                        'sort': 'volume',
                        'limit': 10
                    }
                )
                
                if response.status_code == 200:
                    markets = response.json()
                    all_markets.extend(markets)
            
            # Remove duplicates and format
            seen = set()
            tech_markets = []
            
            for market in all_markets:
                market_id = market.get('id')
                if market_id not in seen:
                    seen.add(market_id)
                    tech_markets.append({
                        'source': 'Manifold Markets',
                        'title': market.get('question', 'Unknown'),
                        'probability': f"{int(market.get('probability', 0) * 100)}%",
                        'volume': market.get('volume', 0),
                        'url': market.get('url', ''),
                        'fetched_at': datetime.now().isoformat()
                    })
            
            return tech_markets[:limit]
            
        except Exception as e:
            print(f"❌ Alternative method failed: {str(e)}")
            return []

    def fetch_manifold_predictions(self, limit: int = 10) -> List[Dict]:
        """
        Fetch prediction markets from Manifold Markets with specific filters
        """
        print("🎯 Fetching Manifold Markets predictions...")
        
        try:
            # Get more markets to filter through
            response = requests.get(
                "https://api.manifold.markets/v0/markets",
                params={
                    'limit': 200,  # Get more since we'll filter heavily
                    'sort': 'last-bet-time'  # Still get active markets
                }
            )
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                markets = response.json()
                print(f"   Total markets fetched: {len(markets)}")
                
                tech_markets = []
                
                # Comprehensive tech keywords
                tech_keywords = ['ai', 'gpt', 'openai', 'google', 'apple', 'meta', 
                            'tech', 'programming', 'software', 'startup', 'crypto',
                            'llm', 'agi', 'microsoft', 'amazon', 'tesla', 'nvidia',
                            'chatgpt', 'anthropic', 'claude', 'gemini', 'bard',
                            'twitter', 'x.com', 'spacex', 'neuralink', 'github',
                            'bitcoin', 'ethereum', 'blockchain', 'quantum', 'data',
                            'machine learning', 'neural', 'algorithm', 'compute']
                
                # Get current time and 7 days ago
                from datetime import datetime, timedelta
                current_time = datetime.now()
                seven_days_ago = current_time - timedelta(days=7)
                seven_days_ago_ms = int(seven_days_ago.timestamp() * 1000)
                
                for market in markets:
                    # Filter 1: Only BINARY markets
                    if market.get('outcomeType') != 'BINARY':
                        continue
                    
                    # Filter 2: Not resolved
                    if market.get('isResolved', False):
                        continue
                    
                    # Filter 3: Calculate total pool and check if > 1000
                    pool = market.get('pool', {})
                    if isinstance(pool, dict):
                        no_shares = pool.get('NO', 0)
                        yes_shares = pool.get('YES', 0)
                        total_pool = no_shares + yes_shares
                    else:
                        continue  # Skip if no pool data
                    
                    if total_pool <= 1000:
                        continue
                    
                    # Filter 4: Has activity in last 7 days
                    last_bet_time = market.get('lastBetTime', 0)
                    if last_bet_time < seven_days_ago_ms:
                        continue
                    
                    # Filter 5: Tech-related
                    question = market.get('question', '')
                    title_lower = question.lower()
                    
                    if not any(keyword in title_lower for keyword in tech_keywords):
                        continue
                    
                    # All filters passed, extract data
                    probability = market.get('probability', 0)
                    probability_pct = int(probability * 100)
                    
                    # Get timing info
                    close_time = market.get('closeTime')
                    if close_time:
                        close_date = datetime.fromtimestamp(close_time / 1000).strftime('%Y-%m-%d')
                    else:
                        close_date = 'No close date'
                    
                    # Calculate days since last bet
                    if last_bet_time:
                        days_since_bet = (current_time - datetime.fromtimestamp(last_bet_time / 1000)).days
                    else:
                        days_since_bet = None
                    
                    # Build market data
                    market_data = {
                        'source': 'Manifold Markets',
                        'id': market.get('id', ''),
                        'title': question,
                        'slug': market.get('slug', ''),
                        'url': market.get('url', ''),
                        
                        # Probability and pool info
                        'probability': f"{probability_pct}%",
                        'probability_raw': probability,
                        'pool_total': total_pool,  # Keep as number for sorting
                        'pool_total_display': f"${total_pool:,.0f}",
                        'pool_yes': f"${yes_shares:,.0f}",
                        'pool_no': f"${no_shares:,.0f}",
                        
                        # Volume and activity
                        'volume': market.get('volume', 0),
                        'total_liquidity': market.get('totalLiquidity', 0),
                        'unique_bettors': market.get('uniqueBettorCount', 0),
                        
                        # Creator info
                        'creator_name': market.get('creatorName', 'Unknown'),
                        'creator_username': market.get('creatorUsername', ''),
                        
                        # Timing
                        'close_date': close_date,
                        'days_since_last_bet': days_since_bet,
                        
                        # Market type (always BINARY based on filter)
                        'outcome_type': 'BINARY',
                        
                        # Description (first 200 chars)
                        'description': market.get('description', '')[:200] + '...' if market.get('description') else 'No description',
                        
                        # Meta
                        'fetched_at': current_time.isoformat()
                    }
                    
                    tech_markets.append(market_data)
                    
                    # Debug info
                    if len(tech_markets) <= 3:
                        print(f"   Found: {question[:50]}... (Pool: ${total_pool:,.0f})")
                
                # Sort by total pool value (descending)
                tech_markets.sort(key=lambda x: x['pool_total'], reverse=True)
                
                # Take top markets
                tech_markets = tech_markets[:limit]
                
                print(f"✅ Fetched {len(tech_markets)} prediction markets from Manifold")
                print(f"   (Filtered: BINARY only, pool > $1000, active in last 7 days)")
                return tech_markets
            else:
                print(f"❌ Failed to fetch from Manifold: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching Manifold markets: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def test_manifold_api_params(self):
        """Test what parameters work with the new API"""
        base_url = "https://api.manifold.markets/v0/markets"
        
        # Test different parameter combinations
        test_params = [
            {'limit': 5},
            {'limit': 5, 'sort': 'volume'},
            {'limit': 5, 'sort': 'last-bet-time'},
            {'limit': 5, 'sort': 'created-time'},
        ]
        
        for params in test_params:
            try:
                response = requests.get(base_url, params=params)
                print(f"Params {params}: Status {response.status_code}")
                if response.status_code != 200:
                    print(f"  Error: {response.text[:100]}")
            except Exception as e:
                print(f"Params {params}: Failed - {e}")

    def fetch_metaculus_predictions(self, limit: int = 5) -> List[Dict]:
        """
        Scrape Metaculus predictions (more complex but doable)
        """
        print("🔮 Fetching Metaculus predictions...")
        
        try:
            # Metaculus AI category page
            url = "https://www.metaculus.com/questions/?categories=ai-computing"
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            predictions = []
            
            # Find question cards (structure may change)
            questions = soup.find_all('div', class_='question-card', limit=limit)
            
            for q in questions:
                title_elem = q.find('h2') or q.find('a', class_='question-title')
                if title_elem:
                    title = title_elem.text.strip()
                    
                    # Try to find probability
                    prob_elem = q.find('div', class_='prediction-value')
                    probability = prob_elem.text.strip() if prob_elem else 'Unknown'
                    
                    # Get link
                    link_elem = q.find('a', href=True)
                    url = f"https://www.metaculus.com{link_elem['href']}" if link_elem else ''
                    
                    predictions.append({
                        'source': 'Metaculus',
                        'title': title,
                        'probability': probability,
                        'url': url,
                        'market_type': 'forecast',
                        'fetched_at': datetime.now().isoformat()
                    })
            
            print(f"✅ Fetched {len(predictions)} predictions from Metaculus")
            return predictions
            
        except Exception as e:
            print(f"❌ Error fetching Metaculus: {str(e)}")
            return []

    def fetch_all(self) -> Dict[str, List[Dict]]:
        """
        Fetch data from all sources
        """
        print("\n🎯 Starting Tech Pulse data collection...\n")
        
        results = {
            'metadata': {
                'fetched_at': datetime.now().isoformat(),
                'sources': ['Product Hunt', 'GitHub Trending', 'RSS Feeds', 'Manifold Markets']
            },
            'product_hunt': self.fetch_product_hunt(),
            'github_trending': self.fetch_github_trending(),
            'rss_articles': self.fetch_rss_feeds(),
            'predictions': self.fetch_manifold_predictions()  # Changed from kalshi
        }
        
        # Calculate totals
        total_items = (
            len(results['product_hunt']) + 
            len(results['github_trending']) + 
            len(results['rss_articles']) + 
            len(results['predictions'])
        )
        
        results['metadata']['total_items'] = total_items
        
        print(f"\n✨ Collection complete! Total items: {total_items}")
        
        return results

    def save_to_json(self, data: Dict, filename: str = 'tech_pulse_data.json'):
        """
        Save fetched data to JSON file
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Data saved to {filename}")

    def print_summary(self, data: Dict):
        """
        Print a nice summary of fetched data
        """
        print("\n" + "="*50)
        print("📊 TECH PULSE SUMMARY")
        print("="*50)
        
        # Product Hunt summary
        if data['product_hunt']:
            print("\n🚀 Product Hunt Top Products:")
            for i, product in enumerate(data['product_hunt'][:3], 1):
                print(f"{i}. {product['title']} - {product['tagline']}")
                print(f"   Votes: {product.get('votes', 'N/A')} | Comments: {product.get('comments', 'N/A')}")
        
        # GitHub summary
        if data['github_trending']:
            print("\n🔥 GitHub Trending Repos:")
            for i, repo in enumerate(data['github_trending'][:3], 1):
                print(f"{i}. {repo['title']} ({repo['language']})")
                print(f"   ⭐ {repo['stars']} | 🔥 {repo.get('stars_today', 0)} today")
        
        # RSS summary
        if data['rss_articles']:
            print("\n📰 Latest Tech News:")
            for i, article in enumerate(data['rss_articles'][:3], 1):
                print(f"{i}. {article['title']}")
                print(f"   Source: {article['source']}")
                print(f"   Preview: {article['description'][:100]}...")

        # Predictions summary (works for both Manifold and Kalshi)
        if data.get('predictions'):
            predictions = data.get('predictions')
            print("\n🔮 Prediction Markets:")
            for i, market in enumerate(predictions[:3], 1):
                print(f"{i}. {market['title'][:70]}{'...' if len(market['title']) > 70 else ''}")
                print(f"   📊 {market['probability']} chance | 💰 Pool: {market['pool_total']} | 👥 {market['unique_bettors']} bettors")
                print(f"   📈 24h Volume: ${market['volume_24h']:,.0f} | ⏰ Closes: {market['close_date']}")
        
        
        print("\n" + "="*50)


# Main execution continued
if __name__ == "__main__":
    # Create fetcher instance
    fetcher = TechPulseFetcher()
    
    if not fetcher.ph_token:
        print("\n⚠️  WARNING: No Product Hunt API token found!")
        print("To get full Product Hunt data:")
        print("1. Go to https://www.producthunt.com/v2/oauth/applications")
        print("2. Create a new application")
        print("3. Get your developer token")
        print("4. Set environment variable: export PRODUCT_HUNT_TOKEN='your_token'")
        print("\nContinuing with RSS fallback for Product Hunt...\n")
    
    # Fetch all data
    data = fetcher.fetch_all()
    
    # Save to main JSON file
    fetcher.save_to_json(data, 'tech_pulse_all.json')
    
    # Save individual source files for easier inspection
    if data.get('product_hunt'):
        fetcher.save_to_json(data['product_hunt'], 'product_hunt_data.json')
    
    if data.get('github_trending'):
        fetcher.save_to_json(data['github_trending'], 'github_trending_data.json')
    
    if data.get('rss_articles'):
        fetcher.save_to_json(data['rss_articles'], 'rss_feeds_data.json')
    
    # Save predictions (handles both 'predictions' and 'kalshi_predictions' keys)
    if data.get('predictions'):
        fetcher.save_to_json(data['predictions'], 'predictions_data.json')
    elif data.get('kalshi_predictions'):
        fetcher.save_to_json(data['kalshi_predictions'], 'kalshi_predictions_data.json')
    
    # Print summary
    fetcher.print_summary(data)
    
    # Print file locations
    print("\n📁 Data files created:")
    print("  - tech_pulse_all.json (complete dataset)")
    print("  - product_hunt_data.json")
    print("  - github_trending_data.json") 
    print("  - rss_feeds_data.json")
    if data.get('predictions') or data.get('kalshi_predictions'):
        print("  - predictions_data.json")