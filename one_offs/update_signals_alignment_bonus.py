#!/usr/bin/env python3
"""
TrendSignal - Retroactive Alignment Bonus Update Script
Updates existing signals in database with alignment bonus logic
"""

import sqlite3
import json
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# Database path - IMPORTANT: Use one of these formats for Windows:
# Option 1: Raw string (r"...") - recommended
# DATABASE_PATH = r"C:\Users\ZsoltBalogh\OneDrive - R34DY Zrt\Dokumentumok\GitHub\trendsignal-mvp\trendsignal.db"
#
# Option 2: Forward slashes - also works on Windows
# DATABASE_PATH = "C:/Users/ZsoltBalogh/OneDrive - R34DY Zrt/Dokumentumok/GitHub/trendsignal-mvp/trendsignal.db"
#
# Option 3: Escaped backslashes
# DATABASE_PATH = "C:\\Users\\ZsoltBalogh\\OneDrive - R34DY Zrt\\Dokumentumok\\GitHub\\trendsignal-mvp\\trendsignal.db"

DATABASE_PATH = r"..\trendsignal.db"  # Relative path from one_offs folder
# Or use absolute path:
# DATABASE_PATH = r"C:\Users\ZsoltBalogh\OneDrive - R34DY Zrt\Dokumentumok\GitHub\trendsignal-mvp\trendsignal.db"

# Alignment thresholds
TR_TECH_THRESHOLD = 60
TR_RISK_THRESHOLD = 40
ST_SENT_THRESHOLD = 40
ST_TECH_THRESHOLD = 40
SR_SENT_THRESHOLD = 40
SR_RISK_THRESHOLD = 40

# Bonus values
BONUS_TR = 5
BONUS_ST = 5
BONUS_SR = 3
BONUS_ALL = 8

# Confidence boost (50% of score bonus)
CONF_BOOST_ALL = 0.04
CONF_BOOST_STRONG = 0.025
CONF_BOOST_WEAK = 0.015

# Strength thresholds
STRONG_SCORE = 55
MODERATE_SCORE = 35
WEAK_SCORE = 15
HOLD_ZONE = 15

STRONG_CONFIDENCE = 0.75
MODERATE_CONFIDENCE = 0.60

# ============================================================================
# FUNCTIONS
# ============================================================================

def calculate_alignment_bonus(sentiment_score, technical_score, risk_score):
    """
    Calculate alignment bonus using the same logic as signal_generator.py
    """
    # Check strength of each pair (absolute values)
    abs_sent = abs(sentiment_score)
    abs_tech = abs(technical_score)
    abs_risk = abs(risk_score)
    
    tr_strong = abs_tech > TR_TECH_THRESHOLD and abs_risk > TR_RISK_THRESHOLD
    st_strong = abs_sent > ST_SENT_THRESHOLD and abs_tech > ST_TECH_THRESHOLD
    sr_strong = abs_sent > SR_SENT_THRESHOLD and abs_risk > SR_RISK_THRESHOLD
    
    strong_pairs = sum([tr_strong, st_strong, sr_strong])
    
    # Calculate bonus magnitude
    if strong_pairs == 3:
        bonus_magnitude = BONUS_ALL
    elif strong_pairs == 1:
        if tr_strong:
            bonus_magnitude = BONUS_TR
        elif st_strong:
            bonus_magnitude = BONUS_ST
        elif sr_strong:
            bonus_magnitude = BONUS_SR
        else:
            bonus_magnitude = 0
    else:
        bonus_magnitude = 0
    
    # Apply in correct direction
    if sentiment_score > 0 and technical_score > 0 and risk_score > 0:
        return bonus_magnitude  # BUY
    elif sentiment_score < 0 and technical_score < 0 and risk_score < 0:
        return -bonus_magnitude  # SELL
    else:
        return 0  # Mixed


def calculate_confidence_boost(alignment_bonus):
    """
    Calculate confidence boost (50% of alignment magnitude)
    Always positive regardless of BUY/SELL
    """
    magnitude = abs(alignment_bonus)
    
    if magnitude == 8:
        return CONF_BOOST_ALL
    elif magnitude == 5:
        return CONF_BOOST_STRONG
    elif magnitude == 3:
        return CONF_BOOST_WEAK
    else:
        return 0.0


def determine_strength(combined_score, confidence):
    """
    Determine strength category based on score and confidence
    """
    if combined_score >= STRONG_SCORE and confidence >= STRONG_CONFIDENCE:
        return 'STRONG'
    elif combined_score >= MODERATE_SCORE and confidence >= MODERATE_CONFIDENCE:
        return 'MODERATE'
    elif combined_score >= WEAK_SCORE:
        return 'WEAK'
    elif combined_score <= -STRONG_SCORE and confidence >= STRONG_CONFIDENCE:
        return 'STRONG'
    elif combined_score <= -MODERATE_SCORE and confidence >= MODERATE_CONFIDENCE:
        return 'MODERATE'
    elif combined_score <= -WEAK_SCORE:
        return 'WEAK'
    else:
        return 'NEUTRAL'


# ============================================================================
# MAIN UPDATE SCRIPT
# ============================================================================

def main():
    # Connect to database
    db_path = Path(DATABASE_PATH)
    if not db_path.exists():
        print(f"❌ Database not found: {DATABASE_PATH}")
        print("Please adjust DATABASE_PATH in the script")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 80)
    print("TrendSignal - Retroactive Alignment Bonus Update")
    print("=" * 80)
    
    # Step 1: Add columns if they don't exist
    print("\n📋 Step 1: Adding temporary columns...")
    try:
        cursor.execute("ALTER TABLE signals ADD COLUMN alignment_bonus INTEGER DEFAULT 0")
        print("  ✅ Added alignment_bonus column")
    except sqlite3.OperationalError:
        print("  ⚠️  alignment_bonus column already exists")
    
    try:
        cursor.execute("ALTER TABLE signals ADD COLUMN confidence_boost REAL DEFAULT 0.0")
        print("  ✅ Added confidence_boost column")
    except sqlite3.OperationalError:
        print("  ⚠️  confidence_boost column already exists")
    
    try:
        cursor.execute("ALTER TABLE signals ADD COLUMN base_combined_score REAL")
        print("  ✅ Added base_combined_score column")
    except sqlite3.OperationalError:
        print("  ⚠️  base_combined_score column already exists")
    
    try:
        cursor.execute("ALTER TABLE signals ADD COLUMN base_confidence REAL")
        print("  ✅ Added base_confidence column")
    except sqlite3.OperationalError:
        print("  ⚠️  base_confidence column already exists")
    
    conn.commit()
    
    # Step 2: Fetch all signals
    print("\n📊 Step 2: Fetching signals...")
    
    cursor.execute("""
        SELECT id, ticker_symbol, 
               sentiment_score, technical_score, risk_score,
               sentiment_confidence, technical_confidence,
               weight_sentiment, weight_technical, weight_risk,
               combined_score, decision, strength, reasoning, risk_details
        FROM signals
    """)
    signals = cursor.fetchall()
    print(f"  ✅ Loaded {len(signals)} signals")
    
    # Step 3: Calculate alignment bonus for each signal
    print("\n🔄 Step 3: Calculating alignment bonuses...")
    
    updates = []
    stats = {"total": 0, "with_bonus": 0, "buy_aligned": 0, "sell_aligned": 0}
    
    for signal in signals:
        signal_id = signal['id']
        sent = signal['sentiment_score']
        tech = signal['technical_score']
        risk = signal['risk_score']
        
        sent_conf = signal['sentiment_confidence']
        tech_conf = signal['technical_confidence']
        
        # Extract risk_confidence from risk_details JSON
        try:
            risk_details_json = signal['risk_details']
            if risk_details_json:
                risk_details = json.loads(risk_details_json)
                risk_conf = risk_details.get('confidence', 0.5)
            else:
                risk_conf = 0.5
        except (json.JSONDecodeError, KeyError, TypeError):
            risk_conf = 0.5  # Default fallback
        
        w_sent = signal['weight_sentiment']
        w_tech = signal['weight_technical']
        w_risk = signal['weight_risk']
        
        # Calculate base scores
        base_score = sent * w_sent + tech * w_tech + risk * w_risk
        base_conf = sent_conf * w_sent + tech_conf * w_tech + risk_conf * w_risk
        
        # Calculate alignment bonus
        alignment_bonus = calculate_alignment_bonus(sent, tech, risk)
        confidence_boost = calculate_confidence_boost(alignment_bonus)
        
        # Calculate final values
        final_score = base_score + alignment_bonus
        final_conf = min(base_conf + confidence_boost, 0.95)
        
        # Determine new strength
        new_strength = determine_strength(final_score, final_conf)
        
        # Update reasoning JSON
        reasoning_json = signal['reasoning']
        if reasoning_json:
            try:
                reasoning = json.loads(reasoning_json)
                if alignment_bonus != 0:
                    reasoning['alignment_bonus'] = alignment_bonus
                if confidence_boost > 0:
                    reasoning['confidence_boost'] = confidence_boost
                reasoning_updated = json.dumps(reasoning)
            except:
                reasoning_updated = reasoning_json
        else:
            reasoning_updated = reasoning_json
        
        updates.append({
            'id': signal_id,
            'base_score': base_score,
            'base_conf': base_conf,
            'alignment_bonus': alignment_bonus,
            'confidence_boost': confidence_boost,
            'final_score': final_score,
            'final_conf': final_conf,
            'new_strength': new_strength,
            'reasoning': reasoning_updated
        })
        
        stats['total'] += 1
        if alignment_bonus != 0:
            stats['with_bonus'] += 1
            if alignment_bonus > 0:
                stats['buy_aligned'] += 1
            else:
                stats['sell_aligned'] += 1
    
    print(f"  ✅ Calculated bonuses for {stats['total']} signals")
    print(f"     - With alignment: {stats['with_bonus']} ({stats['with_bonus']/stats['total']*100:.1f}%)")
    print(f"       - BUY aligned:  {stats['buy_aligned']}")
    print(f"       - SELL aligned: {stats['sell_aligned']}")
    
    # Step 4: Apply updates
    print("\n💾 Step 4: Applying updates to database...")
    
    for update in updates:
        cursor.execute("""
            UPDATE signals
            SET base_combined_score = ?,
                base_confidence = ?,
                alignment_bonus = ?,
                confidence_boost = ?,
                combined_score = ?,
                strength = ?,
                reasoning = ?
            WHERE id = ?
        """, (
            update['base_score'],
            update['base_conf'],
            update['alignment_bonus'],
            update['confidence_boost'],
            update['final_score'],
            update['new_strength'],
            update['reasoning'],
            update['id']
        ))
    
    conn.commit()
    print(f"  ✅ Updated {len(updates)} signals")
    
    # Step 5: Verification
    print("\n✅ Step 5: Verification...")
    
    # Strength distribution
    cursor.execute("""
        SELECT strength, COUNT(*) as count
        FROM signals
        GROUP BY strength
        ORDER BY CASE strength
            WHEN 'STRONG' THEN 1
            WHEN 'MODERATE' THEN 2
            WHEN 'WEAK' THEN 3
            WHEN 'NEUTRAL' THEN 4
        END
    """)
    print("\n  Strength Distribution:")
    for row in cursor.fetchall():
        print(f"    {row['strength']:8s}: {row['count']:3d} ({row['count']/stats['total']*100:.1f}%)")
    
    # Alignment bonus distribution
    cursor.execute("""
        SELECT alignment_bonus, COUNT(*) as count
        FROM signals
        GROUP BY alignment_bonus
        ORDER BY alignment_bonus DESC
    """)
    print("\n  Alignment Bonus Distribution:")
    for row in cursor.fetchall():
        bonus = row['alignment_bonus']
        count = row['count']
        print(f"    {bonus:+3d}: {count:3d} ({count/stats['total']*100:.1f}%)")
    
    # Show top aligned signals
    cursor.execute("""
        SELECT ticker_symbol, combined_score, alignment_bonus, 
               base_confidence + confidence_boost as final_conf, strength
        FROM signals
        WHERE alignment_bonus != 0
        ORDER BY ABS(combined_score) DESC
        LIMIT 10
    """)
    print("\n  Top 10 Aligned Signals:")
    print(f"    {'Ticker':<10} {'Score':>8} {'Bonus':>6} {'Conf':>6} {'Strength':<10}")
    print(f"    {'-'*50}")
    for row in cursor.fetchall():
        print(f"    {row[0]:<10} {row[1]:>8.2f} {row[2]:>+6d} {row[3]:>6.1%} {row[4]:<10}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ UPDATE COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Verify the results look correct")
    print("2. Check a few signals manually in the UI")
    print("3. If satisfied, the temporary columns can be kept or dropped")
    print("4. Generate new signals to see the alignment bonus in action")


if __name__ == "__main__":
    main()
