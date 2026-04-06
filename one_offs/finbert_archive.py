"""
TrendSignal - FinBERT scoring az archive_news_items tablan
==========================================================

Kitolti az archive_news_items.finbert_score mezot az osszes cikkre,
a ProsusAI/finbert modell segitsegevel (helyi CPU futas, ~22 perc).

Resume: kihagyja azokat a sorokat ahol finbert_score IS NOT NULL.

Futtatas:
    python one_offs/finbert_archive.py
    python one_offs/finbert_archive.py --batch-size 32   # lassabb gepen
    python one_offs/finbert_archive.py --limit 500        # teszteles
    python one_offs/finbert_archive.py --dry-run          # csak szamolj
"""

import os
import sys
import sqlite3
import time
import argparse

import warnings
warnings.filterwarnings('ignore')

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH     = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trendsignal.db")
MODEL_NAME  = "ProsusAI/finbert"
BATCH_SIZE  = 64
COMMIT_EVERY = 500
PROGRESS_EVERY = 1000


def load_model():
    print(f"FinBERT modell betoltese ({MODEL_NAME})...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.eval()
    print(f"  Betoltve: {time.time()-t0:.1f}s | device: CPU")
    return tokenizer, model


def score_batch(tokenizer, model, texts: list) -> list:
    """Visszaad egy lista float score-t (-1..+1) a texts-nek megfeleloen."""
    inputs = tokenizer(
        texts,
        return_tensors='pt',
        truncation=True,
        max_length=512,
        padding=True,
    )
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.nn.functional.softmax(logits, dim=1)

    scores = []
    for i in range(len(texts)):
        pos = probs[i][0].item()
        neg = probs[i][1].item()
        neu = probs[i][2].item()
        # Azonos keplet mint a live pipeline-ban
        score = (pos - neg) / (pos + neu + neg)
        scores.append(round(score, 6))
    return scores


def main():
    parser = argparse.ArgumentParser(description="FinBERT scoring archive_news_items")
    parser.add_argument("--batch-size",  type=int, default=BATCH_SIZE)
    parser.add_argument("--limit",       type=int, default=None, help="Max cikkek szama (teszteles)")
    parser.add_argument("--dry-run",     action="store_true", help="Csak szamolj, ne irj DB-be")
    args = parser.parse_args()

    print("=" * 60)
    print("  TrendSignal - FinBERT Archive Scoring")
    print("=" * 60)
    print(f"  DB:         {DB_PATH}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Limit:      {args.limit or 'nincs'}")
    print(f"  Dry-run:    {args.dry_run}")
    print()

    # --- DB ---
    conn = sqlite3.connect(DB_PATH, timeout=30)

    # Feldolgozando sorok betoltese
    sql = """
        SELECT id, title, summary
        FROM archive_news_items
        WHERE finbert_score IS NULL
        ORDER BY id DESC
    """
    if args.limit:
        sql += f" LIMIT {args.limit}"

    rows = conn.execute(sql).fetchall()
    total = len(rows)

    if total == 0:
        print("  Nincs feldolgozando sor — minden archiv cikknek van mar finbert_score.")
        conn.close()
        return

    print(f"  Feldolgozando cikkek: {total:,}")

    # Becsult ido (17 ms/cikk batch=64 alapjan)
    est_min = total * 17 / 1000 / 60 * (64 / args.batch_size)
    print(f"  Becsult ido: ~{est_min:.0f} perc (CPU, batch={args.batch_size})")
    print()

    if args.dry_run:
        print("  [DRY-RUN] Kilepes.")
        conn.close()
        return

    # --- Modell ---
    tokenizer, model = load_model()
    print()

    # --- Feldolgozas ---
    processed = 0
    errors    = 0
    t_start   = time.time()

    for batch_start in range(0, total, args.batch_size):
        batch = rows[batch_start : batch_start + args.batch_size]

        ids   = [r[0] for r in batch]
        texts = []
        for _, title, summary in batch:
            # Cim + osszefoglalo kombinacio, mint a live pipeline-ban
            parts = []
            if title:   parts.append(title.strip())
            if summary: parts.append(summary.strip())
            texts.append(" ".join(parts) if parts else "no text")

        try:
            scores = score_batch(tokenizer, model, texts)
        except Exception as e:
            print(f"  [HIBA] batch {batch_start}: {e}")
            errors += len(batch)
            processed += len(batch)
            continue

        # DB iras
        conn.executemany(
            "UPDATE archive_news_items SET finbert_score = ? WHERE id = ?",
            [(score, row_id) for score, row_id in zip(scores, ids)]
        )

        processed += len(batch)

        # Commit
        if processed % COMMIT_EVERY < args.batch_size:
            conn.commit()

        # Progress
        if processed % PROGRESS_EVERY < args.batch_size or processed >= total:
            elapsed = time.time() - t_start
            rate    = processed / elapsed if elapsed > 0 else 0
            eta_min = (total - processed) / rate / 60 if rate > 0 else 0
            print(
                f"  {processed:6,}/{total:,} "
                f"| {rate:.0f} cikk/s "
                f"| ETA {eta_min:.1f} perc"
                f"{' | hibak: ' + str(errors) if errors else ''}"
            )

    # Vegso commit
    conn.commit()

    elapsed = time.time() - t_start
    print()
    print(f"  KESZ — {elapsed:.0f}s ({elapsed/60:.1f} perc)")
    print(f"  Feldolgozva:  {processed:,}")
    print(f"  Hibas:        {errors:,}")
    print(f"  Atlag sebesseg: {processed/elapsed:.0f} cikk/s")

    # Ellenorzes
    r = conn.execute("SELECT COUNT(*) FROM archive_news_items WHERE finbert_score IS NULL").fetchone()[0]
    print(f"  Maradek NULL finbert_score: {r:,}")

    conn.close()


if __name__ == "__main__":
    main()
