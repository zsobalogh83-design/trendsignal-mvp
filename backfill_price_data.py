"""
TrendSignal - Historical Price Data Backfill Script
Downloads and stores 5-minute candles for all active tickers

Usage:
    python backfill_price_data.py --days 60 --interval 5m
    python backfill_price_data.py --from 2026-01-01 --to 2026-02-17

Version: 1.0
Date: 2026-02-17
"""

import sys
import io

# Force UTF-8 stdout/stderr on Windows (needed for emoji in database.py prints)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import argparse
import logging
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import project modules - DIRECT imports to avoid src.__init__.py
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now import directly from modules (not through src package)
from database import SessionLocal
from models import Ticker, PriceData


class PriceDataBackfill:
    """Historical price data backfill manager"""
    
    def __init__(self, db: Session):
        """
        Initialize backfill manager.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_active_tickers(self) -> List[Ticker]:
        """
        Get all active tickers from database.
        
        Returns:
            List of Ticker objects where is_active=True
        """
        tickers = self.db.query(Ticker).filter(
            Ticker.is_active == True
        ).all()
        
        logger.info(f"Found {len(tickers)} active tickers")
        return tickers
    
    def backfill_ticker(
        self,
        ticker: Ticker,
        start_date: datetime,
        end_date: datetime,
        interval: str = "5m"
    ) -> int:
        """
        Backfill price data for a single ticker.
        
        Args:
            ticker: Ticker object
            start_date: Start date for backfill
            end_date: End date for backfill
            interval: Price interval ('5m', '15m', '1h', '1d')
        
        Returns:
            Number of candles inserted
        """
        symbol = ticker.symbol
        logger.info(f"📊 Backfilling {symbol} from {start_date.date()} to {end_date.date()}")
        
        try:
            # Download data from yfinance
            yf_ticker = yf.Ticker(symbol)
            df = yf_ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            
            if df.empty:
                logger.warning(f"⚠️  No data returned for {symbol}")
                return 0
            
            # Convert index to timezone-naive UTC
            # yfinance returns ET for US stocks, CET for BÉT - must convert to UTC first
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_convert('UTC').tz_localize(None)
            # else: already naive (shouldn't happen), leave as-is
            
            logger.info(f"   Downloaded {len(df)} candles")
            
            # Filter out candles that already exist in DB
            existing_timestamps = self._get_existing_timestamps(
                ticker.id,
                symbol,
                interval,
                start_date,
                end_date
            )
            
            # Filter DataFrame to only new candles
            df_filtered = df[~df.index.isin(existing_timestamps)]
            
            if df_filtered.empty:
                logger.info(f"   ✓ All candles already exist in DB")
                return 0
            
            logger.info(f"   Inserting {len(df_filtered)} new candles (skipping {len(df) - len(df_filtered)} existing)")
            
            # Insert new candles
            inserted_count = 0
            for timestamp, row in df_filtered.iterrows():
                try:
                    # Calculate price change
                    price_change = None
                    price_change_pct = None
                    
                    if row['Open'] != 0:
                        price_change = row['Close'] - row['Open']
                        price_change_pct = (price_change / row['Open']) * 100
                    
                    # Create PriceData record
                    price_data = PriceData(
                        ticker_id=ticker.id,
                        ticker_symbol=symbol,
                        timestamp=timestamp,
                        interval=interval,
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume']),
                        price_change=price_change,
                        price_change_pct=price_change_pct
                    )
                    
                    self.db.add(price_data)
                    inserted_count += 1
                    
                    # Commit in batches of 100
                    if inserted_count % 100 == 0:
                        self.db.commit()
                        logger.info(f"   ... {inserted_count} candles committed")
                
                except Exception as e:
                    logger.error(f"   ❌ Error inserting candle at {timestamp}: {e}")
                    continue
            
            # Final commit
            self.db.commit()
            logger.info(f"   ✅ {symbol}: {inserted_count} candles inserted")
            
            return inserted_count
        
        except Exception as e:
            logger.error(f"❌ Error backfilling {symbol}: {e}")
            self.db.rollback()
            return 0
    
    def _get_existing_timestamps(
        self,
        ticker_id: int,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: datetime
    ) -> set:
        """
        Get existing timestamps from database for deduplication.
        
        Args:
            ticker_id: Ticker ID
            symbol: Ticker symbol
            interval: Price interval
            start_date: Start date
            end_date: End date
        
        Returns:
            Set of existing timestamps
        """
        existing = self.db.query(PriceData.timestamp).filter(
            and_(
                PriceData.ticker_symbol == symbol,
                PriceData.interval == interval,
                PriceData.timestamp >= start_date,
                PriceData.timestamp <= end_date
            )
        ).all()
        
        return set(row[0] for row in existing)
    
    def backfill_all_tickers(
        self,
        start_date: datetime,
        end_date: datetime,
        interval: str = "5m"
    ) -> dict:
        """
        Backfill all active tickers.
        
        Args:
            start_date: Start date for backfill
            end_date: End date for backfill
            interval: Price interval
        
        Returns:
            Summary dict with statistics
        """
        tickers = self.get_active_tickers()
        
        summary = {
            'total_tickers': len(tickers),
            'successful': 0,
            'failed': 0,
            'total_candles': 0,
            'details': {}
        }
        
        for ticker in tickers:
            try:
                candles = self.backfill_ticker(ticker, start_date, end_date, interval)
                summary['successful'] += 1
                summary['total_candles'] += candles
                summary['details'][ticker.symbol] = {
                    'status': 'success',
                    'candles': candles
                }
            except Exception as e:
                logger.error(f"❌ Failed to backfill {ticker.symbol}: {e}")
                summary['failed'] += 1
                summary['details'][ticker.symbol] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return summary
    
    def get_backfill_date_range(self, lookback_days: Optional[int] = None) -> tuple[datetime, datetime]:
        """
        Calculate optimal backfill date range.
        
        Args:
            lookback_days: Number of days to look back (default: find oldest signal)
        
        Returns:
            (start_date, end_date)
        """
        end_date = datetime.now()
        
        if lookback_days:
            start_date = end_date - timedelta(days=lookback_days)
        else:
            # Find oldest signal in database
            from models import Signal
            oldest_signal = self.db.query(Signal).order_by(Signal.created_at.asc()).first()
            
            if oldest_signal:
                # Start from 1 day before oldest signal to ensure coverage
                start_date = oldest_signal.created_at - timedelta(days=1)
                logger.info(f"📅 Oldest signal: {oldest_signal.created_at.date()}")
            else:
                # No signals yet, default to 60 days
                start_date = end_date - timedelta(days=60)
                logger.info(f"📅 No signals found, using 60-day default")
        
        return start_date, end_date


def main():
    """Main backfill execution"""
    
    parser = argparse.ArgumentParser(
        description='Backfill historical price data for TrendSignal'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        help='Number of days to look back (default: auto-detect from oldest signal)'
    )
    
    parser.add_argument(
        '--from',
        dest='from_date',
        type=str,
        help='Start date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--to',
        dest='to_date',
        type=str,
        help='End date (YYYY-MM-DD format, default: today)'
    )
    
    parser.add_argument(
        '--interval',
        type=str,
        default='5m',
        choices=['5m', '15m', '1h', '1d'],
        help='Price interval (default: 5m)'
    )
    
    parser.add_argument(
        '--ticker',
        type=str,
        help='Specific ticker symbol (optional, default: all active tickers)'
    )
    
    args = parser.parse_args()
    
    # Create database session
    db = SessionLocal()
    backfill = PriceDataBackfill(db)
    
    try:
        # Determine date range
        if args.from_date and args.to_date:
            start_date = datetime.strptime(args.from_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.to_date, '%Y-%m-%d')
        elif args.days:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=args.days)
        else:
            start_date, end_date = backfill.get_backfill_date_range()
        
        print("\n" + "="*70)
        print("📊 TrendSignal - Price Data Backfill")
        print("="*70)
        print(f"Start Date:    {start_date.date()}")
        print(f"End Date:      {end_date.date()}")
        print(f"Interval:      {args.interval}")
        print(f"Ticker Filter: {args.ticker or 'All active tickers'}")
        print("="*70 + "\n")
        
        # Execute backfill
        if args.ticker:
            # Single ticker backfill
            ticker = db.query(Ticker).filter(Ticker.symbol == args.ticker).first()
            if not ticker:
                logger.error(f"❌ Ticker {args.ticker} not found in database")
                return
            
            candles = backfill.backfill_ticker(ticker, start_date, end_date, args.interval)
            
            print("\n" + "="*70)
            print(f"✅ Backfill Complete: {args.ticker}")
            print(f"   Candles inserted: {candles}")
            print("="*70 + "\n")
        
        else:
            # All tickers backfill
            summary = backfill.backfill_all_tickers(start_date, end_date, args.interval)
            
            print("\n" + "="*70)
            print("✅ Backfill Complete - Summary")
            print("="*70)
            print(f"Total Tickers:    {summary['total_tickers']}")
            print(f"Successful:       {summary['successful']}")
            print(f"Failed:           {summary['failed']}")
            print(f"Total Candles:    {summary['total_candles']}")
            print("\nDetails by Ticker:")
            print("-"*70)
            
            for symbol, details in summary['details'].items():
                status_emoji = "✅" if details['status'] == 'success' else "❌"
                if details['status'] == 'success':
                    print(f"{status_emoji} {symbol:10s} - {details['candles']:>6,} candles")
                else:
                    print(f"{status_emoji} {symbol:10s} - ERROR: {details['error']}")
            
            print("="*70 + "\n")
    
    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}")
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
