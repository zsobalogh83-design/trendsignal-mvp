/**
 * OptimizerPage — TrendSignal Self-Tuning Engine UI
 *
 * 4 view states:
 *   IDLE        — no active run, show stats + launch form
 *   RUNNING     — live progress: generation chart, fitness metrics, stop button
 *   RESULT      — run complete with proposals: gate cards, config diff, approve/reject
 *   NO_PROPOSAL — run complete but all proposals REJECTED
 *
 * Polling: 3s interval during RUNNING state via useOptimizerProgress hook.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  FiPlay, FiSquare, FiCheckCircle, FiXCircle, FiAlertTriangle,
  FiTrendingUp, FiActivity, FiClock, FiDatabase, FiSettings,
  FiChevronDown, FiChevronUp, FiInfo,
} from 'react-icons/fi';
import {
  useOptimizerStatus,
  useOptimizerProgress,
  useProposals,
  useStartOptimizer,
  useStopOptimizer,
  useApproveProposal,
  useRejectProposal,
} from '../hooks/useApi';
import type {
  ConfigProposal,
  OptimizerProgress,
  ProposalVerdict,
  WalkForwardWindow,
} from '../types/index';

// ============================================================
// Helpers
// ============================================================

function fmt2(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toFixed(2);
}

function fmt4(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toFixed(4);
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`;
}

function fmtDuration(sec: number | null): string {
  if (!sec) return '—';
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}m ${s}s`;
}

function verdictColor(v: ProposalVerdict | null | undefined): string {
  if (v === 'PROPOSABLE')  return 'text-emerald-400 bg-emerald-900/30 border-emerald-700';
  if (v === 'CONDITIONAL') return 'text-amber-400  bg-amber-900/30  border-amber-700';
  return 'text-red-400 bg-red-900/30 border-red-700';
}

function verdictIcon(v: ProposalVerdict | null | undefined) {
  if (v === 'PROPOSABLE')  return <FiCheckCircle className="w-4 h-4" />;
  if (v === 'CONDITIONAL') return <FiAlertTriangle className="w-4 h-4" />;
  return <FiXCircle className="w-4 h-4" />;
}

function gateIcon(ok: number) {
  return ok
    ? <FiCheckCircle className="w-4 h-4 text-emerald-400" />
    : <FiXCircle className="w-4 h-4 text-red-400" />;
}

// ============================================================
// Sub-components
// ============================================================

/** Mini progress bar for generation progress */
function GenProgressBar({ current, max }: { current: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (current / max) * 100) : 0;
  return (
    <div className="w-full bg-gray-700 rounded-full h-2 mt-1">
      <div
        className="bg-blue-500 h-2 rounded-full transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/** Simple sparkline using SVG for the last N generation fitness values */
function FitnessSpark({ points, color = '#3b82f6' }: { points: number[]; color?: string }) {
  if (points.length < 2) return null;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 0.001;
  const W = 160, H = 40, pad = 2;
  const xs = points.map((_, i) => pad + (i / (points.length - 1)) * (W - pad * 2));
  const ys = points.map(v => H - pad - ((v - min) / range) * (H - pad * 2));
  const d = xs.map((x, i) => `${i === 0 ? 'M' : 'L'} ${x} ${ys[i]}`).join(' ');
  return (
    <svg width={W} height={H} className="overflow-visible">
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" />
      <circle cx={xs[xs.length - 1]} cy={ys[ys.length - 1]} r="2.5" fill={color} />
    </svg>
  );
}

/** Collapsible config diff section */
function ConfigDiffTable({ diff }: { diff: Record<string, { before: number; after: number }> | null }) {
  const [open, setOpen] = useState(false);
  const entries = diff ? Object.entries(diff) : [];
  if (!entries.length) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-200 transition-colors"
      >
        {open ? <FiChevronUp /> : <FiChevronDown />}
        {entries.length} változtatott paraméter
      </button>
      {open && (
        <div className="mt-2 rounded-lg border border-gray-700 overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-800 text-gray-400">
                <th className="text-left px-3 py-1.5">Paraméter</th>
                <th className="text-right px-3 py-1.5">Előtte</th>
                <th className="text-right px-3 py-1.5">Utána</th>
                <th className="text-right px-3 py-1.5">Delta</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([key, val]) => {
                const delta = val.after - val.before;
                return (
                  <tr key={key} className="border-t border-gray-700 hover:bg-gray-800/50">
                    <td className="px-3 py-1 font-mono text-gray-300">{key}</td>
                    <td className="px-3 py-1 text-right text-gray-400">{fmt4(val.before)}</td>
                    <td className="px-3 py-1 text-right text-blue-300">{fmt4(val.after)}</td>
                    <td className={`px-3 py-1 text-right font-medium ${delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {delta >= 0 ? '+' : ''}{fmt4(delta)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Walk-forward windows table */
function WalkForwardTable({ windows }: { windows: WalkForwardWindow[] }) {
  if (!windows.length) return <p className="text-xs text-gray-500 mt-1">Nincs adat</p>;
  return (
    <div className="mt-2 rounded border border-gray-700 overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-gray-800 text-gray-400">
            <th className="text-left px-2 py-1">Ablak</th>
            <th className="text-left px-2 py-1">Időszak</th>
            <th className="text-right px-2 py-1">Prop PF</th>
            <th className="text-right px-2 py-1">Base PF</th>
            <th className="text-right px-2 py-1">Delta</th>
          </tr>
        </thead>
        <tbody>
          {windows.map(w => (
            <tr key={w.window} className="border-t border-gray-700">
              <td className="px-2 py-1 text-gray-400">#{w.window}</td>
              <td className="px-2 py-1 text-gray-400 font-mono text-[10px]">{w.signal_range}</td>
              <td className="px-2 py-1 text-right text-blue-300">{fmt2(w.prop_pf)}</td>
              <td className="px-2 py-1 text-right text-gray-400">{fmt2(w.base_pf)}</td>
              <td className={`px-2 py-1 text-right font-medium ${w.positive ? 'text-emerald-400' : 'text-red-400'}`}>
                {w.positive ? '+' : ''}{fmt2(w.pf_delta)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** One proposal card */
function ProposalCard({
  proposal,
  onApprove,
  onReject,
  approving,
  rejecting,
}: {
  proposal: ConfigProposal;
  onApprove: () => void;
  onReject: () => void;
  approving: boolean;
  rejecting: boolean;
}) {
  const [wfOpen, setWfOpen] = useState(false);

  const diff = typeof proposal.config_diff_json === 'string'
    ? JSON.parse(proposal.config_diff_json || '{}')
    : (proposal.config_diff_json ?? {});

  const wfWindows: WalkForwardWindow[] = Array.isArray(proposal.wf_result_json)
    ? proposal.wf_result_json
    : (typeof proposal.wf_result_json === 'string'
        ? JSON.parse(proposal.wf_result_json || '[]')
        : []);

  const isPending   = proposal.review_status === 'PENDING';
  const isApproved  = proposal.review_status === 'APPROVED';
  const isRejected  = proposal.review_status === 'REJECTED_BY_USER';

  return (
    <div className={`rounded-xl border p-5 space-y-4 ${
      proposal.verdict === 'PROPOSABLE'
        ? 'border-emerald-700 bg-emerald-950/20'
        : proposal.verdict === 'CONDITIONAL'
          ? 'border-amber-700 bg-amber-950/20'
          : 'border-gray-700 bg-gray-900'
    }`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-sm">#{proposal.rank}. javaslat</span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${verdictColor(proposal.verdict)}`}>
              {verdictIcon(proposal.verdict)}
              {proposal.verdict}
            </span>
          </div>
          {proposal.verdict_reason && (
            <p className="text-xs text-gray-500 mt-0.5">{proposal.verdict_reason}</p>
          )}
        </div>
        {/* Reviewed status badge */}
        {isApproved && (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-emerald-900/40 text-emerald-400 text-xs border border-emerald-700">
            <FiCheckCircle className="w-3 h-3" /> Elfogadva
          </span>
        )}
        {isRejected && (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-gray-800 text-gray-500 text-xs border border-gray-700">
            <FiXCircle className="w-3 h-3" /> Elutasítva
          </span>
        )}
      </div>

      {/* Fitness metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Train fitness',   value: fmt4(proposal.train_fitness) },
          { label: 'Val fitness',     value: fmt4(proposal.val_fitness) },
          { label: 'Test fitness',    value: fmt4(proposal.test_fitness) },
          { label: 'Baseline',        value: fmt4(proposal.baseline_fitness) },
          { label: 'Javulás',         value: fmtPct(proposal.fitness_improvement_pct), highlight: (proposal.fitness_improvement_pct ?? 0) >= 10 },
          { label: 'Profit Factor',   value: fmt2(proposal.test_profit_factor) },
          { label: 'Base PF',         value: fmt2(proposal.baseline_profit_factor) },
          { label: 'Win Rate',        value: fmt2((proposal.test_win_rate ?? 0) * 100) + '%' },
        ].map(({ label, value, highlight }) => (
          <div key={label} className="bg-gray-800/50 rounded-lg p-2.5">
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-sm font-semibold mt-0.5 ${highlight ? 'text-emerald-400' : 'text-gray-200'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Gate checklist */}
      <div className="space-y-1">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Acceptance Gates</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-1">
          {[
            { label: 'Min. 50 trade',      ok: proposal.gate_min_trades_ok,           val: `${proposal.test_trade_count ?? 0} db` },
            { label: 'Fitness +10%',       ok: proposal.gate_fitness_improvement_ok,  val: fmtPct(proposal.fitness_improvement_pct) },
            { label: 'PF delta ≥ 0.10',    ok: proposal.gate_profit_factor_ok,        val: fmt2((proposal.test_profit_factor ?? 0) - (proposal.baseline_profit_factor ?? 0)) },
            { label: 'Bootstrap p<0.05',   ok: proposal.gate_bootstrap_ok,            val: `p=${fmt4(proposal.bootstrap_p_value)}` },
            { label: 'Overfitting ≤20%',   ok: proposal.gate_overfitting_ok,          val: fmtPct(proposal.train_val_gap) },
            { label: 'Sideways PF ≥1.0',   ok: proposal.gate_sideways_pf_ok,         val: fmt2(proposal.regime_sideways_pf) + ' (warn)' },
          ].map(({ label, ok, val }) => (
            <div key={label} className="flex items-center gap-1.5 text-xs">
              {gateIcon(ok)}
              <span className="text-gray-300">{label}</span>
              <span className="text-gray-500 ml-auto">{val}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Regime breakdown */}
      <div>
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">Piaci Regime</p>
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Trending',  pf: proposal.regime_trending_pf, trades: proposal.regime_trending_trades,  color: 'text-blue-400' },
            { label: 'Sideways',  pf: proposal.regime_sideways_pf, trades: proposal.regime_sideways_trades,  color: 'text-amber-400' },
            { label: 'High Vol',  pf: proposal.regime_highvol_pf,  trades: proposal.regime_highvol_trades,   color: 'text-purple-400' },
          ].map(({ label, pf, trades, color }) => (
            <div key={label} className="bg-gray-800/40 rounded p-2 text-center">
              <p className={`text-xs font-medium ${color}`}>{label}</p>
              <p className="text-sm font-semibold text-gray-200 mt-0.5">PF {fmt2(pf)}</p>
              <p className="text-xs text-gray-500">{trades ?? 0} trade</p>
            </div>
          ))}
        </div>
      </div>

      {/* Walk-forward toggle */}
      {wfWindows.length > 0 && (
        <div>
          <button
            onClick={() => setWfOpen(o => !o)}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
          >
            {wfOpen ? <FiChevronUp /> : <FiChevronDown />}
            Walk-Forward ({proposal.wf_positive_count}/{proposal.wf_window_count} pozitív
            {proposal.wf_consistent ? ' — CONSISTENT' : ' — MIXED'})
          </button>
          {wfOpen && <WalkForwardTable windows={wfWindows} />}
        </div>
      )}

      {/* Config diff */}
      <ConfigDiffTable diff={diff} />

      {/* Action buttons */}
      {isPending && proposal.verdict !== 'REJECTED' && (
        <div className="flex gap-3 pt-1">
          <button
            onClick={onApprove}
            disabled={approving || rejecting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg
                       bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50
                       text-white text-sm font-semibold transition-colors"
          >
            <FiCheckCircle className="w-4 h-4" />
            {approving ? 'Alkalmazás...' : 'Jóváhagyás'}
          </button>
          <button
            onClick={onReject}
            disabled={approving || rejecting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg
                       bg-gray-700 hover:bg-gray-600 disabled:opacity-50
                       text-gray-200 text-sm font-semibold transition-colors"
          >
            <FiXCircle className="w-4 h-4" />
            {rejecting ? 'Elutasítás...' : 'Elutasítás'}
          </button>
        </div>
      )}
      {isPending && proposal.verdict === 'REJECTED' && (
        <div className="flex gap-3 pt-1">
          <button
            onClick={onReject}
            disabled={rejecting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg
                       bg-gray-700 hover:bg-gray-600 disabled:opacity-50
                       text-gray-300 text-sm transition-colors"
          >
            <FiXCircle className="w-4 h-4" />
            {rejecting ? 'Elutasítás...' : 'Elutasítás (nincs jobb)'}
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================================
// IDLE state
// ============================================================

function IdlePanel({
  signalCount,
  tradeCount,
  onStart,
  starting,
}: {
  signalCount: number;
  tradeCount: number;
  onStart: (pop: number, gen: number) => void;
  starting: boolean;
}) {
  const [population, setPopulation] = useState(80);
  const [generations, setGenerations] = useState(100);
  const [advanced, setAdvanced] = useState(false);

  const minTrades = 50; // acceptance gate minimum
  const ready = tradeCount >= minTrades;

  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-xl p-4 text-center">
          <FiDatabase className="w-5 h-5 text-blue-400 mx-auto mb-1" />
          <p className="text-2xl font-bold text-gray-100">{signalCount.toLocaleString()}</p>
          <p className="text-xs text-gray-400 mt-0.5">Jelzés a DB-ben</p>
        </div>
        <div className={`rounded-xl p-4 text-center ${ready ? 'bg-gray-800' : 'bg-amber-950/30 border border-amber-800'}`}>
          <FiTrendingUp className={`w-5 h-5 mx-auto mb-1 ${ready ? 'text-emerald-400' : 'text-amber-400'}`} />
          <p className="text-2xl font-bold text-gray-100">{tradeCount.toLocaleString()}</p>
          <p className={`text-xs mt-0.5 ${ready ? 'text-gray-400' : 'text-amber-400'}`}>
            {ready ? 'Lezárt trade (elegendő)' : `Lezárt trade (min. ${minTrades} kell)`}
          </p>
        </div>
      </div>

      {/* Launch config */}
      <div className="bg-gray-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <FiSettings className="w-4 h-4 text-gray-400" />
          <h3 className="text-sm font-medium text-gray-300">GA Konfiguráció</h3>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-400">Populáció mérete</label>
            <select
              value={population}
              onChange={e => setPopulation(+e.target.value)}
              className="mt-1 w-full bg-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {[20, 40, 80, 120].map(v => <option key={v} value={v}>{v} egyén</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400">Generációk száma</label>
            <select
              value={generations}
              onChange={e => setGenerations(+e.target.value)}
              className="mt-1 w-full bg-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {[10, 25, 50, 100].map(v => <option key={v} value={v}>{v} gen.</option>)}
            </select>
          </div>
        </div>

        {/* Estimated runtime */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <FiClock className="w-3.5 h-3.5" />
          <span>
            Becsült futásidő: ~{Math.round(population * generations * 0.032 / 60)}–
            {Math.round(population * generations * 0.06 / 60)} perc
          </span>
        </div>

        {/* Advanced toggle */}
        <button
          onClick={() => setAdvanced(a => !a)}
          className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
        >
          {advanced ? <FiChevronUp /> : <FiChevronDown />} Haladó beállítások
        </button>

        {advanced && (
          <div className="text-xs text-gray-500 bg-gray-900/50 rounded-lg p-3 space-y-1">
            <p>• Crossover valószínűség: 0.70 (2-pont)</p>
            <p>• Mutáció valószínűség: 0.20 (Gauss, σ=5%)</p>
            <p>• Szelekció: Tournament (k=3)</p>
            <p>• Elitizmus: Top-2 megőrzése</p>
            <p>• Dimenziók: 40 (periódusok nélkül)</p>
          </div>
        )}

        {!ready && (
          <div className="flex items-start gap-2 bg-amber-950/30 border border-amber-800 rounded-lg p-3">
            <FiAlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-300">
              Az elfogadási kapu minimum {minTrades} lezárt trade-t igényel a test seten.
              Jelenleg {tradeCount} db van. Az optimalizáló elindítható, de a javaslatok
              valószínűleg REJECTED státuszt kapnak.
            </p>
          </div>
        )}

        <button
          onClick={() => onStart(population, generations)}
          disabled={starting}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                     bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-semibold text-sm transition-colors"
        >
          <FiPlay className="w-4 h-4" />
          {starting ? 'Indítás...' : 'Optimalizáló indítása'}
        </button>
      </div>
    </div>
  );
}

// ============================================================
// RUNNING state
// ============================================================

function RunningPanel({
  progress,
  runId,
  onStop,
  stopping,
}: {
  progress: OptimizerProgress;
  runId: number;
  onStop: () => void;
  stopping: boolean;
}) {
  const gens = progress.recent_generations ?? [];
  // gens are sorted DESC from API → reverse for chart
  const sortedGens = [...gens].reverse();
  const trainPoints = sortedGens.map(g => g.best_train_fitness);
  const valPoints   = sortedGens.map(g => g.best_val_fitness ?? 0);

  const pct = progress.max_generations > 0
    ? Math.round((progress.generations_run / progress.max_generations) * 100)
    : 0;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* Header: progress + stop */}
      <div className="bg-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
              <FiActivity className="w-4 h-4 text-blue-400 animate-pulse" />
              Futás #{runId}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {progress.generations_run} / {progress.max_generations} generáció
              {progress.elapsed_seconds != null && ` · ${fmtDuration(progress.elapsed_seconds)} eltelt`}
            </p>
          </div>
          <button
            onClick={onStop}
            disabled={stopping}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-900/40
                       hover:bg-red-900/70 text-red-400 text-xs font-medium border border-red-800
                       transition-colors disabled:opacity-50"
          >
            <FiSquare className="w-3.5 h-3.5" />
            {stopping ? 'Leállítás...' : 'Leállítás'}
          </button>
        </div>

        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500">
            <span>{pct}%</span>
            <span>{progress.max_generations - progress.generations_run} gen. maradt</span>
          </div>
          <GenProgressBar current={progress.generations_run} max={progress.max_generations} />
        </div>
      </div>

      {/* Fitness metrics */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Legjobb train', value: fmt4(progress.best_train_fitness), color: 'text-blue-400' },
          { label: 'Legjobb val',   value: fmt4(progress.best_val_fitness),   color: 'text-emerald-400' },
          { label: 'Train/Val gap', value: fmtPct(progress.train_val_gap_pct), color: (progress.train_val_gap_pct ?? 0) > 20 ? 'text-amber-400' : 'text-gray-300' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-lg font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Live sparklines */}
      {sortedGens.length >= 2 && (
        <div className="bg-gray-800 rounded-xl p-5">
          <p className="text-xs text-gray-400 font-medium mb-3">Fitness evolúció (utolsó {sortedGens.length} gen.)</p>
          <div className="flex gap-8">
            <div>
              <p className="text-xs text-blue-400 mb-1">Train best</p>
              <FitnessSpark points={trainPoints} color="#3b82f6" />
            </div>
            <div>
              <p className="text-xs text-emerald-400 mb-1">Val best</p>
              <FitnessSpark points={valPoints} color="#34d399" />
            </div>
          </div>
        </div>
      )}

      {/* Recent generations table */}
      {gens.length > 0 && (
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700">
            <p className="text-xs font-medium text-gray-400">Legutóbbi generációk</p>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left px-4 py-2">Gen.</th>
                <th className="text-right px-4 py-2">Best train</th>
                <th className="text-right px-4 py-2">Avg train</th>
                <th className="text-right px-4 py-2">Val best</th>
                <th className="text-right px-4 py-2">Gap</th>
              </tr>
            </thead>
            <tbody>
              {gens.map(g => (
                <tr key={g.generation} className="border-t border-gray-700/50 hover:bg-gray-700/20">
                  <td className="px-4 py-2 text-gray-400">#{g.generation}</td>
                  <td className="px-4 py-2 text-right text-blue-300">{fmt4(g.best_train_fitness)}</td>
                  <td className="px-4 py-2 text-right text-gray-400">{fmt4(g.avg_train_fitness)}</td>
                  <td className="px-4 py-2 text-right text-emerald-300">{fmt4(g.best_val_fitness)}</td>
                  <td className={`px-4 py-2 text-right ${(g.train_val_gap ?? 0) > 20 ? 'text-amber-400' : 'text-gray-400'}`}>
                    {fmtPct(g.train_val_gap)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============================================================
// NO_PROPOSAL state — diagnosztikai panel a részeredményekkel
// ============================================================

function FailedGateBadge({ label, ok, val }: { label: string; ok: number; val: string }) {
  return (
    <div className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs ${
      ok ? 'bg-emerald-950/30 border border-emerald-800' : 'bg-red-950/30 border border-red-800'
    }`}>
      <span className="flex items-center gap-1.5">
        {ok
          ? <FiCheckCircle className="w-3.5 h-3.5 text-emerald-400" />
          : <FiXCircle className="w-3.5 h-3.5 text-red-400" />}
        <span className={ok ? 'text-emerald-300' : 'text-red-300'}>{label}</span>
      </span>
      <span className="text-gray-400 font-mono">{val}</span>
    </div>
  );
}

function NoProposalPanel({
  proposals,
  onRestart,
}: {
  proposals: ConfigProposal[];
  onRestart: () => void;
}) {
  const [showDiff, setShowDiff] = useState(false);

  // Legjobb proposal a train fitness alapján
  const best = proposals.length > 0
    ? [...proposals].sort((a, b) => b.train_fitness - a.train_fitness)[0]
    : null;

  const diff = best
    ? (typeof best.config_diff_json === 'string'
        ? JSON.parse(best.config_diff_json || '{}')
        : (best.config_diff_json ?? {}))
    : {};

  const diffEntries = Object.entries(diff as Record<string, { before: number; after: number }>);

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* Fejléc */}
      <div className="flex items-start gap-3 bg-amber-950/30 border border-amber-800 rounded-xl p-4">
        <FiAlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-amber-300">Nem született elfogadható javaslat</p>
          <p className="text-xs text-amber-500 mt-0.5">
            A GA talált jobb train-fitness konfigurációt, de az egyik kötelező gate nem teljesült.
            Az alábbi részeredmények segítenek megérteni a bukás okát.
          </p>
        </div>
      </div>

      {best && (
        <>
          {/* Legjobb proposal fitness adatai */}
          <div className="bg-gray-800 rounded-xl p-4 space-y-3">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">
              Legjobb megtalált konfiguráció (train alapján)
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Train fitness',  value: fmt4(best.train_fitness),  color: 'text-blue-400' },
                { label: 'Val fitness',    value: fmt4(best.val_fitness),    color: best.val_fitness > 0 ? 'text-emerald-400' : 'text-red-400' },
                { label: 'Test fitness',   value: fmt4(best.test_fitness),   color: best.test_fitness > 0 ? 'text-emerald-400' : 'text-red-400' },
                { label: 'Train/Val gap',  value: fmtPct(best.train_val_gap), color: (best.train_val_gap ?? 100) > 20 ? 'text-amber-400' : 'text-gray-300' },
                { label: 'Test trades',    value: `${best.test_trade_count ?? 0} db`, color: (best.test_trade_count ?? 0) >= 50 ? 'text-emerald-400' : 'text-red-400' },
                { label: 'Profit Factor',  value: fmt2(best.test_profit_factor), color: 'text-gray-200' },
                { label: 'Bootstrap p',    value: fmt4(best.bootstrap_p_value),  color: (best.bootstrap_p_value ?? 1) < 0.05 ? 'text-emerald-400' : 'text-red-400' },
                { label: 'Fitness javulás',value: fmtPct(best.fitness_improvement_pct), color: (best.fitness_improvement_pct ?? 0) >= 10 ? 'text-emerald-400' : 'text-red-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-gray-900/50 rounded-lg p-2.5">
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className={`text-sm font-semibold mt-0.5 ${color}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Gate eredmények */}
          <div className="bg-gray-800 rounded-xl p-4 space-y-2">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">Gate eredmények</p>
            <FailedGateBadge label="Min. 50 trade a test seten"  ok={best.gate_min_trades_ok}          val={`${best.test_trade_count ?? 0} / 50`} />
            <FailedGateBadge label="Fitness javulás ≥ 10%"       ok={best.gate_fitness_improvement_ok} val={fmtPct(best.fitness_improvement_pct)} />
            <FailedGateBadge label="Profit Factor delta ≥ 0.10"  ok={best.gate_profit_factor_ok}       val={fmt2((best.test_profit_factor ?? 0) - (best.baseline_profit_factor ?? 0))} />
            <FailedGateBadge label="Bootstrap p-érték < 0.05"    ok={best.gate_bootstrap_ok}           val={`p = ${fmt4(best.bootstrap_p_value)}`} />
            <FailedGateBadge label="Overfitting ≤ 20%"           ok={best.gate_overfitting_ok}         val={fmtPct(best.train_val_gap)} />
          </div>

          {/* Config diff — összecsukható */}
          {diffEntries.length > 0 && (
            <div className="bg-gray-800 rounded-xl overflow-hidden">
              <button
                onClick={() => setShowDiff(o => !o)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-750 transition-colors"
              >
                <span className="text-xs font-medium text-gray-400">
                  A GA által javasolt {diffEntries.length} paramétermódosítás (nem alkalmazva)
                </span>
                {showDiff ? <FiChevronUp className="w-4 h-4 text-gray-500" /> : <FiChevronDown className="w-4 h-4 text-gray-500" />}
              </button>
              {showDiff && (
                <table className="w-full text-xs border-t border-gray-700">
                  <thead>
                    <tr className="bg-gray-900 text-gray-500">
                      <th className="text-left px-4 py-2">Paraméter</th>
                      <th className="text-right px-4 py-2">Előtte</th>
                      <th className="text-right px-4 py-2">Utána</th>
                      <th className="text-right px-4 py-2">Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {diffEntries.map(([key, val]) => {
                      const delta = val.after - val.before;
                      return (
                        <tr key={key} className="border-t border-gray-700/50 hover:bg-gray-700/20">
                          <td className="px-4 py-1.5 font-mono text-gray-300">{key}</td>
                          <td className="px-4 py-1.5 text-right text-gray-500">{fmt4(val.before)}</td>
                          <td className="px-4 py-1.5 text-right text-blue-300">{fmt4(val.after)}</td>
                          <td className={`px-4 py-1.5 text-right font-medium ${delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {delta >= 0 ? '+' : ''}{fmt4(delta)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}

      {/* Teendők panel */}
      <div className="bg-gray-800 rounded-xl p-4 space-y-2">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Következő lépések</p>
        <ul className="text-xs text-gray-500 space-y-1.5">
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">→</span>
            <span>Várd meg, amíg több backtest lezárul, hogy a test set elérje a 50 trade-es minimumot</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">→</span>
            <span>Ha a val fitness 0 volt: az optimalizáló túltanult a train periódusra — más időszakban próbáld</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">→</span>
            <span>Ha a bootstrap nem szignifikáns: az eredmény véletlen lehet — nagyobb populációval/több generációval futtasd újra</span>
          </li>
        </ul>
      </div>

      <div className="flex gap-3">
        <button
          onClick={onRestart}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl
                     bg-blue-600 hover:bg-blue-500 text-white text-sm
                     font-semibold transition-colors"
        >
          <FiPlay className="w-4 h-4" />
          Új futás indítása
        </button>
      </div>
    </div>
  );
}

// ============================================================
// Main Page
// ============================================================

export function OptimizerPage() {
  // ---- Status (idle info, active run detection) ----
  const { data: status, isLoading: statusLoading } = useOptimizerStatus();

  // ---- Determine active run ----
  const activeRunId: number | null = status?.active_run_id ?? null;
  const isRunning = !!activeRunId;

  // ---- Live progress (polls every 3s when running) ----
  const { data: progress } = useOptimizerProgress(activeRunId, isRunning);

  // ---- Find the last completed run for proposals ----
  const lastRun = status?.last_run ?? null;
  const lastCompletedRunId =
    lastRun && (lastRun.status === 'COMPLETED' || lastRun.status === 'STOPPED')
      ? lastRun.id
      : null;

  // ---- Proposals for last completed run ----
  const { data: proposals, refetch: refetchProposals } = useProposals(lastCompletedRunId ?? undefined);

  // ---- Mutations ----
  const startMut    = useStartOptimizer();
  const stopMut     = useStopOptimizer();
  const approveMut  = useApproveProposal();
  const rejectMut   = useRejectProposal();

  // Track which proposal is being approved/rejected
  const [actingOn, setActingOn] = useState<number | null>(null);

  // ---- View mode ----
  type ViewMode = 'IDLE' | 'RUNNING' | 'RESULT' | 'NO_PROPOSAL';

  const viewMode: ViewMode = (() => {
    if (isRunning) return 'RUNNING';
    if (!lastCompletedRunId) return 'IDLE';
    if (!proposals || proposals.length === 0) return 'NO_PROPOSAL';
    const allRejected = proposals.every(p => p.verdict === 'REJECTED');
    if (allRejected) return 'NO_PROPOSAL';
    return 'RESULT';
  })();

  // ---- Handlers ----
  const handleStart = useCallback((pop: number, gen: number) => {
    startMut.mutate({ population_size: pop, max_generations: gen });
  }, [startMut]);

  const handleStop = useCallback(() => {
    if (activeRunId) stopMut.mutate(activeRunId);
  }, [activeRunId, stopMut]);

  const handleApprove = useCallback((proposalId: number) => {
    setActingOn(proposalId);
    approveMut.mutate(proposalId, {
      onSettled: () => {
        setActingOn(null);
        refetchProposals();
      },
    });
  }, [approveMut, refetchProposals]);

  const handleReject = useCallback((proposalId: number) => {
    setActingOn(proposalId);
    rejectMut.mutate(proposalId, {
      onSettled: () => {
        setActingOn(null);
        refetchProposals();
      },
    });
  }, [rejectMut, refetchProposals]);

  // Auto-switch to RESULT when run finishes and proposals arrive
  useEffect(() => {
    if (
      progress?.status === 'COMPLETED' &&
      progress?.proposals_ready > 0
    ) {
      refetchProposals();
    }
  }, [progress?.status, progress?.proposals_ready, refetchProposals]);

  // ---- Render ----
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Top bar */}
      <div className="border-b border-gray-800 bg-gray-900/80 sticky top-0 z-10 backdrop-blur">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-100">Self-Tuning Engine</h1>
            <p className="text-xs text-gray-500 mt-0.5">Genetikus algoritmus alapú paraméter-optimalizáló</p>
          </div>
          {/* Status pill */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
            viewMode === 'RUNNING'
              ? 'bg-blue-950/50 border-blue-700 text-blue-300'
              : viewMode === 'RESULT'
                ? 'bg-emerald-950/50 border-emerald-700 text-emerald-300'
                : 'bg-gray-800 border-gray-700 text-gray-400'
          }`}>
            {viewMode === 'RUNNING' && <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />}
            {viewMode === 'RUNNING'  ? 'FUTÁS' :
             viewMode === 'RESULT'   ? 'EREDMÉNY' :
             viewMode === 'NO_PROPOSAL' ? 'NINCS JAVASLAT' : 'VÁRAKOZÁS'}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {statusLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : viewMode === 'IDLE' ? (
          <IdlePanel
            signalCount={status?.signal_count ?? 0}
            tradeCount={status?.trade_count ?? 0}
            onStart={handleStart}
            starting={startMut.isPending}
          />
        ) : viewMode === 'RUNNING' && progress ? (
          <RunningPanel
            progress={progress}
            runId={activeRunId!}
            onStop={handleStop}
            stopping={stopMut.isPending}
          />
        ) : viewMode === 'RUNNING' ? (
          /* progress not yet loaded */
          <div className="flex items-center justify-center py-20 gap-3 text-gray-400">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Csatlakozás az optimalizálóhoz...</span>
          </div>
        ) : viewMode === 'RESULT' && proposals ? (
          <div className="space-y-6">
            {/* Section header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-gray-200">Javaslatok</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Futás #{lastCompletedRunId} · {proposals.length} javaslat
                  · {proposals.filter(p => p.verdict !== 'REJECTED').length} elfogadható
                </p>
              </div>
              <button
                onClick={() => handleStart(80, 100)}
                disabled={startMut.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
                           bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700
                           transition-colors disabled:opacity-50"
              >
                <FiPlay className="w-3.5 h-3.5" /> Új futás
              </button>
            </div>

            {/* Proposal cards */}
            {proposals.map(p => (
              <ProposalCard
                key={p.id}
                proposal={p}
                onApprove={() => handleApprove(p.id)}
                onReject={() => handleReject(p.id)}
                approving={approveMut.isPending && actingOn === p.id}
                rejecting={rejectMut.isPending && actingOn === p.id}
              />
            ))}
          </div>
        ) : (
          <NoProposalPanel
            proposals={proposals ?? []}
            onRestart={() => handleStart(80, 100)}
          />
        )}

        {/* Error toasts */}
        {startMut.error && (
          <div className="fixed bottom-6 right-6 bg-red-900 border border-red-700 text-red-200 text-sm px-4 py-3 rounded-xl shadow-lg max-w-xs">
            <strong>Hiba:</strong> {(startMut.error as Error).message}
          </div>
        )}
        {approveMut.error && (
          <div className="fixed bottom-6 right-6 bg-red-900 border border-red-700 text-red-200 text-sm px-4 py-3 rounded-xl shadow-lg max-w-xs">
            <strong>Jóváhagyás sikertelen:</strong> {(approveMut.error as Error).message}
          </div>
        )}
      </div>
    </div>
  );
}
