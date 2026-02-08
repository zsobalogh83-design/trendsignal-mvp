#!/usr/bin/env python3
"""
TrendSignal - Alignment Bonus Update from CSV Export
Reads signals2.csv and generates UPDATE statements
"""

import pandas as pd
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

CSV_PATH = "signals2.csv"  # The exported signal_calculations CSV

# Alignment thresholds
TR_TECH = 60
TR_RISK = 40
ST_SENT = 40
ST_TECH = 40
SR_SENT = 40
SR_RISK = 40

# Strength thresholds (conservative)
STRONG_SCORE = 55
MODERATE_SCORE = 35
WEAK_SCORE = 15

STRONG_CONF = 0.75
MODERATE_CONF = 0.60

# ============================================================================
# FUNCTIONS
# ============================================================================

def calc_alignment_bonus(sent, tech, risk):
    """Calculate alignment bonus"""
    abs_sent, abs_tech, abs_risk = abs(sent), abs(tech), abs(risk)
    
    tr = abs_tech > TR_TECH and abs_risk > TR_RISK
    st = abs_sent > ST_SENT and abs_tech > ST_TECH
    sr = abs_sent > SR_SENT and abs_risk > SR_RISK
    
    pairs = sum([tr, st, sr])
    
    if pairs == 3:
        mag = 8
    elif pairs == 1:
        mag = 5 if (tr or st) else 3
    else:
        mag = 0
    
    if sent > 0 and tech > 0 and risk > 0:
        return mag
    elif sent < 0 and tech < 0 and risk < 0:
        return -mag
    return 0


def calc_conf_boost(bonus):
    """Calculate confidence boost"""
    mag = abs(bonus)
    if mag == 8: return 0.04
    elif mag == 5: return 0.025
    elif mag == 3: return 0.015
    return 0.0


def calc_strength(score, conf):
    """Determine strength"""
    if score >= STRONG_SCORE and conf >= STRONG_CONF:
        return 'STRONG'
    elif score >= MODERATE_SCORE and conf >= MODERATE_CONF:
        return 'MODERATE'
    elif score >= WEAK_SCORE:
        return 'WEAK'
    elif score <= -STRONG_SCORE and conf >= STRONG_CONF:
        return 'STRONG'
    elif score <= -MODERATE_SCORE and conf >= MODERATE_CONF:
        return 'MODERATE'
    elif score <= -WEAK_SCORE:
        return 'WEAK'
    return 'NEUTRAL'


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("TrendSignal - Alignment Bonus Calculation from CSV")
    print("=" * 80)
    
    # Load CSV
    print(f"\n📂 Loading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    print(f"  ✅ Loaded {len(df)} signals")
    
    # Calculate alignment for each row
    print("\n🔄 Calculating alignment bonuses...")
    
    results = []
    
    for idx, row in df.iterrows():
        # Get values
        signal_id = row['signal_id']
        sent = row['sentiment_score']
        tech = row['technical_score']
        risk = row['risk_score']
        
        sent_conf = row['sentiment_confidence']
        tech_conf = row['technical_confidence']
        risk_conf = row['risk_confidence']
        
        w_sent = row['weight_sentiment']
        w_tech = row['weight_technical']
        w_risk = row['weight_risk']
        
        # Calculate base scores
        base_score = sent * w_sent + tech * w_tech + risk * w_risk
        base_conf = sent_conf * w_sent + tech_conf * w_tech + risk_conf * w_risk
        
        # Calculate bonuses
        alignment_bonus = calc_alignment_bonus(sent, tech, risk)
        conf_boost = calc_conf_boost(alignment_bonus)
        
        # Final values
        final_score = base_score + alignment_bonus
        final_conf = min(base_conf + conf_boost, 0.95)
        
        # New strength
        new_strength = calc_strength(final_score, final_conf)
        
        results.append({
            'signal_id': signal_id,
            'ticker': row['ticker_symbol'],
            'base_score': round(base_score, 2),
            'alignment_bonus': alignment_bonus,
            'final_score': round(final_score, 2),
            'base_conf': round(base_conf, 4),
            'conf_boost': round(conf_boost, 4),
            'final_conf': round(final_conf, 4),
            'old_strength': row['strength'],
            'new_strength': new_strength
        })
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    print(f"  ✅ Calculated bonuses for {len(results_df)} signals")
    
    # Statistics
    print("\n📊 Statistics:")
    print(f"  Signals with alignment bonus: {len(results_df[results_df['alignment_bonus'] != 0])} ({len(results_df[results_df['alignment_bonus'] != 0])/len(results_df)*100:.1f}%)")
    print(f"    - BUY aligned (+):  {len(results_df[results_df['alignment_bonus'] > 0])}")
    print(f"    - SELL aligned (-): {len(results_df[results_df['alignment_bonus'] < 0])}")
    
    print("\n  Alignment bonus distribution:")
    bonus_dist = results_df['alignment_bonus'].value_counts().sort_index(ascending=False)
    for bonus, count in bonus_dist.items():
        if bonus != 0:
            print(f"    {bonus:+3d}: {count:3d} ({count/len(results_df)*100:.1f}%)")
    
    print("\n  Strength changes:")
    strength_changes = results_df[results_df['old_strength'] != results_df['new_strength']]
    print(f"    Changed: {len(strength_changes)} signals")
    if len(strength_changes) > 0:
        for _, row in strength_changes.groupby(['old_strength', 'new_strength']).size().items():
            print(f"      {_[0]} → {_[1]}: {row}")
    
    print("\n  New strength distribution:")
    new_dist = results_df['new_strength'].value_counts()
    for strength in ['STRONG', 'MODERATE', 'WEAK', 'NEUTRAL']:
        count = new_dist.get(strength, 0)
        print(f"    {strength:8s}: {count:3d} ({count/len(results_df)*100:.1f}%)")
    
    # Show top aligned signals
    print("\n  Top 10 aligned signals:")
    top_aligned = results_df[results_df['alignment_bonus'] != 0].nlargest(10, 'final_score', keep='first')
    print(f"\n  {'Ticker':<10} {'Base':>7} {'Bonus':>6} {'Final':>7} {'B.Conf':>6} {'Boost':>6} {'F.Conf':>6} {'Strength':<10}")
    print(f"  {'-'*75}")
    for _, row in top_aligned.iterrows():
        print(f"  {row['ticker']:<10} {row['base_score']:>7.2f} {row['alignment_bonus']:>+6d} {row['final_score']:>7.2f} "
              f"{row['base_conf']:>6.3f} {row['conf_boost']:>+6.3f} {row['final_conf']:>6.3f} {row['new_strength']:<10}")
    
    # Generate SQL UPDATE statements
    print("\n" + "=" * 80)
    print("GENERATING SQL UPDATE STATEMENTS")
    print("=" * 80)
    
    # Save to file
    sql_file = "update_signals_from_csv.sql"
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write("-- ============================================================================\n")
        f.write("-- TrendSignal - Alignment Bonus UPDATE Statements\n")
        f.write("-- Generated from signal_calculations export\n")
        f.write("-- ============================================================================\n\n")
        
        f.write("-- Add columns if they don't exist\n")
        f.write("ALTER TABLE signals ADD COLUMN IF NOT EXISTS alignment_bonus INTEGER DEFAULT 0;\n")
        f.write("ALTER TABLE signals ADD COLUMN IF NOT EXISTS confidence_boost REAL DEFAULT 0.0;\n")
        f.write("ALTER TABLE signals ADD COLUMN IF NOT EXISTS base_combined_score REAL;\n")
        f.write("ALTER TABLE signals ADD COLUMN IF NOT EXISTS base_confidence REAL;\n\n")
        
        f.write("ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS alignment_bonus INTEGER DEFAULT 0;\n")
        f.write("ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS confidence_boost REAL DEFAULT 0.0;\n")
        f.write("ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS base_combined_score REAL;\n")
        f.write("ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS base_confidence REAL;\n\n")
        
        f.write("-- Begin transaction\n")
        f.write("BEGIN TRANSACTION;\n\n")
        
        # Generate UPDATE for each signal
        for _, row in results_df.iterrows():
            signal_id = row['signal_id']
            
            # Update signals table (by signal_id foreign key)
            f.write(f"-- Signal ID: {signal_id} ({row['ticker']})\n")
            f.write(f"UPDATE signals SET\n")
            f.write(f"  base_combined_score = {row['base_score']},\n")
            f.write(f"  alignment_bonus = {row['alignment_bonus']},\n")
            f.write(f"  combined_score = {row['final_score']},\n")
            f.write(f"  base_confidence = {row['base_conf']},\n")
            f.write(f"  confidence_boost = {row['conf_boost']},\n")
            f.write(f"  strength = '{row['new_strength']}'\n")
            f.write(f"WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = {signal_id} LIMIT 1);\n\n")
            
            # Update signal_calculations table
            f.write(f"UPDATE signal_calculations SET\n")
            f.write(f"  base_combined_score = {row['base_score']},\n")
            f.write(f"  alignment_bonus = {row['alignment_bonus']},\n")
            f.write(f"  combined_score = {row['final_score']},\n")
            f.write(f"  base_confidence = {row['base_conf']},\n")
            f.write(f"  confidence_boost = {row['conf_boost']},\n")
            f.write(f"  strength = '{row['new_strength']}'\n")
            f.write(f"WHERE signal_id = {signal_id};\n\n")
        
        f.write("-- Commit transaction\n")
        f.write("COMMIT;\n\n")
        
        f.write("-- Verification queries\n")
        f.write("SELECT strength, COUNT(*) as count FROM signals GROUP BY strength;\n")
        f.write("SELECT alignment_bonus, COUNT(*) FROM signal_calculations GROUP BY alignment_bonus ORDER BY alignment_bonus DESC;\n")
    
    print(f"  ✅ Generated SQL file: {sql_file}")
    print(f"     Total UPDATE statements: {len(results_df) * 2} (both tables)")
    
    # Also save results CSV
    results_csv = "alignment_bonus_results.csv"
    results_df.to_csv(results_csv, index=False)
    print(f"  ✅ Saved results: {results_csv}")
    
    print("\n" + "=" * 80)
    print("✅ DONE! Next steps:")
    print("=" * 80)
    print(f"1. Review {results_csv} to verify calculations")
    print(f"2. Open DB Browser for SQLite")
    print(f"3. Load and execute {sql_file}")
    print(f"4. Verify with the queries at the end of the SQL file")


if __name__ == "__main__":
    main()
