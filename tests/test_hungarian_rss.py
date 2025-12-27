"""
Test Hungarian RSS News Collection
Quick test to verify Portfolio.hu RSS feeds work
"""

import feedparser
from datetime import datetime, timedelta

def test_portfolio_rss():
    """Test Portfolio.hu RSS feeds"""
    
    feeds = {
        'Befektetés': 'https://www.portfolio.hu/rss/befektetes.xml',
        'Bank': 'https://www.portfolio.hu/rss/bank.xml',
        'Gazdaság': 'https://www.portfolio.hu/rss/gazdasag.xml',
    }
    
    print("🇭🇺 Testing Portfolio.hu RSS Feeds\n")
    print("=" * 70)
    
    for name, url in feeds.items():
        print(f"\n📰 {name}: {url}")
        
        try:
            feed = feedparser.parse(url)
            
            if not feed.entries:
                print(f"  ⚠️ No entries found")
                continue
            
            print(f"  ✅ Found {len(feed.entries)} articles")
            
            # Show first 3
            for i, entry in enumerate(feed.entries[:3]):
                title = entry.get('title', 'N/A')
                pub_date = entry.get('published', 'N/A')
                
                print(f"\n  {i+1}. {title}")
                print(f"     Published: {pub_date}")
                
                # Check for BÉT company mentions
                text = f"{title}".lower()
                mentions = []
                if 'otp' in text:
                    mentions.append('OTP')
                if 'mol' in text:
                    mentions.append('MOL')
                if 'richter' in text:
                    mentions.append('Richter')
                if '4ig' in text:
                    mentions.append('4iG')
                
                if mentions:
                    print(f"     🎯 Mentions: {', '.join(mentions)}")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 70)


def test_otp_specific():
    """Test collecting OTP-specific news"""
    print("\n\n🎯 Testing OTP-Specific News Collection\n")
    print("=" * 70)
    
    feed = feedparser.parse('https://www.portfolio.hu/rss/befektetes.xml')
    
    otp_news = []
    for entry in feed.entries:
        title = entry.get('title', '')
        description = entry.get('description', '')
        text = f"{title} {description}".lower()
        
        # Check for OTP mention
        if 'otp' in text or 'bank' in text:
            otp_news.append({
                'title': title,
                'published': entry.get('published', 'N/A'),
                'url': entry.get('link', '')
            })
    
    print(f"\n✅ Found {len(otp_news)} OTP-related articles")
    
    for i, news in enumerate(otp_news[:5]):
        print(f"\n{i+1}. {news['title']}")
        print(f"   Published: {news['published']}")
        print(f"   URL: {news['url'][:60]}...")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\nInstall feedparser first if needed:")
    print("!pip install feedparser --quiet\n")
    
    test_portfolio_rss()
    test_otp_specific()
