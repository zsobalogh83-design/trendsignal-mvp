-- ============================================================================
-- TrendSignal - Alignment Bonus UPDATE Statements
-- Generated from signal_calculations export
-- ============================================================================

-- Add columns if they don't exist
ALTER TABLE signals ADD COLUMN IF NOT EXISTS alignment_bonus INTEGER DEFAULT 0;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS confidence_boost REAL DEFAULT 0.0;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS base_combined_score REAL;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS base_confidence REAL;

ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS alignment_bonus INTEGER DEFAULT 0;
ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS confidence_boost REAL DEFAULT 0.0;
ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS base_combined_score REAL;
ALTER TABLE signal_calculations ADD COLUMN IF NOT EXISTS base_confidence REAL;

-- Begin transaction
BEGIN TRANSACTION;

-- Signal ID: 746 (IBM)
UPDATE signals SET
  base_combined_score = -0.54,
  alignment_bonus = 0,
  combined_score = -0.54,
  base_confidence = 0.8147,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 746 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.54,
  alignment_bonus = 0,
  combined_score = -0.54,
  base_confidence = 0.8147,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 746;

-- Signal ID: 745 (META)
UPDATE signals SET
  base_combined_score = -11.41,
  alignment_bonus = 0,
  combined_score = -11.41,
  base_confidence = 0.7918,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 745 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -11.41,
  alignment_bonus = 0,
  combined_score = -11.41,
  base_confidence = 0.7918,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 745;

-- Signal ID: 744 (AMZN)
UPDATE signals SET
  base_combined_score = -21.06,
  alignment_bonus = 0,
  combined_score = -21.06,
  base_confidence = 0.8153,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 744 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -21.06,
  alignment_bonus = 0,
  combined_score = -21.06,
  base_confidence = 0.8153,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 744;

-- Signal ID: 743 (NVDA)
UPDATE signals SET
  base_combined_score = 4.78,
  alignment_bonus = 0,
  combined_score = 4.78,
  base_confidence = 0.8178,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 743 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.78,
  alignment_bonus = 0,
  combined_score = 4.78,
  base_confidence = 0.8178,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 743;

-- Signal ID: 742 (MOL.BD)
UPDATE signals SET
  base_combined_score = 1.43,
  alignment_bonus = 0,
  combined_score = 1.43,
  base_confidence = 0.6525,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 742 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.43,
  alignment_bonus = 0,
  combined_score = 1.43,
  base_confidence = 0.6525,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 742;

-- Signal ID: 741 (OTP.BD)
UPDATE signals SET
  base_combined_score = 5.23,
  alignment_bonus = 0,
  combined_score = 5.23,
  base_confidence = 0.7185,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 741 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.23,
  alignment_bonus = 0,
  combined_score = 5.23,
  base_confidence = 0.7185,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 741;

-- Signal ID: 740 (TSLA)
UPDATE signals SET
  base_combined_score = -14.38,
  alignment_bonus = 0,
  combined_score = -14.38,
  base_confidence = 0.7755,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 740 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -14.38,
  alignment_bonus = 0,
  combined_score = -14.38,
  base_confidence = 0.7755,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 740;

-- Signal ID: 739 (GOOGL)
UPDATE signals SET
  base_combined_score = -11.86,
  alignment_bonus = 0,
  combined_score = -11.86,
  base_confidence = 0.7815,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 739 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -11.86,
  alignment_bonus = 0,
  combined_score = -11.86,
  base_confidence = 0.7815,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 739;

-- Signal ID: 738 (MSFT)
UPDATE signals SET
  base_combined_score = 1.8,
  alignment_bonus = 0,
  combined_score = 1.8,
  base_confidence = 0.7812,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 738 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.8,
  alignment_bonus = 0,
  combined_score = 1.8,
  base_confidence = 0.7812,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 738;

-- Signal ID: 737 (AAPL)
UPDATE signals SET
  base_combined_score = 5.72,
  alignment_bonus = 0,
  combined_score = 5.72,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 737 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.72,
  alignment_bonus = 0,
  combined_score = 5.72,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 737;

-- Signal ID: 736 (NVDA)
UPDATE signals SET
  base_combined_score = 1.46,
  alignment_bonus = 0,
  combined_score = 1.46,
  base_confidence = 0.799,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 736 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.46,
  alignment_bonus = 0,
  combined_score = 1.46,
  base_confidence = 0.799,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 736;

-- Signal ID: 735 (MSFT)
UPDATE signals SET
  base_combined_score = -2.32,
  alignment_bonus = 0,
  combined_score = -2.32,
  base_confidence = 0.7883,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 735 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.32,
  alignment_bonus = 0,
  combined_score = -2.32,
  base_confidence = 0.7883,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 735;

-- Signal ID: 734 (TSLA)
UPDATE signals SET
  base_combined_score = -14.95,
  alignment_bonus = 0,
  combined_score = -14.95,
  base_confidence = 0.7755,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 734 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -14.95,
  alignment_bonus = 0,
  combined_score = -14.95,
  base_confidence = 0.7755,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 734;

-- Signal ID: 733 (AAPL)
UPDATE signals SET
  base_combined_score = 19.01,
  alignment_bonus = 0,
  combined_score = 19.01,
  base_confidence = 0.7855,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 733 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 19.01,
  alignment_bonus = 0,
  combined_score = 19.01,
  base_confidence = 0.7855,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 733;

-- Signal ID: 732 (OTP.BD)
UPDATE signals SET
  base_combined_score = 12.69,
  alignment_bonus = 0,
  combined_score = 12.69,
  base_confidence = 0.7185,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 732 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.69,
  alignment_bonus = 0,
  combined_score = 12.69,
  base_confidence = 0.7185,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 732;

-- Signal ID: 731 (MOL.BD)
UPDATE signals SET
  base_combined_score = 13.07,
  alignment_bonus = 0,
  combined_score = 13.07,
  base_confidence = 0.74,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 731 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.07,
  alignment_bonus = 0,
  combined_score = 13.07,
  base_confidence = 0.74,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 731;

-- Signal ID: 730 (IBM)
UPDATE signals SET
  base_combined_score = -2.69,
  alignment_bonus = 0,
  combined_score = -2.69,
  base_confidence = 0.8147,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 730 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.69,
  alignment_bonus = 0,
  combined_score = -2.69,
  base_confidence = 0.8147,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 730;

-- Signal ID: 729 (META)
UPDATE signals SET
  base_combined_score = -11.21,
  alignment_bonus = 0,
  combined_score = -11.21,
  base_confidence = 0.7927,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 729 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -11.21,
  alignment_bonus = 0,
  combined_score = -11.21,
  base_confidence = 0.7927,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 729;

-- Signal ID: 728 (AMZN)
UPDATE signals SET
  base_combined_score = -22.35,
  alignment_bonus = 0,
  combined_score = -22.35,
  base_confidence = 0.8183,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 728 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -22.35,
  alignment_bonus = 0,
  combined_score = -22.35,
  base_confidence = 0.8183,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 728;

-- Signal ID: 727 (NVDA)
UPDATE signals SET
  base_combined_score = 1.46,
  alignment_bonus = 0,
  combined_score = 1.46,
  base_confidence = 0.799,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 727 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.46,
  alignment_bonus = 0,
  combined_score = 1.46,
  base_confidence = 0.799,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 727;

-- Signal ID: 726 (MOL.BD)
UPDATE signals SET
  base_combined_score = -1.07,
  alignment_bonus = 0,
  combined_score = -1.07,
  base_confidence = 0.6525,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 726 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.07,
  alignment_bonus = 0,
  combined_score = -1.07,
  base_confidence = 0.6525,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 726;

-- Signal ID: 725 (OTP.BD)
UPDATE signals SET
  base_combined_score = 12.69,
  alignment_bonus = 0,
  combined_score = 12.69,
  base_confidence = 0.7185,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 725 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.69,
  alignment_bonus = 0,
  combined_score = 12.69,
  base_confidence = 0.7185,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 725;

-- Signal ID: 724 (TSLA)
UPDATE signals SET
  base_combined_score = -14.96,
  alignment_bonus = 0,
  combined_score = -14.96,
  base_confidence = 0.7755,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 724 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -14.96,
  alignment_bonus = 0,
  combined_score = -14.96,
  base_confidence = 0.7755,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 724;

-- Signal ID: 723 (GOOGL)
UPDATE signals SET
  base_combined_score = -12.4,
  alignment_bonus = 0,
  combined_score = -12.4,
  base_confidence = 0.792,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 723 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -12.4,
  alignment_bonus = 0,
  combined_score = -12.4,
  base_confidence = 0.792,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 723;

-- Signal ID: 722 (MSFT)
UPDATE signals SET
  base_combined_score = -0.57,
  alignment_bonus = 0,
  combined_score = -0.57,
  base_confidence = 0.7837,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 722 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.57,
  alignment_bonus = 0,
  combined_score = -0.57,
  base_confidence = 0.7837,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 722;

-- Signal ID: 721 (AAPL)
UPDATE signals SET
  base_combined_score = 19.01,
  alignment_bonus = 0,
  combined_score = 19.01,
  base_confidence = 0.7855,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 721 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 19.01,
  alignment_bonus = 0,
  combined_score = 19.01,
  base_confidence = 0.7855,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 721;

-- Signal ID: 720 (OTP.BD)
UPDATE signals SET
  base_combined_score = 21.71,
  alignment_bonus = 0,
  combined_score = 21.71,
  base_confidence = 0.6522,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 720 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 21.71,
  alignment_bonus = 0,
  combined_score = 21.71,
  base_confidence = 0.6522,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 720;

-- Signal ID: 719 (MOL.BD)
UPDATE signals SET
  base_combined_score = 7.4,
  alignment_bonus = 0,
  combined_score = 7.4,
  base_confidence = 0.7043,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 719 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.4,
  alignment_bonus = 0,
  combined_score = 7.4,
  base_confidence = 0.7043,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 719;

-- Signal ID: 718 (OTP.BD)
UPDATE signals SET
  base_combined_score = -8.38,
  alignment_bonus = 0,
  combined_score = -8.38,
  base_confidence = 0.7345,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 718 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -8.38,
  alignment_bonus = 0,
  combined_score = -8.38,
  base_confidence = 0.7345,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 718;

-- Signal ID: 717 (MOL.BD)
UPDATE signals SET
  base_combined_score = 10.38,
  alignment_bonus = 0,
  combined_score = 10.38,
  base_confidence = 0.7043,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 717 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.38,
  alignment_bonus = 0,
  combined_score = 10.38,
  base_confidence = 0.7043,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 717;

-- Signal ID: 716 (OTP.BD)
UPDATE signals SET
  base_combined_score = -5.41,
  alignment_bonus = 0,
  combined_score = -5.41,
  base_confidence = 0.7345,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 716 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -5.41,
  alignment_bonus = 0,
  combined_score = -5.41,
  base_confidence = 0.7345,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 716;

-- Signal ID: 715 (MOL.BD)
UPDATE signals SET
  base_combined_score = 9.77,
  alignment_bonus = 0,
  combined_score = 9.77,
  base_confidence = 0.7043,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 715 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.77,
  alignment_bonus = 0,
  combined_score = 9.77,
  base_confidence = 0.7043,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 715;

-- Signal ID: 714 (OTP.BD)
UPDATE signals SET
  base_combined_score = -6.51,
  alignment_bonus = 0,
  combined_score = -6.51,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 714 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -6.51,
  alignment_bonus = 0,
  combined_score = -6.51,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 714;

-- Signal ID: 713 (MOL.BD)
UPDATE signals SET
  base_combined_score = 16.99,
  alignment_bonus = 0,
  combined_score = 16.99,
  base_confidence = 0.6893,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 713 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.99,
  alignment_bonus = 0,
  combined_score = 16.99,
  base_confidence = 0.6893,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 713;

-- Signal ID: 712 (OTP.BD)
UPDATE signals SET
  base_combined_score = 11.38,
  alignment_bonus = 0,
  combined_score = 11.38,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 712 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.38,
  alignment_bonus = 0,
  combined_score = 11.38,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 712;

-- Signal ID: 711 (MOL.BD)
UPDATE signals SET
  base_combined_score = 33.32,
  alignment_bonus = 0,
  combined_score = 33.32,
  base_confidence = 0.6893,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 711 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 33.32,
  alignment_bonus = 0,
  combined_score = 33.32,
  base_confidence = 0.6893,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 711;

-- Signal ID: 710 (OTP.BD)
UPDATE signals SET
  base_combined_score = 9.28,
  alignment_bonus = 0,
  combined_score = 9.28,
  base_confidence = 0.6975,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 710 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.28,
  alignment_bonus = 0,
  combined_score = 9.28,
  base_confidence = 0.6975,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 710;

-- Signal ID: 709 (MOL.BD)
UPDATE signals SET
  base_combined_score = 19.28,
  alignment_bonus = 0,
  combined_score = 19.28,
  base_confidence = 0.6893,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 709 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 19.28,
  alignment_bonus = 0,
  combined_score = 19.28,
  base_confidence = 0.6893,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 709;

-- Signal ID: 708 (OTP.BD)
UPDATE signals SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 708 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 708;

-- Signal ID: 707 (MOL.BD)
UPDATE signals SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 707 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 707;

-- Signal ID: 706 (IBM)
UPDATE signals SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 706 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 706;

-- Signal ID: 705 (META)
UPDATE signals SET
  base_combined_score = -13.19,
  alignment_bonus = 0,
  combined_score = -13.19,
  base_confidence = 0.8047,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 705 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -13.19,
  alignment_bonus = 0,
  combined_score = -13.19,
  base_confidence = 0.8047,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 705;

-- Signal ID: 704 (AMZN)
UPDATE signals SET
  base_combined_score = -1.47,
  alignment_bonus = 0,
  combined_score = -1.47,
  base_confidence = 0.7251,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 704 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.47,
  alignment_bonus = 0,
  combined_score = -1.47,
  base_confidence = 0.7251,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 704;

-- Signal ID: 703 (NVDA)
UPDATE signals SET
  base_combined_score = 5.48,
  alignment_bonus = 0,
  combined_score = 5.48,
  base_confidence = 0.7913,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 703 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.48,
  alignment_bonus = 0,
  combined_score = 5.48,
  base_confidence = 0.7913,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 703;

-- Signal ID: 702 (MOL.BD)
UPDATE signals SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 702 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 702;

-- Signal ID: 701 (OTP.BD)
UPDATE signals SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 701 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 701;

-- Signal ID: 700 (TSLA)
UPDATE signals SET
  base_combined_score = 11.23,
  alignment_bonus = 0,
  combined_score = 11.23,
  base_confidence = 0.7737,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 700 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.23,
  alignment_bonus = 0,
  combined_score = 11.23,
  base_confidence = 0.7737,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 700;

-- Signal ID: 699 (GOOGL)
UPDATE signals SET
  base_combined_score = -33.06,
  alignment_bonus = 0,
  combined_score = -33.06,
  base_confidence = 0.8185,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 699 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -33.06,
  alignment_bonus = 0,
  combined_score = -33.06,
  base_confidence = 0.8185,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 699;

-- Signal ID: 698 (MSFT)
UPDATE signals SET
  base_combined_score = -35.26,
  alignment_bonus = 0,
  combined_score = -35.26,
  base_confidence = 0.8308,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 698 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -35.26,
  alignment_bonus = 0,
  combined_score = -35.26,
  base_confidence = 0.8308,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 698;

-- Signal ID: 697 (AAPL)
UPDATE signals SET
  base_combined_score = 15.21,
  alignment_bonus = 0,
  combined_score = 15.21,
  base_confidence = 0.6965,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 697 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.21,
  alignment_bonus = 0,
  combined_score = 15.21,
  base_confidence = 0.6965,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 697;

-- Signal ID: 696 (OTP.BD)
UPDATE signals SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 696 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 696;

-- Signal ID: 695 (MOL.BD)
UPDATE signals SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 695 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 695;

-- Signal ID: 694 (IBM)
UPDATE signals SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 694 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 694;

-- Signal ID: 693 (META)
UPDATE signals SET
  base_combined_score = -13.19,
  alignment_bonus = 0,
  combined_score = -13.19,
  base_confidence = 0.8047,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 693 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -13.19,
  alignment_bonus = 0,
  combined_score = -13.19,
  base_confidence = 0.8047,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 693;

-- Signal ID: 692 (AMZN)
UPDATE signals SET
  base_combined_score = -3.14,
  alignment_bonus = 0,
  combined_score = -3.14,
  base_confidence = 0.7316,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 692 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -3.14,
  alignment_bonus = 0,
  combined_score = -3.14,
  base_confidence = 0.7316,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 692;

-- Signal ID: 691 (NVDA)
UPDATE signals SET
  base_combined_score = 6.04,
  alignment_bonus = 0,
  combined_score = 6.04,
  base_confidence = 0.7953,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 691 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.04,
  alignment_bonus = 0,
  combined_score = 6.04,
  base_confidence = 0.7953,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 691;

-- Signal ID: 690 (MOL.BD)
UPDATE signals SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 690 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.87,
  alignment_bonus = 0,
  combined_score = 22.87,
  base_confidence = 0.7108,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 690;

-- Signal ID: 689 (OTP.BD)
UPDATE signals SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 689 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.21,
  alignment_bonus = 0,
  combined_score = 11.21,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 689;

-- Signal ID: 688 (TSLA)
UPDATE signals SET
  base_combined_score = 11.23,
  alignment_bonus = 0,
  combined_score = 11.23,
  base_confidence = 0.7737,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 688 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.23,
  alignment_bonus = 0,
  combined_score = 11.23,
  base_confidence = 0.7737,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 688;

-- Signal ID: 687 (GOOGL)
UPDATE signals SET
  base_combined_score = -33.06,
  alignment_bonus = 0,
  combined_score = -33.06,
  base_confidence = 0.8185,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 687 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -33.06,
  alignment_bonus = 0,
  combined_score = -33.06,
  base_confidence = 0.8185,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 687;

-- Signal ID: 686 (MSFT)
UPDATE signals SET
  base_combined_score = -35.26,
  alignment_bonus = 0,
  combined_score = -35.26,
  base_confidence = 0.8308,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 686 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -35.26,
  alignment_bonus = 0,
  combined_score = -35.26,
  base_confidence = 0.8308,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 686;

-- Signal ID: 685 (AAPL)
UPDATE signals SET
  base_combined_score = 15.41,
  alignment_bonus = 0,
  combined_score = 15.41,
  base_confidence = 0.6935,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 685 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.41,
  alignment_bonus = 0,
  combined_score = 15.41,
  base_confidence = 0.6935,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 685;

-- Signal ID: 684 (IBM)
UPDATE signals SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 684 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 684;

-- Signal ID: 683 (META)
UPDATE signals SET
  base_combined_score = -9.79,
  alignment_bonus = 0,
  combined_score = -9.79,
  base_confidence = 0.7963,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 683 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.79,
  alignment_bonus = 0,
  combined_score = -9.79,
  base_confidence = 0.7963,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 683;

-- Signal ID: 682 (AMZN)
UPDATE signals SET
  base_combined_score = -1.72,
  alignment_bonus = 0,
  combined_score = -1.72,
  base_confidence = 0.7261,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 682 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.72,
  alignment_bonus = 0,
  combined_score = -1.72,
  base_confidence = 0.7261,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 682;

-- Signal ID: 681 (NVDA)
UPDATE signals SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7958,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 681 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7958,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 681;

-- Signal ID: 680 (MOL.BD)
UPDATE signals SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 680 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 680;

-- Signal ID: 679 (OTP.BD)
UPDATE signals SET
  base_combined_score = 0.93,
  alignment_bonus = 0,
  combined_score = 0.93,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 679 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.93,
  alignment_bonus = 0,
  combined_score = 0.93,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 679;

-- Signal ID: 678 (TSLA)
UPDATE signals SET
  base_combined_score = 9.18,
  alignment_bonus = 0,
  combined_score = 9.18,
  base_confidence = 0.7792,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 678 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.18,
  alignment_bonus = 0,
  combined_score = 9.18,
  base_confidence = 0.7792,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 678;

-- Signal ID: 677 (GOOGL)
UPDATE signals SET
  base_combined_score = -18.6,
  alignment_bonus = 0,
  combined_score = -18.6,
  base_confidence = 0.7855,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 677 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -18.6,
  alignment_bonus = 0,
  combined_score = -18.6,
  base_confidence = 0.7855,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 677;

-- Signal ID: 676 (MSFT)
UPDATE signals SET
  base_combined_score = -32.25,
  alignment_bonus = 0,
  combined_score = -32.25,
  base_confidence = 0.8083,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 676 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -32.25,
  alignment_bonus = 0,
  combined_score = -32.25,
  base_confidence = 0.8083,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 676;

-- Signal ID: 675 (AAPL)
UPDATE signals SET
  base_combined_score = 11.65,
  alignment_bonus = 0,
  combined_score = 11.65,
  base_confidence = 0.7025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 675 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.65,
  alignment_bonus = 0,
  combined_score = 11.65,
  base_confidence = 0.7025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 675;

-- Signal ID: 674 (IBM)
UPDATE signals SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 674 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 674;

-- Signal ID: 673 (META)
UPDATE signals SET
  base_combined_score = -9.99,
  alignment_bonus = 0,
  combined_score = -9.99,
  base_confidence = 0.7978,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 673 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.99,
  alignment_bonus = 0,
  combined_score = -9.99,
  base_confidence = 0.7978,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 673;

-- Signal ID: 672 (AMZN)
UPDATE signals SET
  base_combined_score = -4.54,
  alignment_bonus = 0,
  combined_score = -4.54,
  base_confidence = 0.7296,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 672 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -4.54,
  alignment_bonus = 0,
  combined_score = -4.54,
  base_confidence = 0.7296,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 672;

-- Signal ID: 671 (NVDA)
UPDATE signals SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7958,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 671 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7958,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 671;

-- Signal ID: 670 (MOL.BD)
UPDATE signals SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 670 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 670;

-- Signal ID: 669 (OTP.BD)
UPDATE signals SET
  base_combined_score = -0.75,
  alignment_bonus = 0,
  combined_score = -0.75,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 669 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.75,
  alignment_bonus = 0,
  combined_score = -0.75,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 669;

-- Signal ID: 668 (TSLA)
UPDATE signals SET
  base_combined_score = 9.18,
  alignment_bonus = 0,
  combined_score = 9.18,
  base_confidence = 0.7792,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 668 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.18,
  alignment_bonus = 0,
  combined_score = 9.18,
  base_confidence = 0.7792,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 668;

-- Signal ID: 667 (GOOGL)
UPDATE signals SET
  base_combined_score = -17.01,
  alignment_bonus = 0,
  combined_score = -17.01,
  base_confidence = 0.782,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 667 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -17.01,
  alignment_bonus = 0,
  combined_score = -17.01,
  base_confidence = 0.782,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 667;

-- Signal ID: 666 (MSFT)
UPDATE signals SET
  base_combined_score = -32.65,
  alignment_bonus = 0,
  combined_score = -32.65,
  base_confidence = 0.8073,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 666 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -32.65,
  alignment_bonus = 0,
  combined_score = -32.65,
  base_confidence = 0.8073,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 666;

-- Signal ID: 665 (AAPL)
UPDATE signals SET
  base_combined_score = 11.65,
  alignment_bonus = 0,
  combined_score = 11.65,
  base_confidence = 0.7025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 665 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.65,
  alignment_bonus = 0,
  combined_score = 11.65,
  base_confidence = 0.7025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 665;

-- Signal ID: 664 (IBM)
UPDATE signals SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 664 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 664;

-- Signal ID: 663 (META)
UPDATE signals SET
  base_combined_score = -9.13,
  alignment_bonus = 0,
  combined_score = -9.13,
  base_confidence = 0.8063,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 663 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.13,
  alignment_bonus = 0,
  combined_score = -9.13,
  base_confidence = 0.8063,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 663;

-- Signal ID: 662 (AMZN)
UPDATE signals SET
  base_combined_score = -5.99,
  alignment_bonus = 0,
  combined_score = -5.99,
  base_confidence = 0.7456,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 662 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -5.99,
  alignment_bonus = 0,
  combined_score = -5.99,
  base_confidence = 0.7456,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 662;

-- Signal ID: 661 (NVDA)
UPDATE signals SET
  base_combined_score = 6.88,
  alignment_bonus = 0,
  combined_score = 6.88,
  base_confidence = 0.7947,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 661 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.88,
  alignment_bonus = 0,
  combined_score = 6.88,
  base_confidence = 0.7947,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 661;

-- Signal ID: 660 (MOL.BD)
UPDATE signals SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 660 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 660;

-- Signal ID: 659 (OTP.BD)
UPDATE signals SET
  base_combined_score = -0.75,
  alignment_bonus = 0,
  combined_score = -0.75,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 659 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.75,
  alignment_bonus = 0,
  combined_score = -0.75,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 659;

-- Signal ID: 658 (TSLA)
UPDATE signals SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7917,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 658 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7917,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 658;

-- Signal ID: 657 (GOOGL)
UPDATE signals SET
  base_combined_score = -20.71,
  alignment_bonus = 0,
  combined_score = -20.71,
  base_confidence = 0.8065,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 657 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -20.71,
  alignment_bonus = 0,
  combined_score = -20.71,
  base_confidence = 0.8065,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 657;

-- Signal ID: 656 (MSFT)
UPDATE signals SET
  base_combined_score = -36.77,
  alignment_bonus = 0,
  combined_score = -36.77,
  base_confidence = 0.8237,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 656 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -36.77,
  alignment_bonus = 0,
  combined_score = -36.77,
  base_confidence = 0.8237,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 656;

-- Signal ID: 655 (AAPL)
UPDATE signals SET
  base_combined_score = 11.66,
  alignment_bonus = 0,
  combined_score = 11.66,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 655 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.66,
  alignment_bonus = 0,
  combined_score = 11.66,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 655;

-- Signal ID: 654 (IBM)
UPDATE signals SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 654 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.91,
  alignment_bonus = 0,
  combined_score = 16.91,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 654;

-- Signal ID: 653 (META)
UPDATE signals SET
  base_combined_score = -9.18,
  alignment_bonus = 0,
  combined_score = -9.18,
  base_confidence = 0.8067,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 653 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.18,
  alignment_bonus = 0,
  combined_score = -9.18,
  base_confidence = 0.8067,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 653;

-- Signal ID: 652 (AMZN)
UPDATE signals SET
  base_combined_score = -2.06,
  alignment_bonus = 0,
  combined_score = -2.06,
  base_confidence = 0.7381,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 652 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.06,
  alignment_bonus = 0,
  combined_score = -2.06,
  base_confidence = 0.7381,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 652;

-- Signal ID: 651 (NVDA)
UPDATE signals SET
  base_combined_score = 6.88,
  alignment_bonus = 0,
  combined_score = 6.88,
  base_confidence = 0.7947,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 651 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.88,
  alignment_bonus = 0,
  combined_score = 6.88,
  base_confidence = 0.7947,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 651;

-- Signal ID: 650 (MOL.BD)
UPDATE signals SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 650 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.73,
  alignment_bonus = 0,
  combined_score = 24.73,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 650;

-- Signal ID: 649 (OTP.BD)
UPDATE signals SET
  base_combined_score = -0.46,
  alignment_bonus = 0,
  combined_score = -0.46,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 649 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.46,
  alignment_bonus = 0,
  combined_score = -0.46,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 649;

-- Signal ID: 648 (TSLA)
UPDATE signals SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7917,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 648 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7917,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 648;

-- Signal ID: 647 (GOOGL)
UPDATE signals SET
  base_combined_score = -20.79,
  alignment_bonus = 0,
  combined_score = -20.79,
  base_confidence = 0.8065,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 647 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -20.79,
  alignment_bonus = 0,
  combined_score = -20.79,
  base_confidence = 0.8065,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 647;

-- Signal ID: 646 (MSFT)
UPDATE signals SET
  base_combined_score = -34.36,
  alignment_bonus = 0,
  combined_score = -34.36,
  base_confidence = 0.8153,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 646 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -34.36,
  alignment_bonus = 0,
  combined_score = -34.36,
  base_confidence = 0.8153,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 646;

-- Signal ID: 645 (AAPL)
UPDATE signals SET
  base_combined_score = 11.66,
  alignment_bonus = 0,
  combined_score = 11.66,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 645 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.66,
  alignment_bonus = 0,
  combined_score = 11.66,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 645;

-- Signal ID: 644 (NVDA)
UPDATE signals SET
  base_combined_score = 13.87,
  alignment_bonus = 0,
  combined_score = 13.87,
  base_confidence = 0.8098,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 644 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.87,
  alignment_bonus = 0,
  combined_score = 13.87,
  base_confidence = 0.8098,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 644;

-- Signal ID: 643 (MOL.BD)
UPDATE signals SET
  base_combined_score = 24.25,
  alignment_bonus = 0,
  combined_score = 24.25,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 643 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.25,
  alignment_bonus = 0,
  combined_score = 24.25,
  base_confidence = 0.7448,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 643;

-- Signal ID: 642 (OTP.BD)
UPDATE signals SET
  base_combined_score = -0.46,
  alignment_bonus = 0,
  combined_score = -0.46,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 642 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.46,
  alignment_bonus = 0,
  combined_score = -0.46,
  base_confidence = 0.7045,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 642;

-- Signal ID: 641 (TSLA)
UPDATE signals SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7917,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 641 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.41,
  alignment_bonus = 0,
  combined_score = 8.41,
  base_confidence = 0.7917,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 641;

-- Signal ID: 640 (GOOGL)
UPDATE signals SET
  base_combined_score = -18.22,
  alignment_bonus = 0,
  combined_score = -18.22,
  base_confidence = 0.798,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 640 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -18.22,
  alignment_bonus = 0,
  combined_score = -18.22,
  base_confidence = 0.798,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 640;

-- Signal ID: 639 (MSFT)
UPDATE signals SET
  base_combined_score = -29.74,
  alignment_bonus = 0,
  combined_score = -29.74,
  base_confidence = 0.8093,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 639 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -29.74,
  alignment_bonus = 0,
  combined_score = -29.74,
  base_confidence = 0.8093,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 639;

-- Signal ID: 638 (AAPL)
UPDATE signals SET
  base_combined_score = 14.04,
  alignment_bonus = 0,
  combined_score = 14.04,
  base_confidence = 0.699,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 638 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.04,
  alignment_bonus = 0,
  combined_score = 14.04,
  base_confidence = 0.699,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 638;

-- Signal ID: 637 (OTP.BD)
UPDATE signals SET
  base_combined_score = 2.19,
  alignment_bonus = 0,
  combined_score = 2.19,
  base_confidence = 0.659,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 637 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 2.19,
  alignment_bonus = 0,
  combined_score = 2.19,
  base_confidence = 0.659,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 637;

-- Signal ID: 636 (MOL.BD)
UPDATE signals SET
  base_combined_score = 21.4,
  alignment_bonus = 0,
  combined_score = 21.4,
  base_confidence = 0.6462,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 636 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 21.4,
  alignment_bonus = 0,
  combined_score = 21.4,
  base_confidence = 0.6462,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 636;

-- Signal ID: 635 (OTP.BD)
UPDATE signals SET
  base_combined_score = 6.1,
  alignment_bonus = 0,
  combined_score = 6.1,
  base_confidence = 0.659,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 635 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.1,
  alignment_bonus = 0,
  combined_score = 6.1,
  base_confidence = 0.659,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 635;

-- Signal ID: 634 (MOL.BD)
UPDATE signals SET
  base_combined_score = 26.27,
  alignment_bonus = 0,
  combined_score = 26.27,
  base_confidence = 0.7473,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 634 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 26.27,
  alignment_bonus = 0,
  combined_score = 26.27,
  base_confidence = 0.7473,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 634;

-- Signal ID: 633 (OTP.BD)
UPDATE signals SET
  base_combined_score = 10.01,
  alignment_bonus = 0,
  combined_score = 10.01,
  base_confidence = 0.659,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 633 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.01,
  alignment_bonus = 0,
  combined_score = 10.01,
  base_confidence = 0.659,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 633;

-- Signal ID: 632 (MOL.BD)
UPDATE signals SET
  base_combined_score = 17.66,
  alignment_bonus = 0,
  combined_score = 17.66,
  base_confidence = 0.7408,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 632 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 17.66,
  alignment_bonus = 0,
  combined_score = 17.66,
  base_confidence = 0.7408,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 632;

-- Signal ID: 631 (OTP.BD)
UPDATE signals SET
  base_combined_score = -1.86,
  alignment_bonus = 0,
  combined_score = -1.86,
  base_confidence = 0.6825,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 631 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.86,
  alignment_bonus = 0,
  combined_score = -1.86,
  base_confidence = 0.6825,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 631;

-- Signal ID: 630 (MOL.BD)
UPDATE signals SET
  base_combined_score = 31.56,
  alignment_bonus = 0,
  combined_score = 31.56,
  base_confidence = 0.6532,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 630 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.56,
  alignment_bonus = 0,
  combined_score = 31.56,
  base_confidence = 0.6532,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 630;

-- Signal ID: 629 (OTP.BD)
UPDATE signals SET
  base_combined_score = 1.58,
  alignment_bonus = 0,
  combined_score = 1.58,
  base_confidence = 0.595,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 629 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.58,
  alignment_bonus = 0,
  combined_score = 1.58,
  base_confidence = 0.595,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 629;

-- Signal ID: 628 (MOL.BD)
UPDATE signals SET
  base_combined_score = 31.17,
  alignment_bonus = 0,
  combined_score = 31.17,
  base_confidence = 0.6597,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 628 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.17,
  alignment_bonus = 0,
  combined_score = 31.17,
  base_confidence = 0.6597,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 628;

-- Signal ID: 627 (OTP.BD)
UPDATE signals SET
  base_combined_score = 12.96,
  alignment_bonus = 0,
  combined_score = 12.96,
  base_confidence = 0.595,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 627 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.96,
  alignment_bonus = 0,
  combined_score = 12.96,
  base_confidence = 0.595,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 627;

-- Signal ID: 626 (MOL.BD)
UPDATE signals SET
  base_combined_score = 24.57,
  alignment_bonus = 0,
  combined_score = 24.57,
  base_confidence = 0.6597,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 626 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.57,
  alignment_bonus = 0,
  combined_score = 24.57,
  base_confidence = 0.6597,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 626;

-- Signal ID: 625 (OTP.BD)
UPDATE signals SET
  base_combined_score = 14.52,
  alignment_bonus = 0,
  combined_score = 14.52,
  base_confidence = 0.727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 625 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.52,
  alignment_bonus = 0,
  combined_score = 14.52,
  base_confidence = 0.727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 625;

-- Signal ID: 624 (MOL.BD)
UPDATE signals SET
  base_combined_score = 30.44,
  alignment_bonus = 0,
  combined_score = 30.44,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 624 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 30.44,
  alignment_bonus = 0,
  combined_score = 30.44,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 624;

-- Signal ID: 623 (OTP.BD)
UPDATE signals SET
  base_combined_score = 14.72,
  alignment_bonus = 0,
  combined_score = 14.72,
  base_confidence = 0.727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 623 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.72,
  alignment_bonus = 0,
  combined_score = 14.72,
  base_confidence = 0.727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 623;

-- Signal ID: 622 (MOL.BD)
UPDATE signals SET
  base_combined_score = 40.78,
  alignment_bonus = 5,
  combined_score = 45.78,
  base_confidence = 0.7553,
  confidence_boost = 0.025,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 622 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 40.78,
  alignment_bonus = 5,
  combined_score = 45.78,
  base_confidence = 0.7553,
  confidence_boost = 0.025,
  strength = 'MODERATE'
WHERE signal_id = 622;

-- Signal ID: 621 (OTP.BD)
UPDATE signals SET
  base_combined_score = 17.06,
  alignment_bonus = 0,
  combined_score = 17.06,
  base_confidence = 0.6395,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 621 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 17.06,
  alignment_bonus = 0,
  combined_score = 17.06,
  base_confidence = 0.6395,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 621;

-- Signal ID: 620 (MOL.BD)
UPDATE signals SET
  base_combined_score = 22.06,
  alignment_bonus = 0,
  combined_score = 22.06,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 620 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.06,
  alignment_bonus = 0,
  combined_score = 22.06,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 620;

-- Signal ID: 619 (OTP.BD)
UPDATE signals SET
  base_combined_score = 10.28,
  alignment_bonus = 0,
  combined_score = 10.28,
  base_confidence = 0.727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 619 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.28,
  alignment_bonus = 0,
  combined_score = 10.28,
  base_confidence = 0.727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 619;

-- Signal ID: 618 (MOL.BD)
UPDATE signals SET
  base_combined_score = 20.31,
  alignment_bonus = 0,
  combined_score = 20.31,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 618 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.31,
  alignment_bonus = 0,
  combined_score = 20.31,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 618;

-- Signal ID: 617 (OTP.BD)
UPDATE signals SET
  base_combined_score = 7.4,
  alignment_bonus = 0,
  combined_score = 7.4,
  base_confidence = 0.7085,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 617 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.4,
  alignment_bonus = 0,
  combined_score = 7.4,
  base_confidence = 0.7085,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 617;

-- Signal ID: 616 (MOL.BD)
UPDATE signals SET
  base_combined_score = 22.06,
  alignment_bonus = 0,
  combined_score = 22.06,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 616 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.06,
  alignment_bonus = 0,
  combined_score = 22.06,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 616;

-- Signal ID: 615 (OTP.BD)
UPDATE signals SET
  base_combined_score = 8.54,
  alignment_bonus = 0,
  combined_score = 8.54,
  base_confidence = 0.7085,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 615 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.54,
  alignment_bonus = 0,
  combined_score = 8.54,
  base_confidence = 0.7085,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 615;

-- Signal ID: 614 (MOL.BD)
UPDATE signals SET
  base_combined_score = 32.77,
  alignment_bonus = 0,
  combined_score = 32.77,
  base_confidence = 0.6597,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 614 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 32.77,
  alignment_bonus = 0,
  combined_score = 32.77,
  base_confidence = 0.6597,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 614;

-- Signal ID: 613 (OTP.BD)
UPDATE signals SET
  base_combined_score = 8.86,
  alignment_bonus = 0,
  combined_score = 8.86,
  base_confidence = 0.7085,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 613 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.86,
  alignment_bonus = 0,
  combined_score = 8.86,
  base_confidence = 0.7085,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 613;

-- Signal ID: 612 (MOL.BD)
UPDATE signals SET
  base_combined_score = 27.31,
  alignment_bonus = 0,
  combined_score = 27.31,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 612 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 27.31,
  alignment_bonus = 0,
  combined_score = 27.31,
  base_confidence = 0.7553,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 612;

-- Signal ID: 611 (OTP.BD)
UPDATE signals SET
  base_combined_score = -1.04,
  alignment_bonus = 0,
  combined_score = -1.04,
  base_confidence = 0.762,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 611 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.04,
  alignment_bonus = 0,
  combined_score = -1.04,
  base_confidence = 0.762,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 611;

-- Signal ID: 610 (MOL.BD)
UPDATE signals SET
  base_combined_score = 25.17,
  alignment_bonus = 0,
  combined_score = 25.17,
  base_confidence = 0.7338,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 610 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.17,
  alignment_bonus = 0,
  combined_score = 25.17,
  base_confidence = 0.7338,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 610;

-- Signal ID: 609 (OTP.BD)
UPDATE signals SET
  base_combined_score = -11.63,
  alignment_bonus = 0,
  combined_score = -11.63,
  base_confidence = 0.7475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 609 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -11.63,
  alignment_bonus = 0,
  combined_score = -11.63,
  base_confidence = 0.7475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 609;

-- Signal ID: 608 (MOL.BD)
UPDATE signals SET
  base_combined_score = 28.14,
  alignment_bonus = 0,
  combined_score = 28.14,
  base_confidence = 0.7338,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 608 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 28.14,
  alignment_bonus = 0,
  combined_score = 28.14,
  base_confidence = 0.7338,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 608;

-- Signal ID: 607 (NVDA)
UPDATE signals SET
  base_combined_score = 4.15,
  alignment_bonus = 0,
  combined_score = 4.15,
  base_confidence = 0.7873,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 607 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.15,
  alignment_bonus = 0,
  combined_score = 4.15,
  base_confidence = 0.7873,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 607;

-- Signal ID: 606 (MSFT)
UPDATE signals SET
  base_combined_score = -10.48,
  alignment_bonus = 0,
  combined_score = -10.48,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 606 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -10.48,
  alignment_bonus = 0,
  combined_score = -10.48,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 606;

-- Signal ID: 605 (TSLA)
UPDATE signals SET
  base_combined_score = 4.03,
  alignment_bonus = 0,
  combined_score = 4.03,
  base_confidence = 0.783,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 605 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.03,
  alignment_bonus = 0,
  combined_score = 4.03,
  base_confidence = 0.783,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 605;

-- Signal ID: 604 (AAPL)
UPDATE signals SET
  base_combined_score = 22.34,
  alignment_bonus = 0,
  combined_score = 22.34,
  base_confidence = 0.8125,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 604 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.34,
  alignment_bonus = 0,
  combined_score = 22.34,
  base_confidence = 0.8125,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 604;

-- Signal ID: 603 (NVDA)
UPDATE signals SET
  base_combined_score = 3.91,
  alignment_bonus = 0,
  combined_score = 3.91,
  base_confidence = 0.6932,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 603 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.91,
  alignment_bonus = 0,
  combined_score = 3.91,
  base_confidence = 0.6932,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 603;

-- Signal ID: 602 (MSFT)
UPDATE signals SET
  base_combined_score = -10.64,
  alignment_bonus = 0,
  combined_score = -10.64,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 602 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -10.64,
  alignment_bonus = 0,
  combined_score = -10.64,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 602;

-- Signal ID: 601 (TSLA)
UPDATE signals SET
  base_combined_score = -10.11,
  alignment_bonus = 0,
  combined_score = -10.11,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 601 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -10.11,
  alignment_bonus = 0,
  combined_score = -10.11,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 601;

-- Signal ID: 600 (AAPL)
UPDATE signals SET
  base_combined_score = 20.72,
  alignment_bonus = 0,
  combined_score = 20.72,
  base_confidence = 0.8125,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 600 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.72,
  alignment_bonus = 0,
  combined_score = 20.72,
  base_confidence = 0.8125,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 600;

-- Signal ID: 599 (NVDA)
UPDATE signals SET
  base_combined_score = -2.04,
  alignment_bonus = 0,
  combined_score = -2.04,
  base_confidence = 0.6947,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 599 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.04,
  alignment_bonus = 0,
  combined_score = -2.04,
  base_confidence = 0.6947,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 599;

-- Signal ID: 598 (MSFT)
UPDATE signals SET
  base_combined_score = -7.42,
  alignment_bonus = 0,
  combined_score = -7.42,
  base_confidence = 0.7905,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 598 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -7.42,
  alignment_bonus = 0,
  combined_score = -7.42,
  base_confidence = 0.7905,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 598;

-- Signal ID: 597 (TSLA)
UPDATE signals SET
  base_combined_score = 12.37,
  alignment_bonus = 0,
  combined_score = 12.37,
  base_confidence = 0.8035,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 597 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.37,
  alignment_bonus = 0,
  combined_score = 12.37,
  base_confidence = 0.8035,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 597;

-- Signal ID: 596 (AAPL)
UPDATE signals SET
  base_combined_score = 35.47,
  alignment_bonus = 0,
  combined_score = 35.47,
  base_confidence = 0.8135,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 596 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 35.47,
  alignment_bonus = 0,
  combined_score = 35.47,
  base_confidence = 0.8135,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 596;

-- Signal ID: 595 (NVDA)
UPDATE signals SET
  base_combined_score = -14.43,
  alignment_bonus = 0,
  combined_score = -14.43,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 595 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -14.43,
  alignment_bonus = 0,
  combined_score = -14.43,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 595;

-- Signal ID: 594 (MSFT)
UPDATE signals SET
  base_combined_score = 0.39,
  alignment_bonus = 0,
  combined_score = 0.39,
  base_confidence = 0.686,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 594 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.39,
  alignment_bonus = 0,
  combined_score = 0.39,
  base_confidence = 0.686,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 594;

-- Signal ID: 593 (TSLA)
UPDATE signals SET
  base_combined_score = -11.38,
  alignment_bonus = 0,
  combined_score = -11.38,
  base_confidence = 0.8005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 593 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -11.38,
  alignment_bonus = 0,
  combined_score = -11.38,
  base_confidence = 0.8005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 593;

-- Signal ID: 592 (AAPL)
UPDATE signals SET
  base_combined_score = 27.83,
  alignment_bonus = 0,
  combined_score = 27.83,
  base_confidence = 0.8135,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 592 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 27.83,
  alignment_bonus = 0,
  combined_score = 27.83,
  base_confidence = 0.8135,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 592;

-- Signal ID: 591 (NVDA)
UPDATE signals SET
  base_combined_score = -12.23,
  alignment_bonus = 0,
  combined_score = -12.23,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 591 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -12.23,
  alignment_bonus = 0,
  combined_score = -12.23,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 591;

-- Signal ID: 590 (MOL.BD)
UPDATE signals SET
  base_combined_score = 20.34,
  alignment_bonus = 0,
  combined_score = 20.34,
  base_confidence = 0.7162,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 590 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.34,
  alignment_bonus = 0,
  combined_score = 20.34,
  base_confidence = 0.7162,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 590;

-- Signal ID: 589 (OTP.BD)
UPDATE signals SET
  base_combined_score = 16.32,
  alignment_bonus = 0,
  combined_score = 16.32,
  base_confidence = 0.763,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 589 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.32,
  alignment_bonus = 0,
  combined_score = 16.32,
  base_confidence = 0.763,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 589;

-- Signal ID: 588 (TSLA)
UPDATE signals SET
  base_combined_score = 1.93,
  alignment_bonus = 0,
  combined_score = 1.93,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 588 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.93,
  alignment_bonus = 0,
  combined_score = 1.93,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 588;

-- Signal ID: 587 (GOOGL)
UPDATE signals SET
  base_combined_score = -9.59,
  alignment_bonus = 0,
  combined_score = -9.59,
  base_confidence = 0.7,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 587 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.59,
  alignment_bonus = 0,
  combined_score = -9.59,
  base_confidence = 0.7,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 587;

-- Signal ID: 586 (MSFT)
UPDATE signals SET
  base_combined_score = -19.48,
  alignment_bonus = 0,
  combined_score = -19.48,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 586 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -19.48,
  alignment_bonus = 0,
  combined_score = -19.48,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 586;

-- Signal ID: 585 (AAPL)
UPDATE signals SET
  base_combined_score = 31.94,
  alignment_bonus = 0,
  combined_score = 31.94,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 585 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.94,
  alignment_bonus = 0,
  combined_score = 31.94,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 585;

-- Signal ID: 584 (NVDA)
UPDATE signals SET
  base_combined_score = -12.23,
  alignment_bonus = 0,
  combined_score = -12.23,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 584 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -12.23,
  alignment_bonus = 0,
  combined_score = -12.23,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 584;

-- Signal ID: 583 (MSFT)
UPDATE signals SET
  base_combined_score = -19.48,
  alignment_bonus = 0,
  combined_score = -19.48,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 583 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -19.48,
  alignment_bonus = 0,
  combined_score = -19.48,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 583;

-- Signal ID: 582 (TSLA)
UPDATE signals SET
  base_combined_score = 1.93,
  alignment_bonus = 0,
  combined_score = 1.93,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 582 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.93,
  alignment_bonus = 0,
  combined_score = 1.93,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 582;

-- Signal ID: 581 (AAPL)
UPDATE signals SET
  base_combined_score = 31.94,
  alignment_bonus = 0,
  combined_score = 31.94,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 581 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.94,
  alignment_bonus = 0,
  combined_score = 31.94,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 581;

-- Signal ID: 580 (NVDA)
UPDATE signals SET
  base_combined_score = -12.78,
  alignment_bonus = 0,
  combined_score = -12.78,
  base_confidence = 0.8022,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 580 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -12.78,
  alignment_bonus = 0,
  combined_score = -12.78,
  base_confidence = 0.8022,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 580;

-- Signal ID: 579 (MSFT)
UPDATE signals SET
  base_combined_score = -17.18,
  alignment_bonus = 0,
  combined_score = -17.18,
  base_confidence = 0.773,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 579 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -17.18,
  alignment_bonus = 0,
  combined_score = -17.18,
  base_confidence = 0.773,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 579;

-- Signal ID: 578 (TSLA)
UPDATE signals SET
  base_combined_score = 7.25,
  alignment_bonus = 0,
  combined_score = 7.25,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 578 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.25,
  alignment_bonus = 0,
  combined_score = 7.25,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 578;

-- Signal ID: 577 (AAPL)
UPDATE signals SET
  base_combined_score = 21.8,
  alignment_bonus = 0,
  combined_score = 21.8,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 577 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 21.8,
  alignment_bonus = 0,
  combined_score = 21.8,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 577;

-- Signal ID: 576 (NVDA)
UPDATE signals SET
  base_combined_score = -12.2,
  alignment_bonus = 0,
  combined_score = -12.2,
  base_confidence = 0.8027,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 576 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -12.2,
  alignment_bonus = 0,
  combined_score = -12.2,
  base_confidence = 0.8027,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 576;

-- Signal ID: 575 (MSFT)
UPDATE signals SET
  base_combined_score = -13.15,
  alignment_bonus = 0,
  combined_score = -13.15,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 575 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -13.15,
  alignment_bonus = 0,
  combined_score = -13.15,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 575;

-- Signal ID: 574 (TSLA)
UPDATE signals SET
  base_combined_score = 0.01,
  alignment_bonus = 0,
  combined_score = 0.01,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 574 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.01,
  alignment_bonus = 0,
  combined_score = 0.01,
  base_confidence = 0.71,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 574;

-- Signal ID: 573 (AAPL)
UPDATE signals SET
  base_combined_score = 16.72,
  alignment_bonus = 0,
  combined_score = 16.72,
  base_confidence = 0.7975,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 573 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.72,
  alignment_bonus = 0,
  combined_score = 16.72,
  base_confidence = 0.7975,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 573;

-- Signal ID: 572 (NVDA)
UPDATE signals SET
  base_combined_score = 3.75,
  alignment_bonus = 0,
  combined_score = 3.75,
  base_confidence = 0.8103,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 572 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.75,
  alignment_bonus = 0,
  combined_score = 3.75,
  base_confidence = 0.8103,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 572;

-- Signal ID: 571 (MSFT)
UPDATE signals SET
  base_combined_score = -18.31,
  alignment_bonus = 0,
  combined_score = -18.31,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 571 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -18.31,
  alignment_bonus = 0,
  combined_score = -18.31,
  base_confidence = 0.7735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 571;

-- Signal ID: 570 (TSLA)
UPDATE signals SET
  base_combined_score = 10.47,
  alignment_bonus = 0,
  combined_score = 10.47,
  base_confidence = 0.7975,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 570 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.47,
  alignment_bonus = 0,
  combined_score = 10.47,
  base_confidence = 0.7975,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 570;

-- Signal ID: 569 (AAPL)
UPDATE signals SET
  base_combined_score = 30.51,
  alignment_bonus = 0,
  combined_score = 30.51,
  base_confidence = 0.801,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 569 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 30.51,
  alignment_bonus = 0,
  combined_score = 30.51,
  base_confidence = 0.801,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 569;

-- Signal ID: 568 (NVDA)
UPDATE signals SET
  base_combined_score = 11.65,
  alignment_bonus = 0,
  combined_score = 11.65,
  base_confidence = 0.8103,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 568 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.65,
  alignment_bonus = 0,
  combined_score = 11.65,
  base_confidence = 0.8103,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 568;

-- Signal ID: 567 (MSFT)
UPDATE signals SET
  base_combined_score = -15.99,
  alignment_bonus = 0,
  combined_score = -15.99,
  base_confidence = 0.7745,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 567 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -15.99,
  alignment_bonus = 0,
  combined_score = -15.99,
  base_confidence = 0.7745,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 567;

-- Signal ID: 566 (TSLA)
UPDATE signals SET
  base_combined_score = 14.47,
  alignment_bonus = 0,
  combined_score = 14.47,
  base_confidence = 0.7973,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 566 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.47,
  alignment_bonus = 0,
  combined_score = 14.47,
  base_confidence = 0.7973,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 566;

-- Signal ID: 565 (AAPL)
UPDATE signals SET
  base_combined_score = 33.82,
  alignment_bonus = 0,
  combined_score = 33.82,
  base_confidence = 0.801,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 565 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 33.82,
  alignment_bonus = 0,
  combined_score = 33.82,
  base_confidence = 0.801,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 565;

-- Signal ID: 564 (NVDA)
UPDATE signals SET
  base_combined_score = 11.82,
  alignment_bonus = 0,
  combined_score = 11.82,
  base_confidence = 0.7073,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 564 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.82,
  alignment_bonus = 0,
  combined_score = 11.82,
  base_confidence = 0.7073,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 564;

-- Signal ID: 563 (MSFT)
UPDATE signals SET
  base_combined_score = 9.35,
  alignment_bonus = 0,
  combined_score = 9.35,
  base_confidence = 0.7775,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 563 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.35,
  alignment_bonus = 0,
  combined_score = 9.35,
  base_confidence = 0.7775,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 563;

-- Signal ID: 562 (TSLA)
UPDATE signals SET
  base_combined_score = 13.44,
  alignment_bonus = 0,
  combined_score = 13.44,
  base_confidence = 0.7143,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 562 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.44,
  alignment_bonus = 0,
  combined_score = 13.44,
  base_confidence = 0.7143,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 562;

-- Signal ID: 561 (AAPL)
UPDATE signals SET
  base_combined_score = 27.11,
  alignment_bonus = 0,
  combined_score = 27.11,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 561 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 27.11,
  alignment_bonus = 0,
  combined_score = 27.11,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 561;

-- Signal ID: 560 (NVDA)
UPDATE signals SET
  base_combined_score = 3.05,
  alignment_bonus = 0,
  combined_score = 3.05,
  base_confidence = 0.7998,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 560 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.05,
  alignment_bonus = 0,
  combined_score = 3.05,
  base_confidence = 0.7998,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 560;

-- Signal ID: 559 (MSFT)
UPDATE signals SET
  base_combined_score = 6.91,
  alignment_bonus = 0,
  combined_score = 6.91,
  base_confidence = 0.6915,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 559 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.91,
  alignment_bonus = 0,
  combined_score = 6.91,
  base_confidence = 0.6915,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 559;

-- Signal ID: 558 (TSLA)
UPDATE signals SET
  base_combined_score = 5.39,
  alignment_bonus = 0,
  combined_score = 5.39,
  base_confidence = 0.81,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 558 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.39,
  alignment_bonus = 0,
  combined_score = 5.39,
  base_confidence = 0.81,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 558;

-- Signal ID: 557 (AAPL)
UPDATE signals SET
  base_combined_score = 27.32,
  alignment_bonus = 0,
  combined_score = 27.32,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 557 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 27.32,
  alignment_bonus = 0,
  combined_score = 27.32,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 557;

-- Signal ID: 556 (NVDA)
UPDATE signals SET
  base_combined_score = 2.74,
  alignment_bonus = 0,
  combined_score = 2.74,
  base_confidence = 0.8003,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 556 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 2.74,
  alignment_bonus = 0,
  combined_score = 2.74,
  base_confidence = 0.8003,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 556;

-- Signal ID: 555 (MSFT)
UPDATE signals SET
  base_combined_score = -4.83,
  alignment_bonus = 0,
  combined_score = -4.83,
  base_confidence = 0.779,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 555 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -4.83,
  alignment_bonus = 0,
  combined_score = -4.83,
  base_confidence = 0.779,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 555;

-- Signal ID: 554 (TSLA)
UPDATE signals SET
  base_combined_score = 3.06,
  alignment_bonus = 0,
  combined_score = 3.06,
  base_confidence = 0.8048,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 554 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.06,
  alignment_bonus = 0,
  combined_score = 3.06,
  base_confidence = 0.8048,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 554;

-- Signal ID: 553 (AAPL)
UPDATE signals SET
  base_combined_score = 25.07,
  alignment_bonus = 0,
  combined_score = 25.07,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 553 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.07,
  alignment_bonus = 0,
  combined_score = 25.07,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 553;

-- Signal ID: 552 (NVDA)
UPDATE signals SET
  base_combined_score = 3.35,
  alignment_bonus = 0,
  combined_score = 3.35,
  base_confidence = 0.8003,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 552 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.35,
  alignment_bonus = 0,
  combined_score = 3.35,
  base_confidence = 0.8003,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 552;

-- Signal ID: 551 (MSFT)
UPDATE signals SET
  base_combined_score = -2.17,
  alignment_bonus = 0,
  combined_score = -2.17,
  base_confidence = 0.6915,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 551 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.17,
  alignment_bonus = 0,
  combined_score = -2.17,
  base_confidence = 0.6915,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 551;

-- Signal ID: 550 (TSLA)
UPDATE signals SET
  base_combined_score = 3.72,
  alignment_bonus = 0,
  combined_score = 3.72,
  base_confidence = 0.8113,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 550 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.72,
  alignment_bonus = 0,
  combined_score = 3.72,
  base_confidence = 0.8113,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 550;

-- Signal ID: 549 (AAPL)
UPDATE signals SET
  base_combined_score = 16.75,
  alignment_bonus = 0,
  combined_score = 16.75,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 549 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.75,
  alignment_bonus = 0,
  combined_score = 16.75,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 549;

-- Signal ID: 548 (NVDA)
UPDATE signals SET
  base_combined_score = 7.47,
  alignment_bonus = 0,
  combined_score = 7.47,
  base_confidence = 0.8073,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 548 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.47,
  alignment_bonus = 0,
  combined_score = 7.47,
  base_confidence = 0.8073,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 548;

-- Signal ID: 547 (MSFT)
UPDATE signals SET
  base_combined_score = -12.94,
  alignment_bonus = 0,
  combined_score = -12.94,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 547 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -12.94,
  alignment_bonus = 0,
  combined_score = -12.94,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 547;

-- Signal ID: 546 (TSLA)
UPDATE signals SET
  base_combined_score = 1.77,
  alignment_bonus = 0,
  combined_score = 1.77,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 546 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.77,
  alignment_bonus = 0,
  combined_score = 1.77,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 546;

-- Signal ID: 545 (AAPL)
UPDATE signals SET
  base_combined_score = 12.16,
  alignment_bonus = 0,
  combined_score = 12.16,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 545 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.16,
  alignment_bonus = 0,
  combined_score = 12.16,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 545;

-- Signal ID: 544 (NVDA)
UPDATE signals SET
  base_combined_score = 20.22,
  alignment_bonus = 0,
  combined_score = 20.22,
  base_confidence = 0.7172,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 544 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.22,
  alignment_bonus = 0,
  combined_score = 20.22,
  base_confidence = 0.7172,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 544;

-- Signal ID: 543 (MSFT)
UPDATE signals SET
  base_combined_score = -9.92,
  alignment_bonus = 0,
  combined_score = -9.92,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 543 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.92,
  alignment_bonus = 0,
  combined_score = -9.92,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 543;

-- Signal ID: 542 (TSLA)
UPDATE signals SET
  base_combined_score = 7.99,
  alignment_bonus = 0,
  combined_score = 7.99,
  base_confidence = 0.7163,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 542 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.99,
  alignment_bonus = 0,
  combined_score = 7.99,
  base_confidence = 0.7163,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 542;

-- Signal ID: 541 (AAPL)
UPDATE signals SET
  base_combined_score = 23.92,
  alignment_bonus = 0,
  combined_score = 23.92,
  base_confidence = 0.706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 541 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.92,
  alignment_bonus = 0,
  combined_score = 23.92,
  base_confidence = 0.706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 541;

-- Signal ID: 540 (NVDA)
UPDATE signals SET
  base_combined_score = 7.32,
  alignment_bonus = 0,
  combined_score = 7.32,
  base_confidence = 0.8147,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 540 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.32,
  alignment_bonus = 0,
  combined_score = 7.32,
  base_confidence = 0.8147,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 540;

-- Signal ID: 539 (MSFT)
UPDATE signals SET
  base_combined_score = -6.89,
  alignment_bonus = 0,
  combined_score = -6.89,
  base_confidence = 0.708,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 539 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -6.89,
  alignment_bonus = 0,
  combined_score = -6.89,
  base_confidence = 0.708,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 539;

-- Signal ID: 538 (TSLA)
UPDATE signals SET
  base_combined_score = 1.58,
  alignment_bonus = 0,
  combined_score = 1.58,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 538 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.58,
  alignment_bonus = 0,
  combined_score = 1.58,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 538;

-- Signal ID: 537 (AAPL)
UPDATE signals SET
  base_combined_score = 14.02,
  alignment_bonus = 0,
  combined_score = 14.02,
  base_confidence = 0.8,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 537 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.02,
  alignment_bonus = 0,
  combined_score = 14.02,
  base_confidence = 0.8,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 537;

-- Signal ID: 536 (NVDA)
UPDATE signals SET
  base_combined_score = 4.36,
  alignment_bonus = 0,
  combined_score = 4.36,
  base_confidence = 0.8223,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 536 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.36,
  alignment_bonus = 0,
  combined_score = 4.36,
  base_confidence = 0.8223,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 536;

-- Signal ID: 535 (MSFT)
UPDATE signals SET
  base_combined_score = -10.02,
  alignment_bonus = 0,
  combined_score = -10.02,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 535 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -10.02,
  alignment_bonus = 0,
  combined_score = -10.02,
  base_confidence = 0.7955,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 535;

-- Signal ID: 534 (TSLA)
UPDATE signals SET
  base_combined_score = 0.38,
  alignment_bonus = 0,
  combined_score = 0.38,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 534 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.38,
  alignment_bonus = 0,
  combined_score = 0.38,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 534;

-- Signal ID: 533 (AAPL)
UPDATE signals SET
  base_combined_score = 14.75,
  alignment_bonus = 0,
  combined_score = 14.75,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 533 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.75,
  alignment_bonus = 0,
  combined_score = 14.75,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 533;

-- Signal ID: 532 (NVDA)
UPDATE signals SET
  base_combined_score = 1.92,
  alignment_bonus = 0,
  combined_score = 1.92,
  base_confidence = 0.8107,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 532 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.92,
  alignment_bonus = 0,
  combined_score = 1.92,
  base_confidence = 0.8107,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 532;

-- Signal ID: 531 (MSFT)
UPDATE signals SET
  base_combined_score = 0.05,
  alignment_bonus = 0,
  combined_score = 0.05,
  base_confidence = 0.6885,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 531 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.05,
  alignment_bonus = 0,
  combined_score = 0.05,
  base_confidence = 0.6885,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 531;

-- Signal ID: 530 (TSLA)
UPDATE signals SET
  base_combined_score = 0.4,
  alignment_bonus = 0,
  combined_score = 0.4,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 530 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.4,
  alignment_bonus = 0,
  combined_score = 0.4,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 530;

-- Signal ID: 529 (AAPL)
UPDATE signals SET
  base_combined_score = 19.44,
  alignment_bonus = 0,
  combined_score = 19.44,
  base_confidence = 0.7925,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 529 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 19.44,
  alignment_bonus = 0,
  combined_score = 19.44,
  base_confidence = 0.7925,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 529;

-- Signal ID: 528 (NVDA)
UPDATE signals SET
  base_combined_score = 1.12,
  alignment_bonus = 0,
  combined_score = 1.12,
  base_confidence = 0.8107,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 528 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.12,
  alignment_bonus = 0,
  combined_score = 1.12,
  base_confidence = 0.8107,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 528;

-- Signal ID: 527 (MSFT)
UPDATE signals SET
  base_combined_score = 4.06,
  alignment_bonus = 0,
  combined_score = 4.06,
  base_confidence = 0.793,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 527 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.06,
  alignment_bonus = 0,
  combined_score = 4.06,
  base_confidence = 0.793,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 527;

-- Signal ID: 526 (TSLA)
UPDATE signals SET
  base_combined_score = -0.06,
  alignment_bonus = 0,
  combined_score = -0.06,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 526 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.06,
  alignment_bonus = 0,
  combined_score = -0.06,
  base_confidence = 0.8037,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 526;

-- Signal ID: 525 (AAPL)
UPDATE signals SET
  base_combined_score = 23.46,
  alignment_bonus = 0,
  combined_score = 23.46,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 525 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.46,
  alignment_bonus = 0,
  combined_score = 23.46,
  base_confidence = 0.705,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 525;

-- Signal ID: 524 (NVDA)
UPDATE signals SET
  base_combined_score = 9.34,
  alignment_bonus = 0,
  combined_score = 9.34,
  base_confidence = 0.6475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 524 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.34,
  alignment_bonus = 0,
  combined_score = 9.34,
  base_confidence = 0.6475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 524;

-- Signal ID: 523 (MSFT)
UPDATE signals SET
  base_combined_score = 7.9,
  alignment_bonus = 0,
  combined_score = 7.9,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 523 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.9,
  alignment_bonus = 0,
  combined_score = 7.9,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 523;

-- Signal ID: 522 (TSLA)
UPDATE signals SET
  base_combined_score = 2.63,
  alignment_bonus = 0,
  combined_score = 2.63,
  base_confidence = 0.8014,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 522 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 2.63,
  alignment_bonus = 0,
  combined_score = 2.63,
  base_confidence = 0.8014,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 522;

-- Signal ID: 521 (AAPL)
UPDATE signals SET
  base_combined_score = 2.85,
  alignment_bonus = 0,
  combined_score = 2.85,
  base_confidence = 0.799,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 521 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 2.85,
  alignment_bonus = 0,
  combined_score = 2.85,
  base_confidence = 0.799,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 521;

-- Signal ID: 520 (OTP.BD)
UPDATE signals SET
  base_combined_score = 30.7,
  alignment_bonus = 0,
  combined_score = 30.7,
  base_confidence = 0.756,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 520 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 30.7,
  alignment_bonus = 0,
  combined_score = 30.7,
  base_confidence = 0.756,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 520;

-- Signal ID: 519 (MOL.BD)
UPDATE signals SET
  base_combined_score = 17.53,
  alignment_bonus = 0,
  combined_score = 17.53,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 519 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 17.53,
  alignment_bonus = 0,
  combined_score = 17.53,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 519;

-- Signal ID: 518 (NVDA)
UPDATE signals SET
  base_combined_score = 1.62,
  alignment_bonus = 0,
  combined_score = 1.62,
  base_confidence = 0.812,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 518 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.62,
  alignment_bonus = 0,
  combined_score = 1.62,
  base_confidence = 0.812,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 518;

-- Signal ID: 517 (MOL.BD)
UPDATE signals SET
  base_combined_score = 15.95,
  alignment_bonus = 0,
  combined_score = 15.95,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 517 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.95,
  alignment_bonus = 0,
  combined_score = 15.95,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 517;

-- Signal ID: 516 (OTP.BD)
UPDATE signals SET
  base_combined_score = 31.67,
  alignment_bonus = 0,
  combined_score = 31.67,
  base_confidence = 0.756,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 516 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.67,
  alignment_bonus = 0,
  combined_score = 31.67,
  base_confidence = 0.756,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 516;

-- Signal ID: 515 (TSLA)
UPDATE signals SET
  base_combined_score = -0.48,
  alignment_bonus = 0,
  combined_score = -0.48,
  base_confidence = 0.7904,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 515 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.48,
  alignment_bonus = 0,
  combined_score = -0.48,
  base_confidence = 0.7904,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 515;

-- Signal ID: 514 (GOOGL)
UPDATE signals SET
  base_combined_score = 16.51,
  alignment_bonus = 0,
  combined_score = 16.51,
  base_confidence = 0.782,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 514 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.51,
  alignment_bonus = 0,
  combined_score = 16.51,
  base_confidence = 0.782,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 514;

-- Signal ID: 513 (MSFT)
UPDATE signals SET
  base_combined_score = 6.85,
  alignment_bonus = 0,
  combined_score = 6.85,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 513 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.85,
  alignment_bonus = 0,
  combined_score = 6.85,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 513;

-- Signal ID: 512 (AAPL)
UPDATE signals SET
  base_combined_score = 24.61,
  alignment_bonus = 0,
  combined_score = 24.61,
  base_confidence = 0.7987,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 512 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.61,
  alignment_bonus = 0,
  combined_score = 24.61,
  base_confidence = 0.7987,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 512;

-- Signal ID: 511 (NVDA)
UPDATE signals SET
  base_combined_score = 1.62,
  alignment_bonus = 0,
  combined_score = 1.62,
  base_confidence = 0.812,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 511 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.62,
  alignment_bonus = 0,
  combined_score = 1.62,
  base_confidence = 0.812,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 511;

-- Signal ID: 510 (MSFT)
UPDATE signals SET
  base_combined_score = 6.85,
  alignment_bonus = 0,
  combined_score = 6.85,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 510 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.85,
  alignment_bonus = 0,
  combined_score = 6.85,
  base_confidence = 0.7895,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 510;

-- Signal ID: 509 (TSLA)
UPDATE signals SET
  base_combined_score = -0.48,
  alignment_bonus = 0,
  combined_score = -0.48,
  base_confidence = 0.7904,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 509 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.48,
  alignment_bonus = 0,
  combined_score = -0.48,
  base_confidence = 0.7904,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 509;

-- Signal ID: 508 (AAPL)
UPDATE signals SET
  base_combined_score = 24.61,
  alignment_bonus = 0,
  combined_score = 24.61,
  base_confidence = 0.7987,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 508 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.61,
  alignment_bonus = 0,
  combined_score = 24.61,
  base_confidence = 0.7987,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 508;

-- Signal ID: 507 (OTP.BD)
UPDATE signals SET
  base_combined_score = 21.63,
  alignment_bonus = 0,
  combined_score = 21.63,
  base_confidence = 0.6685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 507 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 21.63,
  alignment_bonus = 0,
  combined_score = 21.63,
  base_confidence = 0.6685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 507;

-- Signal ID: 506 (MOL.BD)
UPDATE signals SET
  base_combined_score = 20.38,
  alignment_bonus = 0,
  combined_score = 20.38,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 506 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.38,
  alignment_bonus = 0,
  combined_score = 20.38,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 506;

-- Signal ID: 505 (NVDA)
UPDATE signals SET
  base_combined_score = 5.12,
  alignment_bonus = 0,
  combined_score = 5.12,
  base_confidence = 0.722,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 505 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.12,
  alignment_bonus = 0,
  combined_score = 5.12,
  base_confidence = 0.722,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 505;

-- Signal ID: 504 (MOL.BD)
UPDATE signals SET
  base_combined_score = 10.15,
  alignment_bonus = 0,
  combined_score = 10.15,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 504 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.15,
  alignment_bonus = 0,
  combined_score = 10.15,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 504;

-- Signal ID: 503 (OTP.BD)
UPDATE signals SET
  base_combined_score = 33.74,
  alignment_bonus = 0,
  combined_score = 33.74,
  base_confidence = 0.6685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 503 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 33.74,
  alignment_bonus = 0,
  combined_score = 33.74,
  base_confidence = 0.6685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 503;

-- Signal ID: 502 (TSLA)
UPDATE signals SET
  base_combined_score = 4.63,
  alignment_bonus = 0,
  combined_score = 4.63,
  base_confidence = 0.7029,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 502 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.63,
  alignment_bonus = 0,
  combined_score = 4.63,
  base_confidence = 0.7029,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 502;

-- Signal ID: 501 (GOOGL)
UPDATE signals SET
  base_combined_score = 12.49,
  alignment_bonus = 0,
  combined_score = 12.49,
  base_confidence = 0.782,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 501 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.49,
  alignment_bonus = 0,
  combined_score = 12.49,
  base_confidence = 0.782,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 501;

-- Signal ID: 500 (MSFT)
UPDATE signals SET
  base_combined_score = 6.28,
  alignment_bonus = 0,
  combined_score = 6.28,
  base_confidence = 0.788,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 500 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.28,
  alignment_bonus = 0,
  combined_score = 6.28,
  base_confidence = 0.788,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 500;

-- Signal ID: 499 (AAPL)
UPDATE signals SET
  base_combined_score = 0.8,
  alignment_bonus = 0,
  combined_score = 0.8,
  base_confidence = 0.798,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 499 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.8,
  alignment_bonus = 0,
  combined_score = 0.8,
  base_confidence = 0.798,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 499;

-- Signal ID: 498 (NVDA)
UPDATE signals SET
  base_combined_score = 0.68,
  alignment_bonus = 0,
  combined_score = 0.68,
  base_confidence = 0.8095,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 498 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.68,
  alignment_bonus = 0,
  combined_score = 0.68,
  base_confidence = 0.8095,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 498;

-- Signal ID: 497 (MSFT)
UPDATE signals SET
  base_combined_score = -2.87,
  alignment_bonus = 0,
  combined_score = -2.87,
  base_confidence = 0.7005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 497 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.87,
  alignment_bonus = 0,
  combined_score = -2.87,
  base_confidence = 0.7005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 497;

-- Signal ID: 496 (TSLA)
UPDATE signals SET
  base_combined_score = 0.05,
  alignment_bonus = 0,
  combined_score = 0.05,
  base_confidence = 0.7009,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 496 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.05,
  alignment_bonus = 0,
  combined_score = 0.05,
  base_confidence = 0.7009,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 496;

-- Signal ID: 495 (AAPL)
UPDATE signals SET
  base_combined_score = 0.28,
  alignment_bonus = 0,
  combined_score = 0.28,
  base_confidence = 0.798,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 495 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.28,
  alignment_bonus = 0,
  combined_score = 0.28,
  base_confidence = 0.798,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 495;

-- Signal ID: 494 (OTP.BD)
UPDATE signals SET
  base_combined_score = 32.14,
  alignment_bonus = 0,
  combined_score = 32.14,
  base_confidence = 0.6775,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 494 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 32.14,
  alignment_bonus = 0,
  combined_score = 32.14,
  base_confidence = 0.6775,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 494;

-- Signal ID: 493 (MOL.BD)
UPDATE signals SET
  base_combined_score = -4.51,
  alignment_bonus = 0,
  combined_score = -4.51,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 493 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -4.51,
  alignment_bonus = 0,
  combined_score = -4.51,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 493;

-- Signal ID: 492 (NVDA)
UPDATE signals SET
  base_combined_score = -0.12,
  alignment_bonus = 0,
  combined_score = -0.12,
  base_confidence = 0.7165,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 492 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.12,
  alignment_bonus = 0,
  combined_score = -0.12,
  base_confidence = 0.7165,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 492;

-- Signal ID: 491 (MOL.BD)
UPDATE signals SET
  base_combined_score = -4.51,
  alignment_bonus = 0,
  combined_score = -4.51,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 491 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -4.51,
  alignment_bonus = 0,
  combined_score = -4.51,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 491;

-- Signal ID: 490 (OTP.BD)
UPDATE signals SET
  base_combined_score = 32.14,
  alignment_bonus = 0,
  combined_score = 32.14,
  base_confidence = 0.6775,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 490 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 32.14,
  alignment_bonus = 0,
  combined_score = 32.14,
  base_confidence = 0.6775,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 490;

-- Signal ID: 489 (TSLA)
UPDATE signals SET
  base_combined_score = 2.84,
  alignment_bonus = 0,
  combined_score = 2.84,
  base_confidence = 0.7009,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 489 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 2.84,
  alignment_bonus = 0,
  combined_score = 2.84,
  base_confidence = 0.7009,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 489;

-- Signal ID: 488 (GOOGL)
UPDATE signals SET
  base_combined_score = 12.58,
  alignment_bonus = 0,
  combined_score = 12.58,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 488 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.58,
  alignment_bonus = 0,
  combined_score = 12.58,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 488;

-- Signal ID: 487 (MSFT)
UPDATE signals SET
  base_combined_score = -1.13,
  alignment_bonus = 0,
  combined_score = -1.13,
  base_confidence = 0.7005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 487 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.13,
  alignment_bonus = 0,
  combined_score = -1.13,
  base_confidence = 0.7005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 487;

-- Signal ID: 486 (AAPL)
UPDATE signals SET
  base_combined_score = 2.99,
  alignment_bonus = 0,
  combined_score = 2.99,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 486 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 2.99,
  alignment_bonus = 0,
  combined_score = 2.99,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 486;

-- Signal ID: 485 (NVDA)
UPDATE signals SET
  base_combined_score = 6.99,
  alignment_bonus = 0,
  combined_score = 6.99,
  base_confidence = 0.723,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 485 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.99,
  alignment_bonus = 0,
  combined_score = 6.99,
  base_confidence = 0.723,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 485;

-- Signal ID: 484 (MOL.BD)
UPDATE signals SET
  base_combined_score = -4.51,
  alignment_bonus = 0,
  combined_score = -4.51,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 484 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -4.51,
  alignment_bonus = 0,
  combined_score = -4.51,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 484;

-- Signal ID: 483 (OTP.BD)
UPDATE signals SET
  base_combined_score = 32.97,
  alignment_bonus = 0,
  combined_score = 32.97,
  base_confidence = 0.6775,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 483 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 32.97,
  alignment_bonus = 0,
  combined_score = 32.97,
  base_confidence = 0.6775,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 483;

-- Signal ID: 482 (TSLA)
UPDATE signals SET
  base_combined_score = 7.81,
  alignment_bonus = 0,
  combined_score = 7.81,
  base_confidence = 0.7884,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 482 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.81,
  alignment_bonus = 0,
  combined_score = 7.81,
  base_confidence = 0.7884,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 482;

-- Signal ID: 481 (GOOGL)
UPDATE signals SET
  base_combined_score = 19.94,
  alignment_bonus = 0,
  combined_score = 19.94,
  base_confidence = 0.7035,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 481 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 19.94,
  alignment_bonus = 0,
  combined_score = 19.94,
  base_confidence = 0.7035,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 481;

-- Signal ID: 480 (MSFT)
UPDATE signals SET
  base_combined_score = -2.62,
  alignment_bonus = 0,
  combined_score = -2.62,
  base_confidence = 0.701,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 480 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.62,
  alignment_bonus = 0,
  combined_score = -2.62,
  base_confidence = 0.701,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 480;

-- Signal ID: 479 (AAPL)
UPDATE signals SET
  base_combined_score = 4.4,
  alignment_bonus = 0,
  combined_score = 4.4,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 479 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.4,
  alignment_bonus = 0,
  combined_score = 4.4,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 479;

-- Signal ID: 478 (NVDA)
UPDATE signals SET
  base_combined_score = 13.28,
  alignment_bonus = 0,
  combined_score = 13.28,
  base_confidence = 0.804,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 478 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.28,
  alignment_bonus = 0,
  combined_score = 13.28,
  base_confidence = 0.804,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 478;

-- Signal ID: 477 (MOL.BD)
UPDATE signals SET
  base_combined_score = 4.88,
  alignment_bonus = 0,
  combined_score = 4.88,
  base_confidence = 0.6861,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 477 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.88,
  alignment_bonus = 0,
  combined_score = 4.88,
  base_confidence = 0.6861,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 477;

-- Signal ID: 476 (OTP.BD)
UPDATE signals SET
  base_combined_score = 8.35,
  alignment_bonus = 0,
  combined_score = 8.35,
  base_confidence = 0.7612,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 476 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.35,
  alignment_bonus = 0,
  combined_score = 8.35,
  base_confidence = 0.7612,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 476;

-- Signal ID: 475 (TSLA)
UPDATE signals SET
  base_combined_score = -10.38,
  alignment_bonus = 0,
  combined_score = -10.38,
  base_confidence = 0.7884,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 475 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -10.38,
  alignment_bonus = 0,
  combined_score = -10.38,
  base_confidence = 0.7884,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 475;

-- Signal ID: 474 (GOOGL)
UPDATE signals SET
  base_combined_score = 29.22,
  alignment_bonus = 0,
  combined_score = 29.22,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 474 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 29.22,
  alignment_bonus = 0,
  combined_score = 29.22,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 474;

-- Signal ID: 473 (MSFT)
UPDATE signals SET
  base_combined_score = 5.94,
  alignment_bonus = 0,
  combined_score = 5.94,
  base_confidence = 0.7845,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 473 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.94,
  alignment_bonus = 0,
  combined_score = 5.94,
  base_confidence = 0.7845,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 473;

-- Signal ID: 472 (AAPL)
UPDATE signals SET
  base_combined_score = 6.42,
  alignment_bonus = 0,
  combined_score = 6.42,
  base_confidence = 0.8,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 472 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 6.42,
  alignment_bonus = 0,
  combined_score = 6.42,
  base_confidence = 0.8,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 472;

-- Signal ID: 471 (NVDA)
UPDATE signals SET
  base_combined_score = 11.78,
  alignment_bonus = 0,
  combined_score = 11.78,
  base_confidence = 0.804,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 471 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.78,
  alignment_bonus = 0,
  combined_score = 11.78,
  base_confidence = 0.804,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 471;

-- Signal ID: 470 (MSFT)
UPDATE signals SET
  base_combined_score = 5.94,
  alignment_bonus = 0,
  combined_score = 5.94,
  base_confidence = 0.7845,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 470 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.94,
  alignment_bonus = 0,
  combined_score = 5.94,
  base_confidence = 0.7845,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 470;

-- Signal ID: 469 (TSLA)
UPDATE signals SET
  base_combined_score = -10.38,
  alignment_bonus = 0,
  combined_score = -10.38,
  base_confidence = 0.7884,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 469 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -10.38,
  alignment_bonus = 0,
  combined_score = -10.38,
  base_confidence = 0.7884,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 469;

-- Signal ID: 468 (AAPL)
UPDATE signals SET
  base_combined_score = 4.79,
  alignment_bonus = 0,
  combined_score = 4.79,
  base_confidence = 0.803,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 468 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.79,
  alignment_bonus = 0,
  combined_score = 4.79,
  base_confidence = 0.803,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 468;

-- Signal ID: 467 (OTP.BD)
UPDATE signals SET
  base_combined_score = 8.35,
  alignment_bonus = 0,
  combined_score = 8.35,
  base_confidence = 0.7612,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 467 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.35,
  alignment_bonus = 0,
  combined_score = 8.35,
  base_confidence = 0.7612,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 467;

-- Signal ID: 466 (MOL.BD)
UPDATE signals SET
  base_combined_score = 4.88,
  alignment_bonus = 0,
  combined_score = 4.88,
  base_confidence = 0.6861,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 466 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.88,
  alignment_bonus = 0,
  combined_score = 4.88,
  base_confidence = 0.6861,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 466;

-- Signal ID: 465 (NVDA)
UPDATE signals SET
  base_combined_score = 13.3,
  alignment_bonus = 0,
  combined_score = 13.3,
  base_confidence = 0.804,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 465 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.3,
  alignment_bonus = 0,
  combined_score = 13.3,
  base_confidence = 0.804,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 465;

-- Signal ID: 464 (MOL.BD)
UPDATE signals SET
  base_combined_score = 4.88,
  alignment_bonus = 0,
  combined_score = 4.88,
  base_confidence = 0.6861,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 464 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.88,
  alignment_bonus = 0,
  combined_score = 4.88,
  base_confidence = 0.6861,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 464;

-- Signal ID: 463 (OTP.BD)
UPDATE signals SET
  base_combined_score = 8.35,
  alignment_bonus = 0,
  combined_score = 8.35,
  base_confidence = 0.7612,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 463 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.35,
  alignment_bonus = 0,
  combined_score = 8.35,
  base_confidence = 0.7612,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 463;

-- Signal ID: 462 (TSLA)
UPDATE signals SET
  base_combined_score = -5.94,
  alignment_bonus = 0,
  combined_score = -5.94,
  base_confidence = 0.7939,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 462 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -5.94,
  alignment_bonus = 0,
  combined_score = -5.94,
  base_confidence = 0.7939,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 462;

-- Signal ID: 461 (GOOGL)
UPDATE signals SET
  base_combined_score = 29.22,
  alignment_bonus = 0,
  combined_score = 29.22,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 461 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 29.22,
  alignment_bonus = 0,
  combined_score = 29.22,
  base_confidence = 0.791,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 461;

-- Signal ID: 460 (MSFT)
UPDATE signals SET
  base_combined_score = 10.51,
  alignment_bonus = 0,
  combined_score = 10.51,
  base_confidence = 0.7905,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 460 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.51,
  alignment_bonus = 0,
  combined_score = 10.51,
  base_confidence = 0.7905,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 460;

-- Signal ID: 459 (AAPL)
UPDATE signals SET
  base_combined_score = 4.79,
  alignment_bonus = 0,
  combined_score = 4.79,
  base_confidence = 0.803,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 459 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.79,
  alignment_bonus = 0,
  combined_score = 4.79,
  base_confidence = 0.803,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 459;

-- Signal ID: 458 (NVDA)
UPDATE signals SET
  base_combined_score = -11.45,
  alignment_bonus = 0,
  combined_score = -11.45,
  base_confidence = 0.8025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 458 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -11.45,
  alignment_bonus = 0,
  combined_score = -11.45,
  base_confidence = 0.8025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 458;

-- Signal ID: 457 (MSFT)
UPDATE signals SET
  base_combined_score = 8.53,
  alignment_bonus = 0,
  combined_score = 8.53,
  base_confidence = 0.7845,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 457 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.53,
  alignment_bonus = 0,
  combined_score = 8.53,
  base_confidence = 0.7845,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 457;

-- Signal ID: 456 (TSLA)
UPDATE signals SET
  base_combined_score = 18.26,
  alignment_bonus = 0,
  combined_score = 18.26,
  base_confidence = 0.7989,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 456 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.26,
  alignment_bonus = 0,
  combined_score = 18.26,
  base_confidence = 0.7989,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 456;

-- Signal ID: 455 (AAPL)
UPDATE signals SET
  base_combined_score = 5.5,
  alignment_bonus = 0,
  combined_score = 5.5,
  base_confidence = 0.8005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 455 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.5,
  alignment_bonus = 0,
  combined_score = 5.5,
  base_confidence = 0.8005,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 455;

-- Signal ID: 454 (OTP.BD)
UPDATE signals SET
  base_combined_score = 11.92,
  alignment_bonus = 0,
  combined_score = 11.92,
  base_confidence = 0.775,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 454 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.92,
  alignment_bonus = 0,
  combined_score = 11.92,
  base_confidence = 0.775,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 454;

-- Signal ID: 453 (MOL.BD)
UPDATE signals SET
  base_combined_score = 13.25,
  alignment_bonus = 0,
  combined_score = 13.25,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 453 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.25,
  alignment_bonus = 0,
  combined_score = 13.25,
  base_confidence = 0.7342,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 453;

-- Signal ID: 452 (OTP.BD)
UPDATE signals SET
  base_combined_score = 10.83,
  alignment_bonus = 0,
  combined_score = 10.83,
  base_confidence = 0.6875,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 452 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.83,
  alignment_bonus = 0,
  combined_score = 10.83,
  base_confidence = 0.6875,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 452;

-- Signal ID: 451 (MOL.BD)
UPDATE signals SET
  base_combined_score = 14.99,
  alignment_bonus = 0,
  combined_score = 14.99,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 451 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.99,
  alignment_bonus = 0,
  combined_score = 14.99,
  base_confidence = 0.7298,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 451;

-- Signal ID: 450 (NVDA)
UPDATE signals SET
  base_combined_score = -9.98,
  alignment_bonus = 0,
  combined_score = -9.98,
  base_confidence = 0.7922,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 450 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.98,
  alignment_bonus = 0,
  combined_score = -9.98,
  base_confidence = 0.7922,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 450;

-- Signal ID: 449 (MOL.BD)
UPDATE signals SET
  base_combined_score = 16.84,
  alignment_bonus = 0,
  combined_score = 16.84,
  base_confidence = 0.7228,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 449 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.84,
  alignment_bonus = 0,
  combined_score = 16.84,
  base_confidence = 0.7228,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 449;

-- Signal ID: 448 (OTP.BD)
UPDATE signals SET
  base_combined_score = 13.15,
  alignment_bonus = 0,
  combined_score = 13.15,
  base_confidence = 0.6995,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 448 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.15,
  alignment_bonus = 0,
  combined_score = 13.15,
  base_confidence = 0.6995,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 448;

-- Signal ID: 447 (TSLA)
UPDATE signals SET
  base_combined_score = 0.88,
  alignment_bonus = 0,
  combined_score = 0.88,
  base_confidence = 0.7989,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 447 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.88,
  alignment_bonus = 0,
  combined_score = 0.88,
  base_confidence = 0.7989,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 447;

-- Signal ID: 446 (GOOGL)
UPDATE signals SET
  base_combined_score = 35.02,
  alignment_bonus = 0,
  combined_score = 35.02,
  base_confidence = 0.8,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 446 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 35.02,
  alignment_bonus = 0,
  combined_score = 35.02,
  base_confidence = 0.8,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 446;

-- Signal ID: 445 (MSFT)
UPDATE signals SET
  base_combined_score = 3.36,
  alignment_bonus = 0,
  combined_score = 3.36,
  base_confidence = 0.7915,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 445 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.36,
  alignment_bonus = 0,
  combined_score = 3.36,
  base_confidence = 0.7915,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 445;

-- Signal ID: 444 (AAPL)
UPDATE signals SET
  base_combined_score = 7.77,
  alignment_bonus = 0,
  combined_score = 7.77,
  base_confidence = 0.794,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 444 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.77,
  alignment_bonus = 0,
  combined_score = 7.77,
  base_confidence = 0.794,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 444;

-- Signal ID: 443 (OTP.BD)
UPDATE signals SET
  base_combined_score = 10.91,
  alignment_bonus = 0,
  combined_score = 10.91,
  base_confidence = 0.673,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 443 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.91,
  alignment_bonus = 0,
  combined_score = 10.91,
  base_confidence = 0.673,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 443;

-- Signal ID: 442 (MOL.BD)
UPDATE signals SET
  base_combined_score = 24.19,
  alignment_bonus = 0,
  combined_score = 24.19,
  base_confidence = 0.676,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 442 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 24.19,
  alignment_bonus = 0,
  combined_score = 24.19,
  base_confidence = 0.676,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 442;

-- Signal ID: 441 (OTP.BD)
UPDATE signals SET
  base_combined_score = 28.95,
  alignment_bonus = 0,
  combined_score = 28.95,
  base_confidence = 0.6795,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 441 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 28.95,
  alignment_bonus = 0,
  combined_score = 28.95,
  base_confidence = 0.6795,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 441;

-- Signal ID: 440 (MOL.BD)
UPDATE signals SET
  base_combined_score = 3.93,
  alignment_bonus = 0,
  combined_score = 3.93,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 440 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.93,
  alignment_bonus = 0,
  combined_score = 3.93,
  base_confidence = 0.712,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 440;

-- Signal ID: 439 (OTP.BD)
UPDATE signals SET
  base_combined_score = 38.56,
  alignment_bonus = 0,
  combined_score = 38.56,
  base_confidence = 0.6795,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 439 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 38.56,
  alignment_bonus = 0,
  combined_score = 38.56,
  base_confidence = 0.6795,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 439;

-- Signal ID: 438 (MOL.BD)
UPDATE signals SET
  base_combined_score = 3.89,
  alignment_bonus = 0,
  combined_score = 3.89,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 438 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.89,
  alignment_bonus = 0,
  combined_score = 3.89,
  base_confidence = 0.7225,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 438;

-- Signal ID: 437 (OTP.BD)
UPDATE signals SET
  base_combined_score = 41.55,
  alignment_bonus = 5,
  combined_score = 46.55,
  base_confidence = 0.767,
  confidence_boost = 0.025,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 437 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 41.55,
  alignment_bonus = 5,
  combined_score = 46.55,
  base_confidence = 0.767,
  confidence_boost = 0.025,
  strength = 'MODERATE'
WHERE signal_id = 437;

-- Signal ID: 436 (MOL.BD)
UPDATE signals SET
  base_combined_score = 18.93,
  alignment_bonus = 0,
  combined_score = 18.93,
  base_confidence = 0.7245,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 436 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.93,
  alignment_bonus = 0,
  combined_score = 18.93,
  base_confidence = 0.7245,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 436;

-- Signal ID: 435 (MOL.BD)
UPDATE signals SET
  base_combined_score = 18.82,
  alignment_bonus = 0,
  combined_score = 18.82,
  base_confidence = 0.7245,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 435 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.82,
  alignment_bonus = 0,
  combined_score = 18.82,
  base_confidence = 0.7245,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 435;

-- Signal ID: 434 (OTP.BD)
UPDATE signals SET
  base_combined_score = 40.88,
  alignment_bonus = 5,
  combined_score = 45.88,
  base_confidence = 0.767,
  confidence_boost = 0.025,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 434 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 40.88,
  alignment_bonus = 5,
  combined_score = 45.88,
  base_confidence = 0.767,
  confidence_boost = 0.025,
  strength = 'MODERATE'
WHERE signal_id = 434;

-- Signal ID: 433 (TSLA)
UPDATE signals SET
  base_combined_score = 0.1,
  alignment_bonus = 0,
  combined_score = 0.1,
  base_confidence = 0.7934,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 433 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.1,
  alignment_bonus = 0,
  combined_score = 0.1,
  base_confidence = 0.7934,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 433;

-- Signal ID: 432 (GOOGL)
UPDATE signals SET
  base_combined_score = 21.93,
  alignment_bonus = 0,
  combined_score = 21.93,
  base_confidence = 0.805,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 432 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 21.93,
  alignment_bonus = 0,
  combined_score = 21.93,
  base_confidence = 0.805,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 432;

-- Signal ID: 431 (MSFT)
UPDATE signals SET
  base_combined_score = -6.41,
  alignment_bonus = 0,
  combined_score = -6.41,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 431 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -6.41,
  alignment_bonus = 0,
  combined_score = -6.41,
  base_confidence = 0.7995,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 431;

-- Signal ID: 430 (AAPL)
UPDATE signals SET
  base_combined_score = 11.79,
  alignment_bonus = 0,
  combined_score = 11.79,
  base_confidence = 0.8025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 430 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.79,
  alignment_bonus = 0,
  combined_score = 11.79,
  base_confidence = 0.8025,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 430;

-- Signal ID: 429 (OTP.BD)
UPDATE signals SET
  base_combined_score = 33.14,
  alignment_bonus = 0,
  combined_score = 33.14,
  base_confidence = 0.6795,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 429 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 33.14,
  alignment_bonus = 0,
  combined_score = 33.14,
  base_confidence = 0.6795,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 429;

-- Signal ID: 428 (MOL.BD)
UPDATE signals SET
  base_combined_score = 16.59,
  alignment_bonus = 0,
  combined_score = 16.59,
  base_confidence = 0.7285,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 428 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.59,
  alignment_bonus = 0,
  combined_score = 16.59,
  base_confidence = 0.7285,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 428;

-- Signal ID: 427 (OTP.BD)
UPDATE signals SET
  base_combined_score = 33.37,
  alignment_bonus = 0,
  combined_score = 33.37,
  base_confidence = 0.767,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 427 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 33.37,
  alignment_bonus = 0,
  combined_score = 33.37,
  base_confidence = 0.767,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 427;

-- Signal ID: 426 (MOL.BD)
UPDATE signals SET
  base_combined_score = 13.5,
  alignment_bonus = 0,
  combined_score = 13.5,
  base_confidence = 0.637,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 426 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.5,
  alignment_bonus = 0,
  combined_score = 13.5,
  base_confidence = 0.637,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 426;

-- Signal ID: 425 (MOL.BD)
UPDATE signals SET
  base_combined_score = 9.14,
  alignment_bonus = 0,
  combined_score = 9.14,
  base_confidence = 0.7245,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 425 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.14,
  alignment_bonus = 0,
  combined_score = 9.14,
  base_confidence = 0.7245,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 425;

-- Signal ID: 424 (OTP.BD)
UPDATE signals SET
  base_combined_score = 28.82,
  alignment_bonus = 0,
  combined_score = 28.82,
  base_confidence = 0.781,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 424 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 28.82,
  alignment_bonus = 0,
  combined_score = 28.82,
  base_confidence = 0.781,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 424;

-- Signal ID: 423 (TSLA)
UPDATE signals SET
  base_combined_score = 4.26,
  alignment_bonus = 0,
  combined_score = 4.26,
  base_confidence = 0.7944,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 423 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 4.26,
  alignment_bonus = 0,
  combined_score = 4.26,
  base_confidence = 0.7944,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 423;

-- Signal ID: 422 (GOOGL)
UPDATE signals SET
  base_combined_score = 16.23,
  alignment_bonus = 0,
  combined_score = 16.23,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 422 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.23,
  alignment_bonus = 0,
  combined_score = 16.23,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 422;

-- Signal ID: 421 (MSFT)
UPDATE signals SET
  base_combined_score = -12.4,
  alignment_bonus = 0,
  combined_score = -12.4,
  base_confidence = 0.817,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 421 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -12.4,
  alignment_bonus = 0,
  combined_score = -12.4,
  base_confidence = 0.817,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 421;

-- Signal ID: 420 (AAPL)
UPDATE signals SET
  base_combined_score = 16.02,
  alignment_bonus = 0,
  combined_score = 16.02,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 420 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.02,
  alignment_bonus = 0,
  combined_score = 16.02,
  base_confidence = 0.7935,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 420;

-- Signal ID: 419 (OTP.BD)
UPDATE signals SET
  base_combined_score = 31.79,
  alignment_bonus = 0,
  combined_score = 31.79,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 419 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.79,
  alignment_bonus = 0,
  combined_score = 31.79,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 419;

-- Signal ID: 418 (MOL.BD)
UPDATE signals SET
  base_combined_score = 10.91,
  alignment_bonus = 0,
  combined_score = 10.91,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 418 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 10.91,
  alignment_bonus = 0,
  combined_score = 10.91,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 418;

-- Signal ID: 417 (OTP.BD)
UPDATE signals SET
  base_combined_score = 35.76,
  alignment_bonus = 0,
  combined_score = 35.76,
  base_confidence = 0.7825,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 417 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 35.76,
  alignment_bonus = 0,
  combined_score = 35.76,
  base_confidence = 0.7825,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 417;

-- Signal ID: 416 (MOL.BD)
UPDATE signals SET
  base_combined_score = 15.83,
  alignment_bonus = 0,
  combined_score = 15.83,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 416 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.83,
  alignment_bonus = 0,
  combined_score = 15.83,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 416;

-- Signal ID: 415 (OTP.BD)
UPDATE signals SET
  base_combined_score = 28.88,
  alignment_bonus = 0,
  combined_score = 28.88,
  base_confidence = 0.7825,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 415 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 28.88,
  alignment_bonus = 0,
  combined_score = 28.88,
  base_confidence = 0.7825,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 415;

-- Signal ID: 414 (MOL.BD)
UPDATE signals SET
  base_combined_score = 9.85,
  alignment_bonus = 0,
  combined_score = 9.85,
  base_confidence = 0.6475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 414 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 9.85,
  alignment_bonus = 0,
  combined_score = 9.85,
  base_confidence = 0.6475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 414;

-- Signal ID: 413 (OTP.BD)
UPDATE signals SET
  base_combined_score = 33.37,
  alignment_bonus = 0,
  combined_score = 33.37,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 413 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 33.37,
  alignment_bonus = 0,
  combined_score = 33.37,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 413;

-- Signal ID: 412 (MOL.BD)
UPDATE signals SET
  base_combined_score = 14.93,
  alignment_bonus = 0,
  combined_score = 14.93,
  base_confidence = 0.6475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 412 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 14.93,
  alignment_bonus = 0,
  combined_score = 14.93,
  base_confidence = 0.6475,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 412;

-- Signal ID: 411 (OTP.BD)
UPDATE signals SET
  base_combined_score = 31.79,
  alignment_bonus = 0,
  combined_score = 31.79,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 411 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.79,
  alignment_bonus = 0,
  combined_score = 31.79,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 411;

-- Signal ID: 410 (MOL.BD)
UPDATE signals SET
  base_combined_score = 12.49,
  alignment_bonus = 0,
  combined_score = 12.49,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 410 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.49,
  alignment_bonus = 0,
  combined_score = 12.49,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 410;

-- Signal ID: 409 (OTP.BD)
UPDATE signals SET
  base_combined_score = 31.25,
  alignment_bonus = 0,
  combined_score = 31.25,
  base_confidence = 0.7825,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 409 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.25,
  alignment_bonus = 0,
  combined_score = 31.25,
  base_confidence = 0.7825,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 409;

-- Signal ID: 408 (MOL.BD)
UPDATE signals SET
  base_combined_score = 23.07,
  alignment_bonus = 0,
  combined_score = 23.07,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 408 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.07,
  alignment_bonus = 0,
  combined_score = 23.07,
  base_confidence = 0.735,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 408;

-- Signal ID: 407 (MOL.BD)
UPDATE signals SET
  base_combined_score = 11.38,
  alignment_bonus = 0,
  combined_score = 11.38,
  base_confidence = 0.6885,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 407 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.38,
  alignment_bonus = 0,
  combined_score = 11.38,
  base_confidence = 0.6885,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 407;

-- Signal ID: 406 (OTP.BD)
UPDATE signals SET
  base_combined_score = 41.79,
  alignment_bonus = 0,
  combined_score = 41.79,
  base_confidence = 0.7542,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 406 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 41.79,
  alignment_bonus = 0,
  combined_score = 41.79,
  base_confidence = 0.7542,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 406;

-- Signal ID: 405 (TSLA)
UPDATE signals SET
  base_combined_score = 17.13,
  alignment_bonus = 0,
  combined_score = 17.13,
  base_confidence = 0.7818,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 405 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 17.13,
  alignment_bonus = 0,
  combined_score = 17.13,
  base_confidence = 0.7818,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 405;

-- Signal ID: 404 (GOOGL)
UPDATE signals SET
  base_combined_score = 15.47,
  alignment_bonus = 0,
  combined_score = 15.47,
  base_confidence = 0.7762,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 404 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.47,
  alignment_bonus = 0,
  combined_score = 15.47,
  base_confidence = 0.7762,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 404;

-- Signal ID: 403 (MSFT)
UPDATE signals SET
  base_combined_score = -16.7,
  alignment_bonus = 0,
  combined_score = -16.7,
  base_confidence = 0.8028,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 403 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -16.7,
  alignment_bonus = 0,
  combined_score = -16.7,
  base_confidence = 0.8028,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 403;

-- Signal ID: 402 (AAPL)
UPDATE signals SET
  base_combined_score = 22.74,
  alignment_bonus = 0,
  combined_score = 22.74,
  base_confidence = 0.7832,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 402 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 22.74,
  alignment_bonus = 0,
  combined_score = 22.74,
  base_confidence = 0.7832,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 402;

-- Signal ID: 401 (OTP.BD)
UPDATE signals SET
  base_combined_score = 42.79,
  alignment_bonus = 0,
  combined_score = 42.79,
  base_confidence = 0.7542,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 401 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 42.79,
  alignment_bonus = 0,
  combined_score = 42.79,
  base_confidence = 0.7542,
  confidence_boost = 0.0,
  strength = 'MODERATE'
WHERE signal_id = 401;

-- Signal ID: 400 (MOL.BD)
UPDATE signals SET
  base_combined_score = 3.04,
  alignment_bonus = 0,
  combined_score = 3.04,
  base_confidence = 0.6885,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 400 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 3.04,
  alignment_bonus = 0,
  combined_score = 3.04,
  base_confidence = 0.6885,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 400;

-- Signal ID: 399 (MOL.BD)
UPDATE signals SET
  base_combined_score = -4.67,
  alignment_bonus = 0,
  combined_score = -4.67,
  base_confidence = 0.678,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 399 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -4.67,
  alignment_bonus = 0,
  combined_score = -4.67,
  base_confidence = 0.678,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 399;

-- Signal ID: 398 (OTP.BD)
UPDATE signals SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 398 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 398;

-- Signal ID: 397 (TSLA)
UPDATE signals SET
  base_combined_score = 13.02,
  alignment_bonus = 0,
  combined_score = 13.02,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 397 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.02,
  alignment_bonus = 0,
  combined_score = 13.02,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 397;

-- Signal ID: 396 (GOOGL)
UPDATE signals SET
  base_combined_score = 23.76,
  alignment_bonus = 0,
  combined_score = 23.76,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 396 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.76,
  alignment_bonus = 0,
  combined_score = 23.76,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 396;

-- Signal ID: 395 (MSFT)
UPDATE signals SET
  base_combined_score = -9.24,
  alignment_bonus = 0,
  combined_score = -9.24,
  base_confidence = 0.793,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 395 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.24,
  alignment_bonus = 0,
  combined_score = -9.24,
  base_confidence = 0.793,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 395;

-- Signal ID: 394 (AAPL)
UPDATE signals SET
  base_combined_score = 17.62,
  alignment_bonus = 0,
  combined_score = 17.62,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 394 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 17.62,
  alignment_bonus = 0,
  combined_score = 17.62,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 394;

-- Signal ID: 393 (MOL.BD)
UPDATE signals SET
  base_combined_score = -4.67,
  alignment_bonus = 0,
  combined_score = -4.67,
  base_confidence = 0.678,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 393 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -4.67,
  alignment_bonus = 0,
  combined_score = -4.67,
  base_confidence = 0.678,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 393;

-- Signal ID: 392 (OTP.BD)
UPDATE signals SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 392 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 392;

-- Signal ID: 391 (TSLA)
UPDATE signals SET
  base_combined_score = 13.02,
  alignment_bonus = 0,
  combined_score = 13.02,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 391 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.02,
  alignment_bonus = 0,
  combined_score = 13.02,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 391;

-- Signal ID: 390 (GOOGL)
UPDATE signals SET
  base_combined_score = 23.76,
  alignment_bonus = 0,
  combined_score = 23.76,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 390 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.76,
  alignment_bonus = 0,
  combined_score = 23.76,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 390;

-- Signal ID: 389 (MSFT)
UPDATE signals SET
  base_combined_score = -9.24,
  alignment_bonus = 0,
  combined_score = -9.24,
  base_confidence = 0.793,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 389 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -9.24,
  alignment_bonus = 0,
  combined_score = -9.24,
  base_confidence = 0.793,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 389;

-- Signal ID: 388 (AAPL)
UPDATE signals SET
  base_combined_score = 17.62,
  alignment_bonus = 0,
  combined_score = 17.62,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 388 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 17.62,
  alignment_bonus = 0,
  combined_score = 17.62,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 388;

-- Signal ID: 387 (MOL.BD)
UPDATE signals SET
  base_combined_score = -7.78,
  alignment_bonus = 0,
  combined_score = -7.78,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 387 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -7.78,
  alignment_bonus = 0,
  combined_score = -7.78,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 387;

-- Signal ID: 386 (OTP.BD)
UPDATE signals SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 386 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 386;

-- Signal ID: 385 (TSLA)
UPDATE signals SET
  base_combined_score = 8.32,
  alignment_bonus = 0,
  combined_score = 8.32,
  base_confidence = 0.7692,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 385 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.32,
  alignment_bonus = 0,
  combined_score = 8.32,
  base_confidence = 0.7692,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 385;

-- Signal ID: 384 (GOOGL)
UPDATE signals SET
  base_combined_score = 15.48,
  alignment_bonus = 0,
  combined_score = 15.48,
  base_confidence = 0.7475,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 384 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.48,
  alignment_bonus = 0,
  combined_score = 15.48,
  base_confidence = 0.7475,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 384;

-- Signal ID: 383 (MSFT)
UPDATE signals SET
  base_combined_score = -7.79,
  alignment_bonus = 0,
  combined_score = -7.79,
  base_confidence = 0.786,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 383 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -7.79,
  alignment_bonus = 0,
  combined_score = -7.79,
  base_confidence = 0.786,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 383;

-- Signal ID: 382 (AAPL)
UPDATE signals SET
  base_combined_score = 19.77,
  alignment_bonus = 0,
  combined_score = 19.77,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 382 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 19.77,
  alignment_bonus = 0,
  combined_score = 19.77,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 382;

-- Signal ID: 381 (MOL.BD)
UPDATE signals SET
  base_combined_score = -7.78,
  alignment_bonus = 0,
  combined_score = -7.78,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 381 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -7.78,
  alignment_bonus = 0,
  combined_score = -7.78,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 381;

-- Signal ID: 380 (OTP.BD)
UPDATE signals SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 380 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 380;

-- Signal ID: 379 (TSLA)
UPDATE signals SET
  base_combined_score = 8.32,
  alignment_bonus = 0,
  combined_score = 8.32,
  base_confidence = 0.7692,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 379 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.32,
  alignment_bonus = 0,
  combined_score = 8.32,
  base_confidence = 0.7692,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 379;

-- Signal ID: 378 (GOOGL)
UPDATE signals SET
  base_combined_score = 15.48,
  alignment_bonus = 0,
  combined_score = 15.48,
  base_confidence = 0.7475,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 378 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.48,
  alignment_bonus = 0,
  combined_score = 15.48,
  base_confidence = 0.7475,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 378;

-- Signal ID: 377 (MSFT)
UPDATE signals SET
  base_combined_score = -7.79,
  alignment_bonus = 0,
  combined_score = -7.79,
  base_confidence = 0.786,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 377 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -7.79,
  alignment_bonus = 0,
  combined_score = -7.79,
  base_confidence = 0.786,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 377;

-- Signal ID: 376 (AAPL)
UPDATE signals SET
  base_combined_score = 19.77,
  alignment_bonus = 0,
  combined_score = 19.77,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 376 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 19.77,
  alignment_bonus = 0,
  combined_score = 19.77,
  base_confidence = 0.7748,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 376;

-- Signal ID: 375 (MOL.BD)
UPDATE signals SET
  base_combined_score = -7.33,
  alignment_bonus = 0,
  combined_score = -7.33,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 375 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -7.33,
  alignment_bonus = 0,
  combined_score = -7.33,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 375;

-- Signal ID: 374 (OTP.BD)
UPDATE signals SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 374 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 374;

-- Signal ID: 373 (TSLA)
UPDATE signals SET
  base_combined_score = 7.41,
  alignment_bonus = 0,
  combined_score = 7.41,
  base_confidence = 0.7636,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 373 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 7.41,
  alignment_bonus = 0,
  combined_score = 7.41,
  base_confidence = 0.7636,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 373;

-- Signal ID: 372 (GOOGL)
UPDATE signals SET
  base_combined_score = 17.08,
  alignment_bonus = 0,
  combined_score = 17.08,
  base_confidence = 0.7482,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 372 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 17.08,
  alignment_bonus = 0,
  combined_score = 17.08,
  base_confidence = 0.7482,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 372;

-- Signal ID: 371 (MSFT)
UPDATE signals SET
  base_combined_score = -5.7,
  alignment_bonus = 0,
  combined_score = -5.7,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 371 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -5.7,
  alignment_bonus = 0,
  combined_score = -5.7,
  base_confidence = 0.7797,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 371;

-- Signal ID: 370 (AAPL)
UPDATE signals SET
  base_combined_score = 18.5,
  alignment_bonus = 0,
  combined_score = 18.5,
  base_confidence = 0.7727,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 370 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.5,
  alignment_bonus = 0,
  combined_score = 18.5,
  base_confidence = 0.7727,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 370;

-- Signal ID: 369 (MOL.BD)
UPDATE signals SET
  base_combined_score = -8.34,
  alignment_bonus = 0,
  combined_score = -8.34,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 369 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -8.34,
  alignment_bonus = 0,
  combined_score = -8.34,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 369;

-- Signal ID: 368 (OTP.BD)
UPDATE signals SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 368 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 368;

-- Signal ID: 367 (TSLA)
UPDATE signals SET
  base_combined_score = 5.61,
  alignment_bonus = 0,
  combined_score = 5.61,
  base_confidence = 0.7573,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 367 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.61,
  alignment_bonus = 0,
  combined_score = 5.61,
  base_confidence = 0.7573,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 367;

-- Signal ID: 366 (GOOGL)
UPDATE signals SET
  base_combined_score = 27.42,
  alignment_bonus = 0,
  combined_score = 27.42,
  base_confidence = 0.7713,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 366 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 27.42,
  alignment_bonus = 0,
  combined_score = 27.42,
  base_confidence = 0.7713,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 366;

-- Signal ID: 365 (MSFT)
UPDATE signals SET
  base_combined_score = -2.19,
  alignment_bonus = 0,
  combined_score = -2.19,
  base_confidence = 0.7727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 365 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -2.19,
  alignment_bonus = 0,
  combined_score = -2.19,
  base_confidence = 0.7727,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 365;

-- Signal ID: 364 (AAPL)
UPDATE signals SET
  base_combined_score = 20.11,
  alignment_bonus = 0,
  combined_score = 20.11,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 364 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.11,
  alignment_bonus = 0,
  combined_score = 20.11,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 364;

-- Signal ID: 363 (MOL.BD)
UPDATE signals SET
  base_combined_score = -8.34,
  alignment_bonus = 0,
  combined_score = -8.34,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 363 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -8.34,
  alignment_bonus = 0,
  combined_score = -8.34,
  base_confidence = 0.6857,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 363;

-- Signal ID: 362 (OTP.BD)
UPDATE signals SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 362 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.59,
  alignment_bonus = 0,
  combined_score = 25.59,
  base_confidence = 0.7346,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 362;

-- Signal ID: 361 (TSLA)
UPDATE signals SET
  base_combined_score = 5.61,
  alignment_bonus = 0,
  combined_score = 5.61,
  base_confidence = 0.7573,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 361 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.61,
  alignment_bonus = 0,
  combined_score = 5.61,
  base_confidence = 0.7573,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 361;

-- Signal ID: 360 (GOOGL)
UPDATE signals SET
  base_combined_score = 27.42,
  alignment_bonus = 0,
  combined_score = 27.42,
  base_confidence = 0.7713,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 360 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 27.42,
  alignment_bonus = 0,
  combined_score = 27.42,
  base_confidence = 0.7713,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 360;

-- Signal ID: 359 (MSFT)
UPDATE signals SET
  base_combined_score = -1.44,
  alignment_bonus = 0,
  combined_score = -1.44,
  base_confidence = 0.7657,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 359 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.44,
  alignment_bonus = 0,
  combined_score = -1.44,
  base_confidence = 0.7657,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 359;

-- Signal ID: 358 (AAPL)
UPDATE signals SET
  base_combined_score = 20.11,
  alignment_bonus = 0,
  combined_score = 20.11,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 358 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.11,
  alignment_bonus = 0,
  combined_score = 20.11,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 358;

-- Signal ID: 357 (MOL.BD)
UPDATE signals SET
  base_combined_score = -5.51,
  alignment_bonus = 0,
  combined_score = -5.51,
  base_confidence = 0.6829,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 357 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -5.51,
  alignment_bonus = 0,
  combined_score = -5.51,
  base_confidence = 0.6829,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 357;

-- Signal ID: 356 (OTP.BD)
UPDATE signals SET
  base_combined_score = 23.36,
  alignment_bonus = 0,
  combined_score = 23.36,
  base_confidence = 0.7122,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 356 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.36,
  alignment_bonus = 0,
  combined_score = 23.36,
  base_confidence = 0.7122,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 356;

-- Signal ID: 355 (TSLA)
UPDATE signals SET
  base_combined_score = 12.4,
  alignment_bonus = 0,
  combined_score = 12.4,
  base_confidence = 0.7783,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 355 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.4,
  alignment_bonus = 0,
  combined_score = 12.4,
  base_confidence = 0.7783,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 355;

-- Signal ID: 354 (GOOGL)
UPDATE signals SET
  base_combined_score = 26.4,
  alignment_bonus = 0,
  combined_score = 26.4,
  base_confidence = 0.7769,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 354 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 26.4,
  alignment_bonus = 0,
  combined_score = 26.4,
  base_confidence = 0.7769,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 354;

-- Signal ID: 353 (MSFT)
UPDATE signals SET
  base_combined_score = -0.66,
  alignment_bonus = 0,
  combined_score = -0.66,
  base_confidence = 0.7657,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 353 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.66,
  alignment_bonus = 0,
  combined_score = -0.66,
  base_confidence = 0.7657,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 353;

-- Signal ID: 352 (AAPL)
UPDATE signals SET
  base_combined_score = 18.11,
  alignment_bonus = 0,
  combined_score = 18.11,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 352 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.11,
  alignment_bonus = 0,
  combined_score = 18.11,
  base_confidence = 0.7706,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 352;

-- Signal ID: 351 (MOL.BD)
UPDATE signals SET
  base_combined_score = 0.64,
  alignment_bonus = 0,
  combined_score = 0.64,
  base_confidence = 0.706,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 351 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.64,
  alignment_bonus = 0,
  combined_score = 0.64,
  base_confidence = 0.706,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 351;

-- Signal ID: 350 (OTP.BD)
UPDATE signals SET
  base_combined_score = 18.86,
  alignment_bonus = 0,
  combined_score = 18.86,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 350 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.86,
  alignment_bonus = 0,
  combined_score = 18.86,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 350;

-- Signal ID: 349 (TSLA)
UPDATE signals SET
  base_combined_score = 12.56,
  alignment_bonus = 0,
  combined_score = 12.56,
  base_confidence = 0.765,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 349 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.56,
  alignment_bonus = 0,
  combined_score = 12.56,
  base_confidence = 0.765,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 349;

-- Signal ID: 348 (GOOGL)
UPDATE signals SET
  base_combined_score = 15.62,
  alignment_bonus = 0,
  combined_score = 15.62,
  base_confidence = 0.7206,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 348 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.62,
  alignment_bonus = 0,
  combined_score = 15.62,
  base_confidence = 0.7206,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 348;

-- Signal ID: 347 (MSFT)
UPDATE signals SET
  base_combined_score = -6.52,
  alignment_bonus = 0,
  combined_score = -6.52,
  base_confidence = 0.7094,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 347 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -6.52,
  alignment_bonus = 0,
  combined_score = -6.52,
  base_confidence = 0.7094,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 347;

-- Signal ID: 346 (AAPL)
UPDATE signals SET
  base_combined_score = 30.56,
  alignment_bonus = 0,
  combined_score = 30.56,
  base_confidence = 0.7762,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 346 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 30.56,
  alignment_bonus = 0,
  combined_score = 30.56,
  base_confidence = 0.7762,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 346;

-- Signal ID: 345 (MOL.BD)
UPDATE signals SET
  base_combined_score = 1.08,
  alignment_bonus = 0,
  combined_score = 1.08,
  base_confidence = 0.7193,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 345 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 1.08,
  alignment_bonus = 0,
  combined_score = 1.08,
  base_confidence = 0.7193,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 345;

-- Signal ID: 344 (OTP.BD)
UPDATE signals SET
  base_combined_score = 16.69,
  alignment_bonus = 0,
  combined_score = 16.69,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 344 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 16.69,
  alignment_bonus = 0,
  combined_score = 16.69,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 344;

-- Signal ID: 343 (TSLA)
UPDATE signals SET
  base_combined_score = 5.59,
  alignment_bonus = 0,
  combined_score = 5.59,
  base_confidence = 0.7564,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 343 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 5.59,
  alignment_bonus = 0,
  combined_score = 5.59,
  base_confidence = 0.7564,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 343;

-- Signal ID: 342 (GOOGL)
UPDATE signals SET
  base_combined_score = 8.86,
  alignment_bonus = 0,
  combined_score = 8.86,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 342 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.86,
  alignment_bonus = 0,
  combined_score = 8.86,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 342;

-- Signal ID: 341 (MSFT)
UPDATE signals SET
  base_combined_score = -1.9,
  alignment_bonus = 0,
  combined_score = -1.9,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 341 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.9,
  alignment_bonus = 0,
  combined_score = -1.9,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 341;

-- Signal ID: 340 (AAPL)
UPDATE signals SET
  base_combined_score = 25.72,
  alignment_bonus = 0,
  combined_score = 25.72,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 340 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 25.72,
  alignment_bonus = 0,
  combined_score = 25.72,
  base_confidence = 0.7685,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 340;

-- Signal ID: 339 (MOL.BD)
UPDATE signals SET
  base_combined_score = -0.55,
  alignment_bonus = 0,
  combined_score = -0.55,
  base_confidence = 0.7088,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 339 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.55,
  alignment_bonus = 0,
  combined_score = -0.55,
  base_confidence = 0.7088,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 339;

-- Signal ID: 338 (OTP.BD)
UPDATE signals SET
  base_combined_score = 18.64,
  alignment_bonus = 0,
  combined_score = 18.64,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 338 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.64,
  alignment_bonus = 0,
  combined_score = 18.64,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 338;

-- Signal ID: 337 (TSLA)
UPDATE signals SET
  base_combined_score = -1.22,
  alignment_bonus = 0,
  combined_score = -1.22,
  base_confidence = 0.7521,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 337 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.22,
  alignment_bonus = 0,
  combined_score = -1.22,
  base_confidence = 0.7521,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 337;

-- Signal ID: 336 (GOOGL)
UPDATE signals SET
  base_combined_score = 11.68,
  alignment_bonus = 0,
  combined_score = 11.68,
  base_confidence = 0.7692,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 336 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 11.68,
  alignment_bonus = 0,
  combined_score = 11.68,
  base_confidence = 0.7692,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 336;

-- Signal ID: 335 (MSFT)
UPDATE signals SET
  base_combined_score = 12.33,
  alignment_bonus = 0,
  combined_score = 12.33,
  base_confidence = 0.7741,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 335 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.33,
  alignment_bonus = 0,
  combined_score = 12.33,
  base_confidence = 0.7741,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 335;

-- Signal ID: 334 (AAPL)
UPDATE signals SET
  base_combined_score = 23.41,
  alignment_bonus = 0,
  combined_score = 23.41,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 334 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.41,
  alignment_bonus = 0,
  combined_score = 23.41,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 334;

-- Signal ID: 333 (MOL.BD)
UPDATE signals SET
  base_combined_score = -0.55,
  alignment_bonus = 0,
  combined_score = -0.55,
  base_confidence = 0.7088,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 333 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -0.55,
  alignment_bonus = 0,
  combined_score = -0.55,
  base_confidence = 0.7088,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 333;

-- Signal ID: 332 (OTP.BD)
UPDATE signals SET
  base_combined_score = 18.64,
  alignment_bonus = 0,
  combined_score = 18.64,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 332 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 18.64,
  alignment_bonus = 0,
  combined_score = 18.64,
  base_confidence = 0.6961,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 332;

-- Signal ID: 331 (TSLA)
UPDATE signals SET
  base_combined_score = -1.61,
  alignment_bonus = 0,
  combined_score = -1.61,
  base_confidence = 0.7284,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 331 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -1.61,
  alignment_bonus = 0,
  combined_score = -1.61,
  base_confidence = 0.7284,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 331;

-- Signal ID: 330 (GOOGL)
UPDATE signals SET
  base_combined_score = 13.01,
  alignment_bonus = 0,
  combined_score = 13.01,
  base_confidence = 0.7643,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 330 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 13.01,
  alignment_bonus = 0,
  combined_score = 13.01,
  base_confidence = 0.7643,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 330;

-- Signal ID: 329 (MSFT)
UPDATE signals SET
  base_combined_score = 12.54,
  alignment_bonus = 0,
  combined_score = 12.54,
  base_confidence = 0.7241,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 329 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 12.54,
  alignment_bonus = 0,
  combined_score = 12.54,
  base_confidence = 0.7241,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 329;

-- Signal ID: 328 (AAPL)
UPDATE signals SET
  base_combined_score = 23.42,
  alignment_bonus = 0,
  combined_score = 23.42,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 328 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 23.42,
  alignment_bonus = 0,
  combined_score = 23.42,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 328;

-- Signal ID: 327 (MOL.BD)
UPDATE signals SET
  base_combined_score = -5.62,
  alignment_bonus = 0,
  combined_score = -5.62,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 327 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -5.62,
  alignment_bonus = 0,
  combined_score = -5.62,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 327;

-- Signal ID: 326 (OTP.BD)
UPDATE signals SET
  base_combined_score = 31.45,
  alignment_bonus = 0,
  combined_score = 31.45,
  base_confidence = 0.6698,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 326 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.45,
  alignment_bonus = 0,
  combined_score = 31.45,
  base_confidence = 0.6698,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 326;

-- Signal ID: 325 (TSLA)
UPDATE signals SET
  base_combined_score = 0.87,
  alignment_bonus = 0,
  combined_score = 0.87,
  base_confidence = 0.7275,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 325 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.87,
  alignment_bonus = 0,
  combined_score = 0.87,
  base_confidence = 0.7275,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 325;

-- Signal ID: 324 (GOOGL)
UPDATE signals SET
  base_combined_score = 20.93,
  alignment_bonus = 0,
  combined_score = 20.93,
  base_confidence = 0.7604,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 324 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.93,
  alignment_bonus = 0,
  combined_score = 20.93,
  base_confidence = 0.7604,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 324;

-- Signal ID: 323 (MSFT)
UPDATE signals SET
  base_combined_score = 15.47,
  alignment_bonus = 0,
  combined_score = 15.47,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 323 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.47,
  alignment_bonus = 0,
  combined_score = 15.47,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 323;

-- Signal ID: 322 (AAPL)
UPDATE signals SET
  base_combined_score = 8.01,
  alignment_bonus = 0,
  combined_score = 8.01,
  base_confidence = 0.7248,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 322 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.01,
  alignment_bonus = 0,
  combined_score = 8.01,
  base_confidence = 0.7248,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 322;

-- Signal ID: 321 (MOL.BD)
UPDATE signals SET
  base_combined_score = -5.62,
  alignment_bonus = 0,
  combined_score = -5.62,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 321 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = -5.62,
  alignment_bonus = 0,
  combined_score = -5.62,
  base_confidence = 0.695,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 321;

-- Signal ID: 320 (OTP.BD)
UPDATE signals SET
  base_combined_score = 31.45,
  alignment_bonus = 0,
  combined_score = 31.45,
  base_confidence = 0.6698,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 320 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 31.45,
  alignment_bonus = 0,
  combined_score = 31.45,
  base_confidence = 0.6698,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 320;

-- Signal ID: 319 (TSLA)
UPDATE signals SET
  base_combined_score = 0.87,
  alignment_bonus = 0,
  combined_score = 0.87,
  base_confidence = 0.7275,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 319 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 0.87,
  alignment_bonus = 0,
  combined_score = 0.87,
  base_confidence = 0.7275,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 319;

-- Signal ID: 318 (GOOGL)
UPDATE signals SET
  base_combined_score = 20.93,
  alignment_bonus = 0,
  combined_score = 20.93,
  base_confidence = 0.7604,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 318 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 20.93,
  alignment_bonus = 0,
  combined_score = 20.93,
  base_confidence = 0.7604,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 318;

-- Signal ID: 317 (MSFT)
UPDATE signals SET
  base_combined_score = 15.47,
  alignment_bonus = 0,
  combined_score = 15.47,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 317 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 15.47,
  alignment_bonus = 0,
  combined_score = 15.47,
  base_confidence = 0.7601,
  confidence_boost = 0.0,
  strength = 'WEAK'
WHERE signal_id = 317;

-- Signal ID: 316 (AAPL)
UPDATE signals SET
  base_combined_score = 8.01,
  alignment_bonus = 0,
  combined_score = 8.01,
  base_confidence = 0.7248,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE id = (SELECT signal_id FROM signal_calculations WHERE signal_id = 316 LIMIT 1);

UPDATE signal_calculations SET
  base_combined_score = 8.01,
  alignment_bonus = 0,
  combined_score = 8.01,
  base_confidence = 0.7248,
  confidence_boost = 0.0,
  strength = 'NEUTRAL'
WHERE signal_id = 316;

-- Commit transaction
COMMIT;

-- Verification queries
SELECT strength, COUNT(*) as count FROM signals GROUP BY strength;
SELECT alignment_bonus, COUNT(*) FROM signal_calculations GROUP BY alignment_bonus ORDER BY alignment_bonus DESC;
