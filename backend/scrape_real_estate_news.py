"""
Real Estate News Scraper
Fetches real estate news from various Indian sources using RSS feeds and web scraping
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import time
import random
import os
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealEstateNewsScraper:
    """Scrapes real estate news from multiple sources"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # RSS Feeds for real estate news
        self.rss_feeds = [
            {
                'url': 'https://economictimes.indiatimes.com/wealth/real-estate/rssfeeds/48101904.cms',
                'source': 'Economic Times',
                'category': 'real-estate'
            },
            {
                'url': 'https://www.moneycontrol.com/rss/realestate.xml',
                'source': 'MoneyControl',
                'category': 'real-estate'
            },
            {
                'url': 'https://housing.com/news/feed/',
                'source': 'Housing.com News',
                'category': 'real-estate'
            },
            {
                'url': 'https://www.hindustantimes.com/feeds/rss/real-estate',
                'source': 'Hindustan Times',
                'category': 'real-estate'
            },
            {
                'url': 'https://www.indiatoday.in/rss/real-estate',
                'source': 'India Today',
                'category': 'real-estate'
            },
            {
                'url': 'https://www.financialexpress.com/industry/real-estate/feed/',
                'source': 'Financial Express',
                'category': 'real-estate'
            },
            {
                'url': 'https://www.business-standard.com/rss/real-estate-107.rss',
                'source': 'Business Standard',
                'category': 'real-estate'
            },
            {
                'url': 'https://www.livemint.com/rss/companies/real-estate',
                'source': 'LiveMint',
                'category': 'real-estate'
            },
            {
                'url': 'https://news.google.com/rss/search?q=real+estate+india&hl=en-IN&gl=IN&ceid=IN:en',
                'source': 'Google News',
                'category': 'real-estate'
            },
            {
                'url': 'https://news.google.com/rss/search?q=property+prices+india&hl=en-IN&gl=IN&ceid=IN:en',
                'source': 'Google News',
                'category': 'real-estate'
            },
            {
                'url': 'https://news.google.com/rss/search?q=metro+rail+real+estate+india&hl=en-IN&gl=IN&ceid=IN:en',
                'source': 'Google News',
                'category': 'real-estate'
            }
        ]

    def _fetch_feed_entries(self, feed_url: str) -> List[Dict]:
        """Fetch RSS feed with headers and return entries"""
        try:
            response = requests.get(feed_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            return feed.entries
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
            return []
    
    def scrape_rss_feeds(self) -> List[Dict]:
        """Scrape news from RSS feeds"""
        all_articles = []
        
        for feed_info in self.rss_feeds:
            try:
                logger.info(f"Fetching from {feed_info['source']}...")
                entries = self._fetch_feed_entries(feed_info['url'])
                
                for entry in entries[:30]:  # Limit to 30 articles per feed
                    article = self._parse_rss_entry(entry, feed_info['source'])
                    if article:
                        all_articles.append(article)
                
                # Be polite - add delay between requests
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                logger.error(f"Error fetching {feed_info['source']}: {str(e)}")
        
        return all_articles
    
    def _parse_rss_entry(self, entry, source: str) -> Dict:
        """Parse a single RSS entry"""
        try:
            # Extract location from title/content
            title = entry.get('title', '')
            content = entry.get('summary', entry.get('description', ''))
            
            # Clean HTML from content
            content = BeautifulSoup(content, 'html.parser').get_text()
            
            # Extract location (simple keyword matching)
            location = self._extract_location(title + ' ' + content)
            
            # Calculate impact score based on keywords
            impact_score = self._calculate_impact_score(title + ' ' + content)
            
            # Get published date
            published = entry.get('published', entry.get('updated', ''))
            try:
                date = datetime(*entry.published_parsed[:6]).isoformat()
            except:
                date = datetime.now().isoformat()
            
            return {
                'id': f"news_{hash(entry.link)}",
                'title': title[:200],  # Limit title length
                'content': content[:1000],  # Limit content length
                'location': location,
                'date': date,
                'source': source,
                'url': entry.get('link', ''),
                'impact_score': impact_score
            }
        except Exception as e:
            logger.error(f"Error parsing entry: {str(e)}")
            return None
    
    def _extract_location(self, text: str) -> str:
        """Extract location from text using keyword matching"""
        locations = [
            'Mumbai', 'Bangalore', 'Delhi', 'NCR', 'Hyderabad', 'Pune', 
            'Ahmedabad', 'Chennai', 'Kolkata', 'Gurgaon', 'Noida', 
            'Goa', 'Navi Mumbai', 'Thane', 'Andheri', 'Worli', 'Bandra',
            'Whitefield', 'Electronic City', 'Hinjewadi', 'Powai',
            'Gachibowli', 'Hitech City', 'Koramangala', 'Indiranagar',
            'Bhopal', 'Jaipur', 'Lucknow', 'Chandigarh', 'Kochi', 'Indore'
        ]
        
        text_lower = text.lower()
        for location in locations:
            if location.lower() in text_lower:
                return location
        
        # Default to a major city if no location found
        return "India"
    
    def _calculate_impact_score(self, text: str) -> float:
        """Calculate impact score based on keywords"""
        text_lower = text.lower()
        
        # High impact keywords
        high_impact = ['metro', 'airport', 'smart city', 'billion', 'expressway', 
                      'mega project', 'infrastructure', 'approved', 'launched']
        
        # Moderate impact keywords
        moderate_impact = ['development', 'growth', 'increase', 'new project', 
                          'expansion', 'connectivity', 'residential', 'commercial']
        
        # Negative impact keywords
        negative_impact = ['delay', 'stuck', 'problem', 'issue', 'slowdown', 
                          'decline', 'concern', 'risk']
        
        score = 0.5  # Base score
        
        for keyword in high_impact:
            if keyword in text_lower:
                score += 0.1
        
        for keyword in moderate_impact:
            if keyword in text_lower:
                score += 0.05
        
        for keyword in negative_impact:
            if keyword in text_lower:
                score -= 0.15
        
        # Normalize to 0-1 range
        return max(0.0, min(1.0, score))
    
    def scrape_housing_news(self) -> List[Dict]:
        """Scrape news from Housing.com news section"""
        articles = []
        
        try:
            url = "https://housing.com/news/"
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article links (adjust selectors based on actual site structure)
            article_cards = soup.find_all('article', limit=20)
            
            for card in article_cards:
                try:
                    title_elem = card.find('h2') or card.find('h3')
                    link_elem = card.find('a')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        if not url.startswith('http'):
                            url = 'https://housing.com' + url
                        
                        # Get article content (summary)
                        content_elem = card.find('p')
                        content = content_elem.get_text(strip=True) if content_elem else title
                        
                        location = self._extract_location(title + ' ' + content)
                        impact_score = self._calculate_impact_score(title + ' ' + content)
                        
                        articles.append({
                            'id': f"news_{hash(url)}",
                            'title': title[:200],
                            'content': content[:1000],
                            'location': location,
                            'date': datetime.now().isoformat(),
                            'source': 'Housing.com',
                            'url': url,
                            'impact_score': impact_score
                        })
                except Exception as e:
                    logger.error(f"Error parsing Housing.com article: {str(e)}")
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.error(f"Error scraping Housing.com: {str(e)}")
        
        return articles
    
    def scrape_all(self) -> pd.DataFrame:
        """Scrape from all sources and return as DataFrame"""
        all_articles = []
        
        logger.info("Starting news scraping...")
        
        # Scrape RSS feeds
        rss_articles = self.scrape_rss_feeds()
        all_articles.extend(rss_articles)
        logger.info(f"Fetched {len(rss_articles)} articles from RSS feeds")
        
        # Scrape Housing.com (commented out if it fails)
        try:
            housing_articles = self.scrape_housing_news()
            all_articles.extend(housing_articles)
            logger.info(f"Fetched {len(housing_articles)} articles from Housing.com")
        except Exception as e:
            logger.warning(f"Could not scrape Housing.com: {str(e)}")
        
        # Remove duplicates based on title
        unique_articles = []
        seen_titles = set()
        
        for article in all_articles:
            if article and article['title'] not in seen_titles:
                seen_titles.add(article['title'])
                unique_articles.append(article)
        
        logger.info(f"Total unique articles: {len(unique_articles)}")
        
        # Convert to DataFrame
        df = pd.DataFrame(unique_articles)
        
        # Sort by date (newest first)
        if not df.empty:
            df = df.sort_values('date', ascending=False)
        
        return df


def main():
    """Main function to scrape and save news"""
    scraper = RealEstateNewsScraper()
    
    # Scrape all sources
    df = scraper.scrape_all()
    
    if not df.empty:
        # Save to CSV (project-level Datasets folder)
        output_path = os.path.join('..', 'Datasets', 'real_estate_news_live.csv')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(df)} articles to {output_path}")
        
        # Display sample
        print("\n" + "="*80)
        print(f"Scraped {len(df)} real estate news articles")
        print("="*80)
        print("\nSample articles:")
        print(df[['title', 'source', 'location', 'impact_score']].head(10).to_string())
        print("\n" + "="*80)
        
        return df
    else:
        logger.warning("No articles were scraped!")
        return None


if __name__ == "__main__":
    main()
