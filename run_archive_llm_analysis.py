"""
TrendSignal – Archive News LLM Analysis

LLM (OpenRouter/gpt-4o-mini) + opcionális FinBERT scoring az archive_news_items táblára.
Az eredmények az llm_* és active_score mezőkbe kerülnek.

Futtatás:
    python run_archive_llm_analysis.py                    # LLM only (gyors, ~20-40 perc)
    python run_archive_llm_analysis.py --finbert          # LLM + FinBERT (lassabb, pontosabb)
    python run_archive_llm_analysis.py --batch-size 50   # nagyobb köteg
    python run_archive_llm_analysis.py --dry-run          # csak számolja meg a sorokat

Resume: automatikus. A script ott folytatja ahol abbahagyta (WHERE active_score IS NULL).

Szükséges .env:
    OPENROUTER_API_KEY=sk-or-v1-...

active_score prioritás:
    1. llm_score  (ha LLM sikeresen válaszolt)
    2. finbert_score  (ha --finbert engedélyezve és FinBERT lefutott)
    3. av_sentiment_score  (AV fallback – mindig elérhető)
"""

import argparse
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
import os

load_dotenv()

# Windows encoding fix (cp1250 → utf-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.llm_context_checker import LLMContextChecker, LLMCheckResult

# ── Konfiguráció ─────────────────────────────────────────────────────────────

DB_PATH = "trendsignal.db"


# ── Adapter ──────────────────────────────────────────────────────────────────

@dataclass
class _ArchiveNewsItem:
    """
    Minimális adapter az archive_news_items sorhoz,
    hogy a LLMContextChecker._build_messages() működjön (title + description).
    """
    title: str
    description: str   # az archive_news_items 'summary' mezője


# ── DB segédfüggvények ────────────────────────────────────────────────────────

def get_ticker_names(db_path: str) -> dict:
    """Visszaadja a {symbol: name} mapot a tickers táblából."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT symbol, name FROM tickers")
    names = {r[0]: (r[1] or r[0]) for r in cur.fetchall()}
    conn.close()
    return names


def count_unprocessed(db_path: str) -> int:
    """Megszámolja az active_score IS NULL sorokat."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM archive_news_items WHERE active_score IS NULL")
    count = cur.fetchone()[0]
    conn.close()
    return count


def count_total(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM archive_news_items")
    count = cur.fetchone()[0]
    conn.close()
    return count


def fetch_unprocessed_batch(db_path: str, batch_size: int) -> list:
    """Lekéri a következő batch feldolgozandó sort."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, ticker_symbol, title, summary, av_sentiment_score
        FROM archive_news_items
        WHERE active_score IS NULL
        ORDER BY id
        LIMIT ?
    """, (batch_size,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def save_result(
    db_path: str,
    row_id: int,
    finbert_score: Optional[float],
    llm_result: LLMCheckResult,
    av_score: Optional[float],
) -> None:
    """
    Menti az elemzési eredményt a DB-be.

    Mindig beállítja active_score-t és active_score_source-t,
    hogy a sor "feldolgozottnak" minősüljön (resume logika).

    Prioritás:
        1. llm_score  (ha LLM sikerrel válaszolt)
        2. finbert_score  (ha FinBERT futott)
        3. av_sentiment_score  (Alpha Vantage fallback)
        4. 0.0 / "none"  (ha semmi sem elérhető)
    """
    if llm_result.success:
        active_score  = llm_result.llm_score
        active_source = "llm"
    elif finbert_score is not None:
        active_score  = finbert_score
        active_source = "finbert"
    elif av_score is not None:
        active_score  = float(av_score)
        active_source = "av"
    else:
        active_score  = 0.0
        active_source = "none"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE archive_news_items SET
            finbert_score       = ?,
            llm_score           = ?,
            llm_price_impact    = ?,
            llm_impact_level    = ?,
            llm_impact_duration = ?,
            llm_catalyst_type   = ?,
            llm_priced_in       = ?,
            llm_confidence      = ?,
            llm_reason          = ?,
            llm_latency_ms      = ?,
            is_relevant         = ?,
            active_score        = ?,
            active_score_source = ?
        WHERE id = ?
        """,
        (
            finbert_score,
            llm_result.llm_score       if llm_result.success else None,
            llm_result.price_impact    if llm_result.success else None,
            llm_result.impact_level    if llm_result.success else None,
            llm_result.impact_duration if llm_result.success else None,
            llm_result.catalyst_type   if llm_result.success else None,
            int(llm_result.priced_in)  if llm_result.success else None,
            llm_result.confidence      if llm_result.success else None,
            llm_result.reason          if llm_result.success else None,
            llm_result.latency_ms,
            int(llm_result.relevant)   if llm_result.success else None,
            active_score,
            active_source,
            row_id,
        ),
    )
    conn.commit()
    conn.close()


# ── Fő logika ─────────────────────────────────────────────────────────────────

def run_batch_llm(
    rows: list,
    checker: LLMContextChecker,
    ticker_names: dict,
    max_concurrent: int,
) -> list:
    """
    Párhuzamosan futtatja az LLM elemzést a batch-en.
    Minden sorhoz a saját ticker_symbol-ját használja.

    Returns:
        List[LLMCheckResult] azonos sorrendben mint rows.
    """
    results: list = [None] * len(rows)

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_idx = {
            executor.submit(
                checker.check_single,
                _ArchiveNewsItem(
                    title=rows[i].get("title") or "",
                    description=rows[i].get("summary") or "",
                ),
                rows[i]["ticker_symbol"],
                ticker_names.get(rows[i]["ticker_symbol"], rows[i]["ticker_symbol"]),
                None,   # current_price – nincs historikus adathoz
            ): i
            for i in range(len(rows))
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = LLMCheckResult(success=False)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TrendSignal – archive_news_items LLM elemzés"
    )
    parser.add_argument(
        "--batch-size", type=int, default=20,
        help="Sorok száma kötegenként (alapért.: 20)",
    )
    parser.add_argument(
        "--finbert", action="store_true",
        help="FinBERT elemzés is fusson (lassabb, de pontosabb finbert_score-t ad)",
    )
    parser.add_argument(
        "--model", default="openai/gpt-4o-mini",
        help="OpenRouter LLM model (alapért.: openai/gpt-4o-mini)",
    )
    parser.add_argument(
        "--max-concurrent", type=int, default=5,
        help="Párhuzamos LLM hívások száma (alapért.: 5)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.3,
        help="Késleltetés kötegek között (sec, alapért.: 0.3)",
    )
    parser.add_argument(
        "--max-rows", type=int, default=0,
        help="Maximum feldolgozandó sorok száma (0 = korlátlan, teszteléshez hasznos)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Csak számolja meg a feldolgozandó sorokat, ne fusson elemzés",
    )
    args = parser.parse_args()

    # Ellenőrzések
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("HIBA: Hiányzó OPENROUTER_API_KEY a .env fájlban!")
        print("  Regisztrálj: https://openrouter.ai/")
        sys.exit(1)

    total      = count_total(DB_PATH)
    unprocessed = count_unprocessed(DB_PATH)
    processed_already = total - unprocessed

    print("=" * 60)
    print("TrendSignal – Archive News LLM Analysis")
    print("=" * 60)
    print(f"  DB:               {DB_PATH}")
    print(f"  Model:            {args.model}")
    print(f"  FinBERT:          {'igen' if args.finbert else 'nem (AV score fallback)'}")
    print(f"  Batch méret:      {args.batch_size}")
    if args.max_rows:
        print(f"  Max sorok:        {args.max_rows} (teszt mód)")
    print(f"  Párhuzamosság:    {args.max_concurrent} LLM hívás egyszerre")
    print(f"  Összes sor:       {total}")
    print(f"  Már kész:         {processed_already}")
    print(f"  Feldolgozandó:    {unprocessed}")
    print("=" * 60)

    if args.dry_run:
        print("[DRY-RUN] Kész. Futtasd --dry-run nélkül az elemzés indításához.")
        return

    if unprocessed == 0:
        print("[OK] Minden sor fel van dolgozva. Nincs teendő.")
        return

    # ── FinBERT (opcionális) ─────────────────────────────────────────────────
    finbert = None
    if args.finbert:
        print("\nFinBERT model betöltése (ProsusAI/finbert)...")
        try:
            from src.finbert_analyzer import FinBERTAnalyzer
            finbert = FinBERTAnalyzer()
            print("[OK] FinBERT kész\n")
        except Exception as e:
            print(f"[WARN] FinBERT betöltés sikertelen: {e}")
            print("  Folytatás FinBERT nélkül (AV score lesz a fallback)\n")
            finbert = None

    # ── LLM Checker ─────────────────────────────────────────────────────────
    checker = LLMContextChecker(
        api_key=api_key,
        model=args.model,
        timeout=15.0,
        max_concurrent=args.max_concurrent,
    )

    ticker_names = get_ticker_names(DB_PATH)
    print(f"Tickerek a DB-ből: {sorted(ticker_names.keys())}\n")

    # ── Fő feldolgozó ciklus ─────────────────────────────────────────────────
    grand_processed = 0
    grand_llm_ok    = 0
    grand_llm_fail  = 0
    grand_fb_ok     = 0
    grand_av_fb     = 0

    batch_num = 0
    start_time = time.time()

    while True:
        # Max sorok limit (teszteléshez)
        if args.max_rows and grand_processed >= args.max_rows:
            print(f"\n[LIMIT] --max-rows {args.max_rows} elérve, megállunk.")
            break

        current_batch = args.batch_size
        if args.max_rows:
            current_batch = min(args.batch_size, args.max_rows - grand_processed)

        rows = fetch_unprocessed_batch(DB_PATH, current_batch)
        if not rows:
            break

        batch_num += 1
        n = len(rows)
        elapsed = time.time() - start_time
        speed = grand_processed / elapsed if elapsed > 0 else 0
        remaining = (unprocessed - grand_processed) / speed if speed > 0 else float("inf")
        eta_str = f"{remaining/60:.1f} perc" if speed > 0 and grand_processed > 0 else "?"

        print(
            f"[#{batch_num:4d}] {n} sor | "
            f"feldolgozva: {grand_processed}/{unprocessed} | "
            f"sebesség: {speed:.1f} sor/s | ETA: {eta_str}"
        )

        # ── FinBERT ──────────────────────────────────────────────────────────
        finbert_scores = [None] * n
        if finbert is not None:
            try:
                texts = [
                    f"{r.get('title', '')} {r.get('summary', '') or ''}".strip()
                    for r in rows
                ]
                fb_results = finbert.analyze_batch(texts)
                finbert_scores = [fb["score"] for fb in fb_results]
                grand_fb_ok += n
            except Exception as e:
                print(f"  [WARN] FinBERT batch hiba: {e}")
                finbert_scores = [None] * n

        # ── LLM (párhuzamos) ─────────────────────────────────────────────────
        llm_results = run_batch_llm(rows, checker, ticker_names, args.max_concurrent)

        # ── DB mentés ────────────────────────────────────────────────────────
        batch_llm_ok   = 0
        batch_llm_fail = 0
        batch_av_fb    = 0

        for i, row in enumerate(rows):
            lr   = llm_results[i]
            fbs  = finbert_scores[i]
            avs  = row.get("av_sentiment_score")

            if lr.success:
                batch_llm_ok += 1
            else:
                batch_llm_fail += 1
                if fbs is None and avs is not None:
                    batch_av_fb += 1

            save_result(DB_PATH, row["id"], fbs, lr, avs)

        grand_processed += n
        grand_llm_ok    += batch_llm_ok
        grand_llm_fail  += batch_llm_fail
        grand_av_fb     += batch_av_fb

        print(
            f"         LLM: {batch_llm_ok} ok / {batch_llm_fail} fail"
            + (f" | AV fallback: {batch_av_fb}" if batch_av_fb else "")
            + (f" | FinBERT: {n}" if finbert else "")
        )

        if args.delay > 0:
            time.sleep(args.delay)

    # ── Összesítő ────────────────────────────────────────────────────────────
    total_elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("KÉSZ!")
    print(f"  Feldolgozott sorok:  {grand_processed}")
    print(f"  LLM sikeres:         {grand_llm_ok}")
    print(f"  LLM sikertelen:      {grand_llm_fail}")
    if finbert:
        print(f"  FinBERT elemzett:    {grand_fb_ok}")
    print(f"  AV score fallback:   {grand_av_fb}")
    print(f"  Eltelt idő:          {total_elapsed/60:.1f} perc")
    if grand_processed > 0:
        print(f"  Átlag sebesség:      {grand_processed/total_elapsed:.1f} sor/s")
    print("=" * 60)
    print("Következő lépés: retroaktív signal generálás a kész adatokon.")


if __name__ == "__main__":
    main()
