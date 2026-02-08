"""
TrendSignal - Telegram Alerter Service
Sends Telegram notifications for strong trading signals

Version: 1.0
Date: 2025-02-08
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json
from pathlib import Path
from config import get_config


class TelegramAlerter:
    """
    Telegram notification system for strong trading signals
    
    Features:
    - Sends alerts when |combined_score| > threshold (default: 30)
    - Rate limiting (max alerts per hour)
    - Rich message formatting with scores, S/R levels
    - Optional top news headlines
    - Optional link to TrendSignal UI
    """
    
    def __init__(self):
        """Initialize Telegram alerter with config"""
        self.config = get_config()
        self.bot_token = self.config.telegram_bot_token
        self.chat_id = self.config.telegram_chat_id
        self.enabled = self.config.telegram_alerts_enabled
        self.score_threshold = self.config.telegram_score_threshold
        self.max_per_hour = self.config.telegram_max_alerts_per_hour
        self.include_news = self.config.telegram_include_news
        self.include_link = self.config.telegram_include_link
        
        # Rate limiting tracker
        self.last_sent_times: List[datetime] = []
        
        # ✅ NEW: Daily watermark tracker per ticker (persisted to file)
        # Format: {ticker_symbol: (highest_abs_score, datetime)}
        # Only send alert if score crosses a NEW threshold (30, 35, 65)
        self.watermark_file = Path(__file__).parent.parent / "telegram_watermarks.json"
        self.daily_watermark: Dict[str, tuple] = self._load_watermarks()
        
        # Validate configuration
        if self.enabled and (not self.bot_token or not self.chat_id):
            print("⚠️ Telegram alerts enabled but bot_token or chat_id missing!")
            self.enabled = False
    
    def should_send_alert(self, signal) -> bool:
        """
        Determine if alert should be sent for this signal
        
        Rules:
        - Alert when |combined_score| > 30 (first time crossing)
        - Alert when crossing thresholds: 30, 35, 65 (upward only)
        - NO alert if score stays in same range or goes down
        - Daily watermark: track highest score reached today per ticker
        
        Examples:
        - 28 → 31: Alert (crossed 30)
        - 31 → 34: No alert (same range 30-34)
        - 34 → 36: Alert (crossed 35)
        - 36 → 38: No alert (same range 35+)
        - 38 → 32: No alert (went down)
        - 32 → 36: No alert (already was at 36 today)
        - 36 → 66: Alert (crossed 65)
        
        Args:
            signal: Signal object with combined_score attribute
        
        Returns:
            bool: True if alert should be sent
        """
        # 1. Check if alerts are enabled
        if not self.enabled:
            return False
        
        # 2. Check score threshold
        abs_score = abs(signal.combined_score)
        
        if abs_score <= self.score_threshold:
            return False
        
        # 3. Define thresholds (absolute values)
        thresholds = [30, 35, 65]
        
        # 4. Determine which threshold range current score is in
        def get_threshold_level(score):
            """Returns the highest threshold crossed by this score"""
            for t in reversed(thresholds):
                if score >= t:
                    return t
            return 0
        
        current_level = get_threshold_level(abs_score)
        ticker_symbol = signal.ticker_symbol
        
        # 5. Check daily watermark
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        should_alert = False
        
        if ticker_symbol in self.daily_watermark:
            highest_score, last_time = self.daily_watermark[ticker_symbol]
            
            # Reset watermark if it was from a previous day
            if last_time < today_start:
                # New day, reset watermark
                self.daily_watermark[ticker_symbol] = (abs_score, datetime.now())
                print(f"🔄 Telegram watermark reset for {ticker_symbol}: {abs_score:.1f}")
                should_alert = True
            else:
                # Same day - check if crossed a new threshold
                previous_level = get_threshold_level(highest_score)
                
                if current_level > previous_level:
                    # Crossed a new threshold upward
                    print(f"📈 Telegram threshold crossed: {ticker_symbol} {previous_level} → {current_level}")
                    should_alert = True
                else:
                    # Same or lower level - skip
                    print(f"⏭️  Telegram alert skipped: {ticker_symbol} score {abs_score:.1f} (watermark: {highest_score:.1f}, level: {current_level})")
                    should_alert = False
                
                # ✅ IMPORTANT: Update watermark to highest score seen today (even if no alert)
                self.daily_watermark[ticker_symbol] = (max(highest_score, abs_score), datetime.now())
                
                # Save to file
                self._save_watermarks()
        else:
            # First time seeing this ticker today
            self.daily_watermark[ticker_symbol] = (abs_score, datetime.now())
            print(f"🆕 Telegram first alert: {ticker_symbol} score {abs_score:.1f}")
            should_alert = True
            
            # Save to file
            self._save_watermarks()
        
        if not should_alert:
            return False
        
        # 6. Rate limiting check (global hourly limit)
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Remove old entries
        self.last_sent_times = [t for t in self.last_sent_times if t > one_hour_ago]
        
        # Check if limit reached
        if len(self.last_sent_times) >= self.max_per_hour:
            print(f"⚠️ Telegram rate limit reached: {len(self.last_sent_times)}/{self.max_per_hour} per hour")
            return False
        
        return True
    
    def send_alert(self, signal, news_items: Optional[List] = None):
        """
        Send Telegram alert for signal
        
        Args:
            signal: Signal object
            news_items: Optional list of News objects (top 3 will be used)
        """
        if not self.should_send_alert(signal):
            return
        
        try:
            # Create message
            message = self._create_message(signal, news_items)
            
            # Send via Telegram API
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",  # Enable formatting
                "disable_web_page_preview": True  # Don't show link previews
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                # Track successful send
                self.last_sent_times.append(datetime.now())
                
                # Log sent alert
                abs_score = abs(signal.combined_score)
                direction = "BUY" if signal.combined_score > 0 else "SELL"
                strength = "STRONG" if abs_score >= 65 else "MODERATE"
                
                print(f"✅ Telegram alert sent: {signal.ticker_symbol} {strength}_{direction} (score: {signal.combined_score:.1f})")
            else:
                data = response.json()
                print(f"❌ Telegram API error: {data.get('description', 'Unknown error')}")
        
        except requests.exceptions.Timeout:
            print("❌ Telegram request timeout")
        except requests.exceptions.RequestException as e:
            print(f"❌ Telegram network error: {e}")
        except Exception as e:
            print(f"❌ Telegram alert error: {e}")
    
    def _create_message(self, signal, news_items: Optional[List] = None) -> str:
        """
        Create formatted Telegram message
        
        Args:
            signal: Signal object
            news_items: Optional list of News objects
        
        Returns:
            str: Formatted message with Markdown
        """
        # Determine direction and emoji
        if signal.combined_score > 0:
            direction = "🟢 *STRONG BUY*"
            direction_text = "BUY"
        else:
            direction = "🔴 *STRONG SELL*"
            direction_text = "SELL"
        
        # Build message parts
        parts = [
            "🚨 *TrendSignal Alert*",
            "",
            direction,
            f"*{signal.ticker_symbol}*",
            "",
            f"📊 *Score:* {signal.combined_score:.1f}",
            f"├─ Sentiment: {signal.sentiment_score:.1f}",
            f"├─ Technical: {signal.technical_score:.1f}",
            f"└─ Risk: {signal.risk_score:.1f}",
            "",
            f"🎯 *Confidence:* {signal.overall_confidence:.2f}",
            "",
        ]
        
        # Add stop-loss and take-profit
        if hasattr(signal, 'stop_loss') and signal.stop_loss:
            parts.append(f"💰 *Stop Loss:* ${signal.stop_loss:.2f}")
        
        if hasattr(signal, 'take_profit') and signal.take_profit:
            parts.append(f"💰 *Take Profit:* ${signal.take_profit:.2f}")
        
        parts.append("")
        
        # Add news headlines if available and enabled
        if self.include_news and news_items:
            parts.append("📰 *Top News:*")
            for i, news in enumerate(news_items[:3], 1):
                # Escape markdown special characters in title
                title = news.title.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[')
                sentiment_emoji = "🟢" if news.sentiment_score > 0.2 else ("🔴" if news.sentiment_score < -0.2 else "⚪")
                parts.append(f"{i}. {sentiment_emoji} {title[:80]}{'...' if len(title) > 80 else ''}")
            parts.append("")
        
        # Add link to UI if enabled
        if self.include_link:
            # You can customize this URL based on your actual frontend URL
            ui_url = f"http://localhost:5173/signals/{signal.ticker_symbol}"
            parts.append(f"[📊 View Signal Details]({ui_url})")
            parts.append("")
        
        # Add timestamp
        timestamp = signal.generated_at.strftime('%Y-%m-%d %H:%M') if hasattr(signal, 'generated_at') else datetime.now().strftime('%Y-%m-%d %H:%M')
        parts.append(f"⏰ {timestamp}")
        
        return "\n".join(parts)
    
    def _load_watermarks(self) -> Dict[str, tuple]:
        """
        Load watermarks from JSON file
        
        Returns:
            Dict with ticker watermarks, empty dict if file doesn't exist
        """
        if not self.watermark_file.exists():
            return {}
        
        try:
            with open(self.watermark_file, 'r') as f:
                data = json.load(f)
            
            # Convert ISO datetime strings back to datetime objects
            watermarks = {}
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            for ticker, (score, dt_str) in data.items():
                dt = datetime.fromisoformat(dt_str)
                
                # Only keep today's watermarks
                if dt >= today_start:
                    watermarks[ticker] = (score, dt)
            
            if watermarks:
                print(f"📂 Loaded {len(watermarks)} Telegram watermarks from file")
            
            return watermarks
        
        except Exception as e:
            print(f"⚠️ Failed to load Telegram watermarks: {e}")
            return {}
    
    def _save_watermarks(self):
        """
        Save watermarks to JSON file
        """
        try:
            # Convert datetime objects to ISO strings for JSON
            data = {
                ticker: (score, dt.isoformat())
                for ticker, (score, dt) in self.daily_watermark.items()
            }
            
            with open(self.watermark_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            print(f"⚠️ Failed to save Telegram watermarks: {e}")
    
    def send_test_message(self) -> bool:
        """
        Send a test message to verify configuration
        
        Returns:
            bool: True if test successful
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": "✅ TrendSignal Telegram Alert Test\n\nConfiguration is working correctly!",
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✅ Telegram test message sent successfully!")
                return True
            else:
                data = response.json()
                print(f"❌ Test failed: {data.get('description', 'Unknown error')}")
                return False
        
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_telegram_alerter() -> TelegramAlerter:
    """Get singleton Telegram alerter instance"""
    return TelegramAlerter()


def send_signal_alert(signal, news_items: Optional[List] = None):
    """
    Convenience function to send alert for signal
    
    Usage:
        from telegram_alerter import send_signal_alert
        send_signal_alert(signal, news_items)
    
    Args:
        signal: Signal object
        news_items: Optional list of News objects
    """
    alerter = get_telegram_alerter()
    alerter.send_alert(signal, news_items)


# ==========================================
# INTEGRATION POINT
# ==========================================

def integrate_with_signal_generator(signal, news_items: Optional[List] = None):
    """
    Integration function to be called from signal_generator.py
    
    Add this to signal_generator.py after signal generation:
    
    ```python
    # Import at top
    from telegram_alerter import integrate_with_signal_generator
    
    # After signal generation and db.commit()
    signal = Signal(...)
    db.add(signal)
    db.commit()
    
    # Send Telegram alert if strong signal
    integrate_with_signal_generator(signal, recent_news)
    ```
    
    Args:
        signal: Generated Signal object
        news_items: List of News objects used in signal generation
    """
    try:
        alerter = get_telegram_alerter()
        
        if alerter.enabled and abs(signal.combined_score) > alerter.score_threshold:
            alerter.send_alert(signal, news_items)
    
    except Exception as e:
        # Don't fail signal generation if alert fails
        print(f"⚠️ Telegram alert skipped: {e}")


if __name__ == "__main__":
    """Test Telegram alerter"""
    print("=" * 60)
    print("Telegram Alerter Test")
    print("=" * 60)
    print()
    
    alerter = TelegramAlerter()
    
    print("Configuration:")
    print(f"  Enabled: {alerter.enabled}")
    print(f"  Bot Token: {alerter.bot_token[:20]}..." if alerter.bot_token else "  Bot Token: Not set")
    print(f"  Chat ID: {alerter.chat_id}")
    print(f"  Score Threshold: {alerter.score_threshold}")
    print(f"  Max Alerts/Hour: {alerter.max_per_hour}")
    print()
    
    if alerter.enabled:
        print("Sending test message...")
        success = alerter.send_test_message()
        
        if success:
            print("✅ Configuration is working!")
        else:
            print("❌ Configuration has issues, check bot token and chat ID")
    else:
        print("⚠️ Telegram alerts are disabled")
    
    print()
    print("=" * 60)
