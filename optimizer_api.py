"""
TrendSignal Self-Tuning Engine - FastAPI Router

Endpoints:
  POST /api/v1/optimizer/run         — start optimization (subprocess)
  GET  /api/v1/optimizer/runs        — list recent runs
  GET  /api/v1/optimizer/runs/{id}/progress  — live progress (polling)
  POST /api/v1/optimizer/runs/{id}/stop      — stop running optimizer
  GET  /api/v1/optimizer/proposals           — list proposals
  POST /api/v1/optimizer/proposals/{id}/approve  — approve proposal
  POST /api/v1/optimizer/proposals/{id}/reject   — reject proposal
  GET  /api/v1/optimizer/status      — scheduler + market state

Place this file in the project root and register in api.py:
    from optimizer_api import router as optimizer_router
    app.include_router(optimizer_router)

Version: 1.0
Date: 2026-02-23
"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

BASE_DIR   = Path(__file__).resolve().parent
DB_PATH    = BASE_DIR / "trendsignal.db"
STOP_FLAG  = BASE_DIR / ".optimizer_stop"

# In-memory subprocess handle — hogy le tudjuk állítani azonnal
_active_proc: Optional[subprocess.Popen] = None

router = APIRouter(prefix="/api/v1/optimizer", tags=["Optimizer"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    population_size: int = 80
    max_generations: int = 100
    crossover_prob:  float = 0.70
    mutation_prob:   float = 0.20
    trade_mode:      str   = "all"     # "all" | "long" | "short"
    include_archive: bool  = False     # archive_signals CLOSED trade-ek bevonása
    phase:           str   = "all"     # "all" | "score_only" | "thresholds_only"
    max_cycles:      int   = 10        # max ismétlési ciklus (1-10)


class RunResponse(BaseModel):
    run_id: int
    status: str
    message: str


class ProgressResponse(BaseModel):
    run_id:              int
    status:              str
    generations_run:     int
    max_generations:     int
    best_train_fitness:  Optional[float]
    best_val_fitness:    Optional[float]
    train_val_gap_pct:   Optional[float]
    recent_generations:  List[dict]
    proposals_ready:     int
    elapsed_seconds:     Optional[float]
    current_cycle:       int = 1
    max_cycles:          int = 1


# ---------------------------------------------------------------------------
# Helper: DB connection
# ---------------------------------------------------------------------------

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _running_run_id() -> Optional[int]:
    """Return the run_id of any currently RUNNING optimization, or None."""
    conn = _db()
    row = conn.execute(
        "SELECT id FROM optimization_runs WHERE status='RUNNING' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row["id"] if row else None


# ---------------------------------------------------------------------------
# POST /run — start optimization
# ---------------------------------------------------------------------------

@router.post("/run", response_model=RunResponse)
async def start_optimizer(req: RunRequest):
    """
    Start a genetic optimization run as an isolated subprocess.
    Only one run can be active at a time.
    Stale RUNNING records (no progress for >30 min) are auto-cleared.
    """
    # Check if already running — auto-clear stale records
    existing = _running_run_id()
    if existing:
        conn = _db()
        stale_row = conn.execute("""
            SELECT id, generations_run, started_at FROM optimization_runs
            WHERE id = ? AND status = 'RUNNING'
        """, (existing,)).fetchone()
        conn.close()

        is_stale = False
        if stale_row:
            gens = stale_row["generations_run"] or 0
            started_at_str = stale_row["started_at"]
            try:
                from datetime import datetime, timezone
                started = datetime.fromisoformat(started_at_str)
                age_minutes = (datetime.now() - started).total_seconds() / 60
                # Stale: 0 generations after 30 min, or any run older than 8 hours
                if (gens == 0 and age_minutes > 30) or age_minutes > 480:
                    is_stale = True
            except Exception:
                is_stale = (gens == 0)  # no progress at all → stale

        if is_stale:
            conn = _db()
            conn.execute("""
                UPDATE optimization_runs
                SET status = 'FAILED', completed_at = CURRENT_TIMESTAMP,
                    error_message = 'Process crashed — auto-cleared by new run'
                WHERE id = ?
            """, (existing,))
            conn.commit()
            conn.close()
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Optimizer already running (run_id={existing}). Stop it first.",
            )

    # Remove stale stop flag
    if STOP_FLAG.exists():
        STOP_FLAG.unlink()

    # Create optimization_runs record
    conn = _db()
    cur = conn.execute("""
        INSERT INTO optimization_runs
            (status, population_size, max_generations, dimensions,
             crossover_prob, mutation_prob, tournament_size)
        VALUES ('RUNNING', ?, ?, 47, ?, ?, 3)
    """, (req.population_size, req.max_generations, req.crossover_prob, req.mutation_prob))
    run_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Launch subprocess
    script = BASE_DIR / "optimizer" / "_runner.py"
    cmd = [
        sys.executable, str(script),
        "--run-id",      str(run_id),
        "--population",  str(req.population_size),
        "--generations", str(req.max_generations),
        "--crossover",   str(req.crossover_prob),
        "--mutation",    str(req.mutation_prob),
        "--stop-flag",   str(STOP_FLAG),
        "--trade-mode",  req.trade_mode,
        "--phase",       req.phase,
        "--max-cycles",  str(max(1, min(10, req.max_cycles))),
    ]
    if req.include_archive:
        cmd.append("--include-archive")

    log_path = BASE_DIR / f"optimizer_run_{run_id}.log"
    global _active_proc
    with open(log_path, "w") as log_f:
        _active_proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR),
        )

    return RunResponse(
        run_id=run_id,
        status="RUNNING",
        message=f"Optimization started (run_id={run_id}). "
                f"Poll /runs/{run_id}/progress for updates.",
    )


# ---------------------------------------------------------------------------
# GET /runs — list recent runs
# ---------------------------------------------------------------------------

@router.get("/runs")
async def list_runs(limit: int = 10):
    conn = _db()
    rows = conn.execute("""
        SELECT id, status, started_at, completed_at, duration_seconds,
               population_size, max_generations, generations_run,
               best_train_fitness, best_val_fitness, proposals_generated
        FROM optimization_runs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /runs/{run_id}/progress — live polling endpoint
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/progress", response_model=ProgressResponse)
async def get_progress(run_id: int):
    conn = _db()

    run = conn.execute(
        "SELECT * FROM optimization_runs WHERE id=?", (run_id,)
    ).fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Recent generations (last 10)
    gens = conn.execute("""
        SELECT generation, best_train_fitness, avg_train_fitness,
               best_val_fitness, train_val_gap, recorded_at
        FROM optimization_generations
        WHERE run_id=?
        ORDER BY generation DESC
        LIMIT 10
    """, (run_id,)).fetchall()

    proposals_ready = conn.execute(
        "SELECT COUNT(*) FROM config_proposals WHERE run_id=? AND review_status='PENDING'",
        (run_id,)
    ).fetchone()[0]

    conn.close()

    train_fit = run["best_train_fitness"]
    val_fit   = run["best_val_fitness"]
    gap = None
    if train_fit and val_fit and train_fit > 0:
        gap = round((train_fit - val_fit) / train_fit * 100, 1)

    # Elapsed seconds
    elapsed = run["duration_seconds"]
    if elapsed is None and run["started_at"]:
        from datetime import datetime, timezone
        try:
            started = datetime.fromisoformat(run["started_at"])
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            elapsed = (now - started).total_seconds()
        except Exception:
            pass

    return ProgressResponse(
        run_id=run_id,
        status=run["status"],
        generations_run=run["generations_run"] or 0,
        max_generations=run["max_generations"],
        best_train_fitness=train_fit,
        best_val_fitness=val_fit,
        train_val_gap_pct=gap,
        recent_generations=[dict(g) for g in gens],
        proposals_ready=proposals_ready,
        elapsed_seconds=elapsed,
        current_cycle=run["current_cycle"] or 1,
        max_cycles=run["max_cycles"] or 1,
    )


# ---------------------------------------------------------------------------
# POST /runs/{run_id}/stop
# ---------------------------------------------------------------------------

def _kill_runner_processes() -> int:
    """
    Find and kill all running _runner.py subprocess instances.
    Returns the number of processes killed.
    Falls back gracefully if psutil is not available.
    """
    killed = 0
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if any("_runner.py" in str(arg) for arg in cmdline):
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        pass  # psutil not installed — fall through to _active_proc only
    return killed


@router.post("/runs/{run_id}/stop")
async def stop_optimizer(run_id: int):
    """
    Stop a running optimization.

    Robust against server restarts (deploy): even if _active_proc is None
    (lost on restart), we still write the stop flag and search for the
    _runner.py subprocess via OS process list.

    Also handles stale RUNNING records: if the DB says RUNNING but no
    process is found, the record is marked FAILED so a new run can start.
    """
    run_id_active = _running_run_id()
    if run_id_active != run_id:
        raise HTTPException(
            status_code=400,
            detail=f"Run {run_id} is not currently running.",
        )

    # 1. Stop flag — subprocess ellenőrzi generációk között
    STOP_FLAG.touch()

    killed = 0

    # 2. _active_proc alapú terminálás (normál eset, nincs restart)
    global _active_proc
    if _active_proc is not None and _active_proc.poll() is None:
        try:
            _active_proc.terminate()
            killed += 1
        except Exception:
            pass

    # 3. OS-szintű keresés: deploy/restart után _active_proc=None,
    #    de a subprocess még futhat → megkeressük és leállítjuk
    if killed == 0:
        killed += _kill_runner_processes()

    # 4. Ha nincs élő process de DB-ben RUNNING van → stale record → FAILED
    if killed == 0:
        conn = _db()
        conn.execute("""
            UPDATE optimization_runs
            SET status = 'FAILED', completed_at = CURRENT_TIMESTAMP,
                error_message = 'Process not found — likely killed by server restart. Marked FAILED by stop request.'
            WHERE id = ? AND status = 'RUNNING'
        """, (run_id,))
        conn.commit()
        conn.close()
        return {
            "message": f"Run {run_id}: no live process found (server restart?). "
                       f"Record marked FAILED — you can start a new run.",
            "killed": 0,
        }

    return {
        "message": f"Stop signal sent to run {run_id}. Terminated {killed} process(es).",
        "killed": killed,
    }


# ---------------------------------------------------------------------------
# GET /proposals — list proposals
# ---------------------------------------------------------------------------

@router.get("/proposals")
async def list_proposals(run_id: Optional[int] = None, limit: int = 10):
    conn = _db()
    if run_id:
        rows = conn.execute("""
            SELECT id, run_id, rank, verdict, review_status,
                   train_fitness, val_fitness, test_fitness, baseline_fitness,
                   fitness_improvement_pct,
                   test_trade_count, test_win_rate, test_profit_factor,
                   baseline_profit_factor, train_val_gap, overfitting_ok,
                   bootstrap_p_value, bootstrap_significant, bootstrap_iterations,
                   wf_window_count, wf_positive_count, wf_result_json, wf_consistent,
                   regime_trending_pf, regime_trending_trades,
                   regime_sideways_pf, regime_sideways_trades,
                   regime_highvol_pf,  regime_highvol_trades,
                   gate_min_trades_ok, gate_fitness_improvement_ok,
                   gate_bootstrap_ok, gate_overfitting_ok,
                   gate_profit_factor_ok, gate_sideways_pf_ok,
                   verdict_reason,
                   config_diff_json,
                   created_at, reviewed_at
            FROM config_proposals
            WHERE run_id=?
            ORDER BY rank ASC
            LIMIT ?
        """, (run_id, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, run_id, rank, verdict, review_status,
                   train_fitness, val_fitness, test_fitness, baseline_fitness,
                   fitness_improvement_pct,
                   test_trade_count, test_win_rate, test_profit_factor,
                   baseline_profit_factor, train_val_gap, overfitting_ok,
                   bootstrap_p_value, bootstrap_significant, bootstrap_iterations,
                   wf_window_count, wf_positive_count, wf_result_json, wf_consistent,
                   regime_trending_pf, regime_trending_trades,
                   regime_sideways_pf, regime_sideways_trades,
                   regime_highvol_pf,  regime_highvol_trades,
                   gate_min_trades_ok, gate_fitness_improvement_ok,
                   gate_bootstrap_ok, gate_overfitting_ok,
                   gate_profit_factor_ok, gate_sideways_pf_ok,
                   verdict_reason,
                   config_diff_json,
                   created_at, reviewed_at
            FROM config_proposals
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # Parse JSON fields
        for key in ("config_diff_json", "wf_result_json"):
            if d.get(key) and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# GET /proposals/{id} — full proposal detail (including config diff)
# ---------------------------------------------------------------------------

@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: int):
    conn = _db()
    row = conn.execute(
        "SELECT * FROM config_proposals WHERE id=?", (proposal_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")
    result = dict(row)
    # Parse JSON fields
    for key in ["config_vector_json", "config_diff_json", "wf_result_json"]:
        if result.get(key):
            try:
                result[key] = json.loads(result[key])
            except Exception:
                pass
    return result


# ---------------------------------------------------------------------------
# POST /proposals/{id}/approve
# ---------------------------------------------------------------------------

@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: int):
    """
    Apply the proposed config vector to config.json.
    Updates the live configuration immediately.
    """
    conn = _db()
    row = conn.execute(
        "SELECT config_vector_json, verdict, review_status FROM config_proposals WHERE id=?",
        (proposal_id,)
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Proposal not found")

    if row["review_status"] != "PENDING":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already processed: {row['review_status']}"
        )

    if row["verdict"] == "REJECTED":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Cannot approve a REJECTED proposal. Gate validation failed."
        )

    # Decode and apply config
    try:
        vector = json.loads(row["config_vector_json"])
    except Exception:
        conn.close()
        raise HTTPException(status_code=500, detail="Invalid config_vector_json in proposal")

    sys.path.insert(0, str(BASE_DIR))
    from optimizer.parameter_space import decode_vector
    from src.config import save_config_to_file

    decoded_cfg = decode_vector(vector)

    # Load current config.json and merge only optimizable keys
    config_path = BASE_DIR / "config.json"
    with open(config_path) as f:
        current_cfg = json.load(f)

    # Mentjük az írás ELŐTTI állapotot a config_history táblába
    try:
        from src.config_history import save_config_history
        save_config_history(f"optimizer:{proposal_id}", dict(current_cfg))
    except Exception as _he:
        print(f"[WARN] config_history: optimizer snapshot mentés sikertelen: {_he}")

    current_cfg.update(decoded_cfg)

    # Handle DECAY_WEIGHTS dict format
    current_cfg["DECAY_WEIGHTS"] = {
        "0-2h":   1.0,
        "2-6h":   decoded_cfg.get("DECAY_2_6H", 0.85),
        "6-12h":  decoded_cfg.get("DECAY_6_12H", 0.60),
        "12-24h": decoded_cfg.get("DECAY_12_24H", 0.35),
    }
    # Remove flat decay keys (not part of original config.json format)
    for k in ["DECAY_0_2H", "DECAY_2_6H", "DECAY_6_12H", "DECAY_12_24H"]:
        current_cfg.pop(k, None)

    with open(config_path, "w") as f:
        json.dump(current_cfg, f, indent=2)

    # In-memory singleton frissítése — nélküle az API a régi értékeket adná vissza
    # egészen az alkalmazás következő újraindításáig.
    from src.config import reload_config
    reload_config()

    # Mark proposal as approved
    conn.execute(
        "UPDATE config_proposals SET review_status='APPROVED', reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
        (proposal_id,)
    )
    conn.commit()
    conn.close()

    return {
        "message":     f"Proposal {proposal_id} approved and config.json updated.",
        "applied_keys": list(decoded_cfg.keys()),
    }


# ---------------------------------------------------------------------------
# POST /proposals/{id}/reject
# ---------------------------------------------------------------------------

@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: int):
    conn = _db()
    row = conn.execute(
        "SELECT review_status FROM config_proposals WHERE id=?", (proposal_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Proposal not found")
    if row["review_status"] != "PENDING":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already processed: {row['review_status']}"
        )
    conn.execute(
        "UPDATE config_proposals SET review_status='REJECTED_BY_USER', reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
        (proposal_id,)
    )
    conn.commit()
    conn.close()
    return {"message": f"Proposal {proposal_id} rejected."}


# ---------------------------------------------------------------------------
# GET /status — scheduler + market state for UI
# ---------------------------------------------------------------------------

@router.get("/status")
async def optimizer_status():
    """Returns current optimizer and scheduler state for the UI idle panel."""
    conn = _db()

    # Latest run
    run = conn.execute("""
        SELECT id, status, started_at, completed_at, generations_run,
               best_train_fitness, proposals_generated
        FROM optimization_runs
        ORDER BY id DESC LIMIT 1
    """).fetchone()

    # Counts — signal_calculations (live) + archive_signals (historikus)
    live_signal_count = conn.execute(
        "SELECT COUNT(*) FROM signal_calculations"
    ).fetchone()[0]
    archive_signal_count = conn.execute(
        "SELECT COUNT(*) FROM archive_signals"
    ).fetchone()[0]
    signal_count = live_signal_count + archive_signal_count
    # Live CLOSED trade-ek + archive CLOSED trade-ek összesen
    live_trade_count = conn.execute(
        "SELECT COUNT(*) FROM simulated_trades WHERE status='CLOSED'"
    ).fetchone()[0]
    archive_trade_count = conn.execute(
        "SELECT COUNT(*) FROM archive_simulated_trades WHERE status='CLOSED'"
    ).fetchone()[0]
    trade_count = live_trade_count + archive_trade_count

    conn.close()

    active_run_id = _running_run_id()

    return {
        "optimizer_running": active_run_id is not None,
        "active_run_id":     active_run_id,
        "last_run":          dict(run) if run else None,
        "signal_count":      signal_count,
        "trade_count":       trade_count,
    }
