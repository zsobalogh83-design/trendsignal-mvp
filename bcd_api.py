"""
TrendSignal BCD Optimizer API

FastAPI router for Block Coordinate Descent optimization.
Follows the same pattern as optimizer_api.py.

Endpoints:
    POST /api/v1/optimizer/bcd/run                       Start a BCD run
    GET  /api/v1/optimizer/bcd/runs                      List BCD runs
    GET  /api/v1/optimizer/bcd/runs/{run_id}/progress    Live progress polling
    POST /api/v1/optimizer/bcd/runs/{run_id}/stop        Graceful stop
    GET  /api/v1/optimizer/bcd/runs/{run_id}/analysis    Block impact analysis
    GET  /api/v1/optimizer/bcd/runs/{run_id}/rounds      Per-round history

Version: 1.0
Date: 2026-03-07
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

BASE_DIR    = Path(__file__).resolve().parent
DB_PATH     = BASE_DIR / "trendsignal.db"
STOP_FLAG   = BASE_DIR / ".bcd_optimizer_stop"
LOG_DIR     = BASE_DIR

router = APIRouter(prefix="/api/v1/optimizer/bcd", tags=["BCD Optimizer"])

# Track the running subprocess
_bcd_process: Optional[subprocess.Popen] = None
_bcd_run_id:  Optional[int] = None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BcdRunRequest(BaseModel):
    max_rounds:  int   = Field(60,  ge=5,  le=300,  description="Maximum BCD rounds")
    max_dims:    int   = Field(7,   ge=2,  le=13,   description="Max active dims per round")
    patience:    int   = Field(12,  ge=3,  le=50,   description="Rounds without improvement before stopping")
    mini_pop:    int   = Field(40,  ge=10, le=200,  description="Mini GA population size")
    mini_gen:    int   = Field(60,  ge=10, le=300,  description="Mini GA generations per round")


class BcdRunResponse(BaseModel):
    run_id:  int
    status:  str
    message: str


class BcdProgressResponse(BaseModel):
    run_id:           int
    status:           str
    run_type:         str
    rounds_run:       int
    max_rounds:       int
    best_fitness:     Optional[float]
    baseline_fitness: Optional[float]
    recent_rounds:    list
    proposals_ready:  int
    elapsed_seconds:  Optional[float]


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _create_run_record(req: BcdRunRequest) -> int:
    conn = _db()
    cur = conn.execute("""
        INSERT INTO optimization_runs
            (status, run_type, population_size, max_generations, dimensions,
             crossover_prob, mutation_prob, tournament_size)
        VALUES ('RUNNING', 'BCD', ?, ?, 52, 0.70, 0.20, 3)
    """, (req.mini_pop, req.max_rounds))
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run", response_model=BcdRunResponse)
async def start_bcd_optimizer(req: BcdRunRequest):
    """
    Start a BCD optimization run as a background subprocess.
    Returns the run_id immediately; poll /runs/{run_id}/progress for updates.
    """
    global _bcd_process, _bcd_run_id

    # Check if a BCD run is already active
    if _bcd_process is not None and _bcd_process.poll() is None:
        raise HTTPException(
            status_code=409,
            detail=f"BCD optimizer already running (run_id={_bcd_run_id}). "
                   f"Stop it first via POST /runs/{_bcd_run_id}/stop",
        )

    # Remove stale stop flag
    if STOP_FLAG.exists():
        STOP_FLAG.unlink()

    # Create DB record
    run_id = _create_run_record(req)
    _bcd_run_id = run_id

    # Build subprocess command
    runner_script = BASE_DIR / "optimizer" / "_bcd_process.py"
    log_file      = LOG_DIR / f"bcd_run_{run_id}.log"

    cmd = [
        sys.executable, str(runner_script),
        "--run-id",     str(run_id),
        "--max-rounds", str(req.max_rounds),
        "--max-dims",   str(req.max_dims),
        "--patience",   str(req.patience),
        "--mini-pop",   str(req.mini_pop),
        "--mini-gen",   str(req.mini_gen),
        "--stop-flag",  str(STOP_FLAG),
        "--db-path",    str(DB_PATH),
    ]

    log_fh = open(str(log_file), "w", encoding="utf-8", buffering=1)
    _bcd_process = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=str(BASE_DIR),
    )

    return BcdRunResponse(
        run_id=run_id,
        status="RUNNING",
        message=(
            f"BCD optimizer started (run_id={run_id}). "
            f"Poll /api/v1/optimizer/bcd/runs/{run_id}/progress for updates. "
            f"Log: bcd_run_{run_id}.log"
        ),
    )


@router.get("/runs", response_model=List[dict])
async def list_bcd_runs(limit: int = 10):
    """List recent BCD optimization runs."""
    conn = _db()
    rows = conn.execute("""
        SELECT id, status, run_type, started_at, completed_at, duration_seconds,
               max_generations, generations_run,
               best_train_fitness, best_val_fitness, best_test_fitness,
               baseline_fitness, proposals_generated, bcd_block_impact
        FROM optimization_runs
        WHERE run_type = 'BCD'
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/runs/{run_id}/progress", response_model=BcdProgressResponse)
async def get_bcd_progress(run_id: int):
    """
    Live progress polling for a BCD run.
    Returns current round count, best fitness, and recent round history.
    """
    conn = _db()

    run = conn.execute(
        "SELECT * FROM optimization_runs WHERE id = ? AND run_type = 'BCD'",
        (run_id,),
    ).fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"BCD run {run_id} not found")

    # Recent rounds (last 20)
    rounds = conn.execute("""
        SELECT round_number, unit_ids, n_active_dims,
               fitness_before, fitness_after, improvement_pct, accepted, elapsed_seconds,
               recorded_at
        FROM bcd_rounds
        WHERE run_id = ?
        ORDER BY round_number DESC
        LIMIT 20
    """, (run_id,)).fetchall()

    # Pending proposals
    proposals_ready = conn.execute(
        "SELECT COUNT(*) FROM config_proposals WHERE run_id = ? AND review_status = 'PENDING'",
        (run_id,),
    ).fetchone()[0]

    conn.close()

    # Compute elapsed
    elapsed = None
    if run["started_at"] and run["status"] == "RUNNING":
        from datetime import datetime
        try:
            started = datetime.fromisoformat(run["started_at"])
            elapsed = (datetime.utcnow() - started).total_seconds()
        except Exception:
            pass
    elif run["duration_seconds"]:
        elapsed = run["duration_seconds"]

    return BcdProgressResponse(
        run_id=run_id,
        status=run["status"],
        run_type=run["run_type"] or "BCD",
        rounds_run=run["generations_run"] or 0,
        max_rounds=run["max_generations"] or 0,
        best_fitness=run["best_train_fitness"],
        baseline_fitness=run["baseline_fitness"],
        recent_rounds=[dict(r) for r in rounds],
        proposals_ready=proposals_ready,
        elapsed_seconds=round(elapsed, 1) if elapsed else None,
    )


@router.post("/runs/{run_id}/stop")
async def stop_bcd_run(run_id: int):
    """
    Gracefully stop a running BCD optimization.
    Creates the stop flag file; the runner checks it between rounds.
    """
    global _bcd_process, _bcd_run_id

    STOP_FLAG.touch()

    # Also send SIGTERM if we have a handle
    if _bcd_process is not None and _bcd_process.poll() is None:
        try:
            _bcd_process.terminate()
        except Exception:
            pass

    return {"message": f"Stop signal sent to BCD run {run_id}. Finishing current round..."}


@router.get("/runs/{run_id}/analysis")
async def get_block_analysis(run_id: int):
    """
    Block impact analysis for a completed (or in-progress) BCD run.

    Returns per-atomic-unit statistics:
      - rounds_selected: how many rounds this unit was chosen
      - rounds_accepted: how many of those rounds improved fitness
      - total_improvement: cumulative improvement attributed to this unit
    """
    conn = _db()

    run = conn.execute(
        "SELECT bcd_block_impact, status, generations_run FROM optimization_runs "
        "WHERE id = ? AND run_type = 'BCD'",
        (run_id,),
    ).fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"BCD run {run_id} not found")

    # Full round-level data for detailed analysis
    rounds = conn.execute("""
        SELECT round_number, unit_ids, n_active_dims,
               fitness_before, fitness_after, improvement_pct, accepted, elapsed_seconds
        FROM bcd_rounds
        WHERE run_id = ?
        ORDER BY round_number
    """, (run_id,)).fetchall()
    conn.close()

    # Build per-unit stats from round data
    unit_stats: dict = {}
    for r in rounds:
        unit_ids    = json.loads(r["unit_ids"])
        accepted    = bool(r["accepted"])
        n_units     = len(unit_ids)
        improvement = r["improvement_pct"]

        for uid in unit_ids:
            if uid not in unit_stats:
                unit_stats[uid] = {
                    "unit_id":           uid,
                    "rounds_selected":   0,
                    "rounds_accepted":   0,
                    "total_improvement": 0.0,
                    "best_improvement":  0.0,
                }
            st = unit_stats[uid]
            st["rounds_selected"] += 1
            if accepted:
                st["rounds_accepted"] += 1
                per_unit = improvement / n_units
                st["total_improvement"] = round(st["total_improvement"] + per_unit, 4)
                st["best_improvement"]  = round(max(st["best_improvement"], per_unit), 4)

    # Sort by total_improvement descending
    sorted_stats = sorted(
        unit_stats.values(),
        key=lambda x: x["total_improvement"],
        reverse=True,
    )

    return {
        "run_id":       run_id,
        "status":       run["status"],
        "rounds_total": run["generations_run"] or 0,
        "block_impact": sorted_stats,
        "summary": {
            "top_unit":    sorted_stats[0]["unit_id"] if sorted_stats else None,
            "total_rounds_accepted": sum(1 for r in rounds if r["accepted"]),
            "total_rounds_run":      len(rounds),
        },
    }


@router.get("/runs/{run_id}/rounds")
async def get_bcd_rounds(run_id: int, limit: int = 100):
    """
    Full per-round history for a BCD run.
    """
    conn = _db()

    run = conn.execute(
        "SELECT id FROM optimization_runs WHERE id = ? AND run_type = 'BCD'",
        (run_id,),
    ).fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"BCD run {run_id} not found")

    rounds = conn.execute("""
        SELECT round_number, unit_ids, active_dims, n_active_dims,
               fitness_before, fitness_after, improvement_pct, accepted,
               elapsed_seconds, recorded_at
        FROM bcd_rounds
        WHERE run_id = ?
        ORDER BY round_number
        LIMIT ?
    """, (run_id, limit)).fetchall()
    conn.close()

    result = []
    for r in rounds:
        row = dict(r)
        row["unit_ids"]   = json.loads(r["unit_ids"])
        row["active_dims"] = json.loads(r["active_dims"])
        result.append(row)

    return {"run_id": run_id, "rounds": result, "total": len(result)}


@router.get("/status")
async def bcd_status():
    """BCD optimizer status: is a run currently active?"""
    global _bcd_process, _bcd_run_id

    running = _bcd_process is not None and _bcd_process.poll() is None

    conn = _db()
    last_run = conn.execute("""
        SELECT id, status, started_at, completed_at, generations_run,
               best_train_fitness, baseline_fitness
        FROM optimization_runs
        WHERE run_type = 'BCD'
        ORDER BY id DESC LIMIT 1
    """).fetchone()
    conn.close()

    return {
        "bcd_running":   running,
        "active_run_id": _bcd_run_id if running else None,
        "last_run":      dict(last_run) if last_run else None,
    }
