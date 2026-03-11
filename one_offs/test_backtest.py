"""
TrendSignal - TEST Backtest (Today Only)
Test simulation on a small set of signals

Version: 1.0 - Test mode
Date: 2026-02-17
"""

from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import or_
import logging

from src.models import Signal, SimulatedTrade
from src.trade_manager import TradeManager
from src.exceptions import InsufficientDataError, InvalidSignalError, PositionAlreadyExistsError

logger = logging.getLogger(__name__)


class TestBacktest:
    """Simple test backtest for debugging"""
    
    def __init__(self, db: Session):
        self.db = db
        self.trade_manager = TradeManager(db)
    
    def run_test(self, date: str = "2026-02-17") -> Dict:
        """
        Test backtest on one day's signals.
        
        Args:
            date: Date to process (YYYY-MM-DD)
        
        Returns:
            Stats dict
        """
        logger.info("=" * 70)
        logger.info(f"🧪 TEST BACKTEST - {date}")
        logger.info("=" * 70)
        
        # Get today's NON-NEUTRAL signals
        date_start = datetime.strptime(date, "%Y-%m-%d")
        date_end = date_start + timedelta(days=1)
        
        signals = self.db.query(Signal).filter(
            Signal.created_at >= date_start,
            Signal.created_at < date_end,
            or_(Signal.combined_score >= 25, Signal.combined_score <= -25)
        ).order_by(Signal.created_at).all()
        
        logger.info(f"Found {len(signals)} NON-NEUTRAL signals on {date}")
        
        if not signals:
            logger.warning("No signals found!")
            return {'total': 0}
        
        # Show signals
        logger.info("\nSignals:")
        for sig in signals:
            logger.info(
                f"  #{sig.id:4d} {sig.ticker_symbol:8s} "
                f"@ {sig.created_at} UTC | Score: {sig.combined_score:+6.2f}"
            )
        
        # Process each signal
        stats = {
            'total': len(signals),
            'opened': 0,
            'skip_no_data': 0,
            'skip_invalid': 0,
            'skip_duplicate': 0,
            'errors': []
        }
        
        logger.info("\n" + "=" * 70)
        logger.info("Processing signals...")
        logger.info("=" * 70)
        
        for i, signal in enumerate(signals, 1):
            logger.info(f"\n[{i}/{len(signals)}] Signal #{signal.id} - {signal.ticker_symbol}")
            
            try:
                # Check existing trade
                existing = self.db.query(SimulatedTrade).filter(
                    SimulatedTrade.entry_signal_id == signal.id
                ).first()
                
                if existing:
                    logger.info(f"   ⏭️  SKIP: Trade already exists (trade_id={existing.id})")
                    stats['skip_duplicate'] += 1
                    continue
                
                # Try to open position
                trade = self.trade_manager.open_position(signal)
                
                if trade:
                    self.db.flush()
                    logger.info(f"   ✅ OPENED: Trade #{trade.id}")
                    stats['opened'] += 1
                else:
                    logger.warning(f"   ⚠️  SKIP: Could not open")
                    stats['skip_invalid'] += 1
            
            except InsufficientDataError as e:
                logger.info(f"   ⏭️  SKIP: {e}")
                stats['skip_no_data'] += 1
            
            except InvalidSignalError as e:
                logger.info(f"   ⏭️  SKIP: {e}")
                stats['skip_invalid'] += 1
            
            except PositionAlreadyExistsError as e:
                logger.info(f"   ⏭️  SKIP: {e}")
                stats['skip_duplicate'] += 1
            
            except Exception as e:
                logger.error(f"   ❌ ERROR: {e}")
                stats['errors'].append({
                    'signal_id': signal.id,
                    'symbol': signal.ticker_symbol,
                    'error': str(e)
                })
        
        # Commit
        self.db.commit()
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST RESULTS")
        logger.info("=" * 70)
        logger.info(f"Total signals:     {stats['total']}")
        logger.info(f"Opened:            {stats['opened']}")
        logger.info(f"Skip (no data):    {stats['skip_no_data']}")
        logger.info(f"Skip (invalid):    {stats['skip_invalid']}")
        logger.info(f"Skip (duplicate):  {stats['skip_duplicate']}")
        logger.info(f"Errors:            {len(stats['errors'])}")
        
        if stats['errors']:
            logger.info("\nErrors:")
            for err in stats['errors']:
                logger.info(f"  Signal {err['signal_id']} ({err['symbol']}): {err['error']}")
        
        logger.info("=" * 70)
        
        return stats
