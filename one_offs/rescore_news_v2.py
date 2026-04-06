"""
TrendSignal - Visszamenőleges LLM újraértékelés (v2 prompt)
============================================================

Újraértékeli az archive_news_items és news_items táblák összes LLM-mel
már feldolgozott cikkét az új, meglepetés-alapú v2 prompt szerint.

Változások v1 → v2:
  - Cikktípus szűrés: filing/opinion/tangential → llm_score = 0.0
  - Meglepetés-detekció: beat/miss/in_line/no_baseline
  - is_first_report bónusz
  - directly_about ellenőrzés

DB-ben tárolt új mezők:
  - llm_score_worthy    BOOLEAN   (score_worthy)
  - llm_is_first_report BOOLEAN   (is_first_report)
  - llm_surprise_dir    VARCHAR   (surprise_direction, raw)
  Felülírt meglévő mezők:
  - llm_price_impact    → price_impact property (beat→up, miss→down, stb.)
  - llm_catalyst_type   → article_type → régi catalyst értékre mappolva
  - llm_impact_level    → surprise_magnitude
  - llm_priced_in       → NOT score_worthy
  - llm_score           → új score
  - active_score        → új score (ha LLM sikeres)
  - active_score_source → 'llm_v2'

Resume: a script kihagyja azokat a sorokat ahol active_score_source='llm_v2'.

Futtatás:
    python one_offs/rescore_news_v2.py
    python one_offs/rescore_news_v2.py --dry-run        # csak számolja, nem hív API-t
    python one_offs/rescore_news_v2.py --limit 500      # csak 500 cikk (tesztelés)
    python one_offs/rescore_news_v2.py --table news     # csak news_items
    python one_offs/rescore_news_v2.py --table archive  # csak archive_news_items
    python one_offs/rescore_news_v2.py --concurrency 30 # párhuzamosság

Szükséges env var:
    OPENROUTER_API_KEY=...
"""

import os
import sys
import sqlite3
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.llm_context_checker import LLMContextChecker, LLMCheckResult

# ---------------------------------------------------------------------------
# Konfig
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trendsignal.db")

DEFAULT_CONCURRENCY = 20
BATCH_SIZE = 200      # DB fetch/commit batch
PROGRESS_EVERY = 100  # konzol progress print

# Ticker → cégnév lookup (az LLM prompt-ba kerül)
TICKER_NAMES = {
    "AAPL":   "Apple Inc.",
    "AMZN":   "Amazon.com Inc.",
    "GOOGL":  "Alphabet Inc.",
    "IBM":    "IBM Corp.",
    "META":   "Meta Platforms Inc.",
    "MSFT":   "Microsoft Corp.",
    "NVDA":   "Nvidia Corp.",
    "TSLA":   "Tesla Inc.",
    "MOL.BD": "MOL Magyar Olaj- és Gázipari Nyrt.",
    "OTP.BD": "OTP Bank Nyrt.",
}


# ---------------------------------------------------------------------------
# Adapter: archive_news_items sor → news_item-szerű objekt
# ---------------------------------------------------------------------------

@dataclass
class NewsAdapter:
    """
    Egyszerű wrapper, hogy a LLMContextChecker._build_messages()
    archive_news_items sorokat is el tudjon fogadni.
    """
    title: str
    description: str   # summary mezőre mappolva
    summary: str       # duplikált, hogy mindkét property működjön


# ---------------------------------------------------------------------------
# DB migrációk
# ---------------------------------------------------------------------------

def ensure_columns(conn: sqlite3.Connection):
    """
    Hozzáadja az új v2 mezőket, ha még nem léteznek.
    CREATE TABLE-t nem módosít, csak ALTER TABLE ADD COLUMN-t futtat.
    """
    new_cols = [
        ("archive_news_items", "llm_score_worthy",    "BOOLEAN"),
        ("archive_news_items", "llm_is_first_report", "BOOLEAN"),
        ("archive_news_items", "llm_surprise_dir",    "VARCHAR(20)"),
        ("news_items",         "llm_score_worthy",    "BOOLEAN"),
        ("news_items",         "llm_is_first_report", "BOOLEAN"),
        ("news_items",         "llm_surprise_dir",    "VARCHAR(20)"),
    ]
    existing_cols = {}
    for tbl in ("archive_news_items", "news_items"):
        try:
            rows = conn.execute(f"PRAGMA table_info({tbl})").fetchall()
            existing_cols[tbl] = {r[1] for r in rows}
        except Exception:
            existing_cols[tbl] = set()

    for tbl, col, col_type in new_cols:
        if col not in existing_cols.get(tbl, set()):
            try:
                conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}")
                print(f"  [DB] {tbl}.{col} hozzáadva")
            except Exception as e:
                print(f"  [DB] {tbl}.{col} ALTER hiba: {e}")
    conn.commit()


# ---------------------------------------------------------------------------
# Cikkek betöltése
# ---------------------------------------------------------------------------

def load_pending_archive(conn: sqlite3.Connection, limit: Optional[int]) -> list:
    """archive_news_items sorok amelyek még nem v2-vel lettek értékelve."""
    sql = """
        SELECT id, ticker_symbol, title, summary, av_relevance_score
        FROM archive_news_items
        WHERE active_score_source != 'llm_v2'
          AND (active_score_source = 'llm' OR active_score IS NOT NULL)
        ORDER BY id DESC
    """
    if limit:
        sql += f" LIMIT {limit}"
    return conn.execute(sql).fetchall()


def load_pending_live(conn: sqlite3.Connection, limit: Optional[int]) -> list:
    """news_items sorok amelyek még nem v2-vel lettek értékelve."""
    sql = """
        SELECT n.id, t.symbol AS ticker_symbol, n.title, n.description AS summary,
               nt.relevance_score AS av_relevance_score
        FROM news_items n
        JOIN news_tickers nt ON nt.news_id = n.id
        JOIN tickers t ON t.id = nt.ticker_id
        WHERE n.active_score_source != 'llm_v2'
          AND (n.active_score_source = 'llm' OR n.active_score IS NOT NULL)
        ORDER BY n.id DESC
    """
    if limit:
        sql += f" LIMIT {limit}"
    return conn.execute(sql).fetchall()


# ---------------------------------------------------------------------------
# DB írás
# ---------------------------------------------------------------------------

def save_result(conn: sqlite3.Connection, table: str, row_id: int,
                result: LLMCheckResult, dry_run: bool):
    """Egy LLM eredmény mentése a DB-be."""
    if dry_run:
        return

    if table == "archive_news_items":
        conn.execute("""
            UPDATE archive_news_items SET
                llm_score            = ?,
                llm_price_impact     = ?,
                llm_impact_level     = ?,
                llm_impact_duration  = ?,
                llm_catalyst_type    = ?,
                llm_priced_in        = ?,
                llm_confidence       = ?,
                llm_reason           = ?,
                llm_latency_ms       = ?,
                llm_score_worthy     = ?,
                llm_is_first_report  = ?,
                llm_surprise_dir     = ?,
                active_score         = ?,
                active_score_source  = 'llm_v2'
            WHERE id = ?
        """, (
            result.llm_score,
            result.price_impact,
            result.impact_level,
            result.impact_duration,
            result.catalyst_type,
            1 if result.priced_in else 0,
            result.confidence,
            result.reason,
            result.latency_ms,
            1 if result.score_worthy else 0,
            1 if result.is_first_report else 0,
            result.surprise_direction,
            result.llm_score,    # active_score = llm_score
            row_id,
        ))
    else:  # news_items
        conn.execute("""
            UPDATE news_items SET
                llm_score            = ?,
                llm_price_impact     = ?,
                llm_impact_level     = ?,
                llm_impact_duration  = ?,
                llm_catalyst_type    = ?,
                llm_priced_in        = ?,
                llm_confidence       = ?,
                llm_reason           = ?,
                llm_latency_ms       = ?,
                llm_score_worthy     = ?,
                llm_is_first_report  = ?,
                llm_surprise_dir     = ?,
                active_score         = ?,
                active_score_source  = 'llm_v2'
            WHERE id = ?
        """, (
            result.llm_score,
            result.price_impact,
            result.impact_level,
            result.impact_duration,
            result.catalyst_type,
            1 if result.priced_in else 0,
            result.confidence,
            result.reason,
            result.latency_ms,
            1 if result.score_worthy else 0,
            1 if result.is_first_report else 0,
            result.surprise_direction,
            result.llm_score,
            row_id,
        ))


# ---------------------------------------------------------------------------
# Feldolgozás
# ---------------------------------------------------------------------------

def process_table(
    checker: LLMContextChecker,
    conn: sqlite3.Connection,
    table: str,
    rows: list,
    concurrency: int,
    dry_run: bool,
):
    """
    Egy tábla sorait dolgozza fel párhuzamosan.
    rows: list of sqlite3.Row (id, ticker_symbol, title, summary, av_relevance_score)
    """
    total = len(rows)
    if total == 0:
        print(f"  [{table}] Nincs feldolgozandó sor.")
        return

    print(f"\n  [{table}] {total:,} cikk feldolgozása (concurrency={concurrency})...")

    stats = {
        "ok": 0, "failed": 0, "score_worthy": 0,
        "zero_score": 0, "api_calls": 0,
    }
    t_start = time.time()

    def _process_one(row):
        row_id  = row[0]
        ticker  = row[1] or "UNKNOWN"
        title   = row[2] or ""
        summary = row[3] or ""
        ticker_name = TICKER_NAMES.get(ticker, ticker)

        news_obj = NewsAdapter(
            title=title,
            description=summary,
            summary=summary,
        )
        result = checker.check_single(news_obj, ticker, ticker_name)
        return row_id, result

    # Párhuzamos feldolgozás
    processed = 0
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(_process_one, row): row for row in rows}

        for future in as_completed(futures):
            try:
                row_id, result = future.result()
                stats["api_calls"] += 1

                if result.success:
                    stats["ok"] += 1
                    if result.score_worthy:
                        stats["score_worthy"] += 1
                    if result.llm_score == 0.0:
                        stats["zero_score"] += 1
                    save_result(conn, table, row_id, result, dry_run)
                else:
                    stats["failed"] += 1

            except Exception as e:
                stats["failed"] += 1
                print(f"  [HIBA] future exception: {e}")

            processed += 1

            # Progress print
            if processed % PROGRESS_EVERY == 0 or processed == total:
                elapsed = time.time() - t_start
                rate = processed / elapsed if elapsed > 0 else 0
                eta_s = (total - processed) / rate if rate > 0 else 0
                eta_m = eta_s / 60
                pct_worthy = stats["score_worthy"] / max(stats["ok"], 1) * 100
                print(
                    f"  {processed:6,}/{total:,} "
                    f"| ok={stats['ok']} fail={stats['failed']} "
                    f"| score_worthy={stats['score_worthy']} ({pct_worthy:.0f}%) "
                    f"| {rate:.1f} cikk/s "
                    f"| ETA {eta_m:.1f} perc"
                )

            # Batch commit minden BATCH_SIZE cikkenként
            if processed % BATCH_SIZE == 0 and not dry_run:
                conn.commit()

    # Végső commit
    if not dry_run:
        conn.commit()

    elapsed = time.time() - t_start
    pct_worthy = stats["score_worthy"] / max(stats["ok"], 1) * 100
    pct_zero   = stats["zero_score"]   / max(stats["ok"], 1) * 100

    print(f"\n  [{table}] KÉSZ — {elapsed:.0f}s")
    print(f"    Sikeres API hívás:  {stats['ok']:,} / {total:,}")
    print(f"    Hibás/kihagyott:    {stats['failed']:,}")
    print(f"    score_worthy=True:  {stats['score_worthy']:,} ({pct_worthy:.1f}%)")
    print(f"    llm_score=0:        {stats['zero_score']:,} ({pct_zero:.1f}%)")
    print(f"    Átlag sebesség:     {total/elapsed:.1f} cikk/s")

    # Becsült API költség (GPT-4o-mini: ~$0.15/1M input + $0.60/1M output token)
    # ~300 input token/cikk (prompt ~250 + title/summary ~50), ~50 output token
    input_tokens  = stats["api_calls"] * 300
    output_tokens = stats["api_calls"] * 50
    cost_usd = input_tokens / 1_000_000 * 0.15 + output_tokens / 1_000_000 * 0.60
    print(f"    Becsült API költség: ${cost_usd:.2f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TrendSignal LLM v2 rescore")
    parser.add_argument("--dry-run",    action="store_true", help="Csak számolja, nem ír DB-be és nem hív API-t")
    parser.add_argument("--limit",      type=int, default=None, help="Max sorok száma táblánként")
    parser.add_argument("--table",      choices=["archive", "news", "both"], default="both")
    parser.add_argument("--concurrency",type=int, default=DEFAULT_CONCURRENCY)
    args = parser.parse_args()

    print("=" * 65)
    print("  TrendSignal - LLM v2 Rescore")
    print("=" * 65)
    print(f"  DB:          {DB_PATH}")
    print(f"  Dry-run:     {args.dry_run}")
    print(f"  Limit:       {args.limit or 'nincs'}")
    print(f"  Table:       {args.table}")
    print(f"  Concurrency: {args.concurrency}")
    print()

    # API kulcs
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key and not args.dry_run:
        print("HIBA: OPENROUTER_API_KEY environment variable nincs beállítva!")
        print("  Adj meg .env fájlban: OPENROUTER_API_KEY=sk-or-...")
        sys.exit(1)

    if args.dry_run:
        print("  [DRY-RUN] Csak számlálás, nincs API hívás és DB írás.\n")

    # DB kapcsolat
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row

    # Migrációk
    print("[1/4] DB migráció (új oszlopok)...")
    ensure_columns(conn)

    # Cikkek betöltése
    print("\n[2/4] Feldolgozandó cikkek betöltése...")
    archive_rows = []
    live_rows    = []

    if args.table in ("archive", "both"):
        archive_rows = load_pending_archive(conn, args.limit)
        print(f"  archive_news_items: {len(archive_rows):,} sor")

    if args.table in ("news", "both"):
        live_rows = load_pending_live(conn, args.limit)
        print(f"  news_items:         {len(live_rows):,} sor")

    total = len(archive_rows) + len(live_rows)
    print(f"  Összesen:           {total:,} cikk")

    if total == 0:
        print("\n  Nincs feldolgozandó sor — minden már v2-vel értékelt.")
        conn.close()
        return

    if args.dry_run:
        # Becsült futási idő és költség dry-run-ban
        avg_speed = args.concurrency * 2.0  # becsült cikk/s
        eta_min   = total / avg_speed / 60
        input_tokens  = total * 300
        output_tokens = total * 50
        cost_usd = input_tokens / 1_000_000 * 0.15 + output_tokens / 1_000_000 * 0.60
        print(f"\n  [DRY-RUN] Becsült futási idő: ~{eta_min:.0f} perc")
        print(f"  [DRY-RUN] Becsült API költség: ~${cost_usd:.2f}")
        conn.close()
        return

    # Checker inicializálás
    print("\n[3/4] LLM checker inicializálás...")
    checker = LLMContextChecker(
        api_key=api_key,
        model='google/gemini-2.0-flash-001',
        timeout=10.0,
        max_concurrent=args.concurrency,
    )

    # Feldolgozás
    print("\n[4/4] Feldolgozás...")
    t_total_start = time.time()

    if archive_rows:
        process_table(checker, conn, "archive_news_items", archive_rows,
                      args.concurrency, dry_run=False)

    if live_rows:
        process_table(checker, conn, "news_items", live_rows,
                      args.concurrency, dry_run=False)

    total_elapsed = time.time() - t_total_start

    # Végső összefoglaló
    print(f"\n{'='*65}")
    print(f"  KÉSZ — összesen {total_elapsed/60:.1f} perc")
    print()

    # DB statisztika az eredményről
    for tbl in (["archive_news_items"] if args.table == "archive"
                else ["news_items"] if args.table == "news"
                else ["archive_news_items", "news_items"]):
        try:
            v2_count = conn.execute(
                f"SELECT COUNT(*) FROM {tbl} WHERE active_score_source='llm_v2'"
            ).fetchone()[0]
            worthy   = conn.execute(
                f"SELECT COUNT(*) FROM {tbl} WHERE active_score_source='llm_v2' AND llm_score_worthy=1"
            ).fetchone()[0]
            nonzero  = conn.execute(
                f"SELECT COUNT(*) FROM {tbl} WHERE active_score_source='llm_v2' AND llm_score != 0"
            ).fetchone()[0]
            avg_score = conn.execute(
                f"SELECT AVG(ABS(llm_score)) FROM {tbl} WHERE active_score_source='llm_v2' AND llm_score != 0"
            ).fetchone()[0]
            print(f"  {tbl}:")
            print(f"    v2-vel értékelt:    {v2_count:,}")
            print(f"    score_worthy=True:  {worthy:,} ({worthy/max(v2_count,1)*100:.1f}%)")
            print(f"    llm_score != 0:     {nonzero:,} ({nonzero/max(v2_count,1)*100:.1f}%)")
            if avg_score:
                print(f"    Átlag |llm_score|:  {avg_score:.4f}")
        except Exception as e:
            print(f"  {tbl} statisztika hiba: {e}")

    conn.close()
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
