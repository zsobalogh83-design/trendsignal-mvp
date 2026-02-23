import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TickerManagement } from '../components/TickerManagement';

// ── Shared style tokens ──────────────────────────────────────────────────────
const CSS = `
  .cfg-container { max-width: 960px; margin: 0 auto; padding: 20px; }

  .cfg-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 20px 0 24px; border-bottom: 1px solid rgba(99,102,241,.2); margin-bottom: 28px;
  }
  .cfg-back {
    display: flex; align-items: center; gap: 6px; color: #60a5fa;
    font-size: 13px; text-decoration: none; padding: 8px 14px;
    border-radius: 8px; background: rgba(59,130,246,.1);
  }
  .cfg-title {
    font-size: 26px; font-weight: 700;
    background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  }
  .cfg-save {
    display: flex; align-items: center; gap: 7px; padding: 10px 22px;
    border-radius: 8px; border: none; font-size: 14px; font-weight: 600;
    cursor: pointer; color: #fff;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  }
  .cfg-save:disabled { background: rgba(100,116,139,.5); cursor: not-allowed; opacity: .6; }

  .cfg-tabs {
    display: flex; gap: 4px; border-bottom: 2px solid rgba(51,65,85,.5);
    margin-bottom: 28px; overflow-x: auto;
  }
  .cfg-tab {
    padding: 10px 20px; background: transparent; border: none;
    color: #94a3b8; font-size: 13px; font-weight: 600; cursor: pointer;
    white-space: nowrap; border-bottom: 3px solid transparent;
    transition: color .2s, border-color .2s;
  }
  .cfg-tab.active { color: #60a5fa; border-bottom-color: #3b82f6; }

  .cfg-section {
    background: linear-gradient(135deg, rgba(30,41,59,.8) 0%, rgba(15,23,42,.9) 100%);
    border: 1px solid rgba(99,102,241,.25); border-radius: 14px;
    padding: 22px 24px; margin-bottom: 20px;
  }
  .cfg-section-title { font-size: 16px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
  .cfg-section-desc  { font-size: 12px; color: #64748b; margin-bottom: 18px; }

  .cfg-sub { font-size: 12px; font-weight: 700; color: #60a5fa;
    text-transform: uppercase; letter-spacing: .08em; margin: 18px 0 8px; }
  .cfg-sub:first-child { margin-top: 0; }

  /* param rows */
  .p-row {
    display: grid; grid-template-columns: 160px 1fr auto;
    align-items: center; gap: 10px 14px;
    padding: 8px 0; border-bottom: 1px solid rgba(51,65,85,.35);
  }
  .p-row:last-child { border-bottom: none; }
  .p-name { font-size: 13px; color: #cbd5e1; font-weight: 500; }
  .p-desc { font-size: 12px; color: #64748b; }
  .p-ctrl { display: flex; align-items: center; gap: 6px; justify-content: flex-end; }
  .p-unit { font-size: 12px; color: #64748b; white-space: nowrap; }

  /* inputs */
  .p-input {
    width: 80px; padding: 5px 8px; border-radius: 6px;
    border: 1px solid rgba(99,102,241,.3); background: rgba(15,23,42,.7);
    color: #f1f5f9; font-size: 13px; text-align: right;
  }
  .p-input:focus { outline: none; border-color: #3b82f6; }
  select.p-input { width: 80px; text-align: left; cursor: pointer; }

  /* indicator table */
  .ind-table { width: 100%; border-collapse: collapse; }
  .ind-table thead th {
    font-size: 11px; font-weight: 600; color: #64748b;
    text-transform: uppercase; letter-spacing: .06em;
    padding: 0 8px 8px; text-align: left;
  }
  .ind-table thead th:not(:first-child) { text-align: center; }
  .ind-table thead th:first-child { width: 36%; }
  .ind-table tbody tr { border-top: 1px solid rgba(51,65,85,.35); }
  .ind-table tbody td { padding: 8px; font-size: 13px; color: #cbd5e1; vertical-align: middle; }
  .ind-table tbody td:not(:first-child) { text-align: center; }
  .ind-name { font-weight: 500; }
  .ind-hint { font-size: 11px; color: #475569; }

  .ind-input {
    width: 64px; padding: 5px 8px; border-radius: 6px;
    border: 1px solid rgba(99,102,241,.3); background: rgba(15,23,42,.7);
    color: #f1f5f9; font-size: 13px; text-align: center;
  }
  .ind-input:focus { outline: none; border-color: #3b82f6; }
  select.ind-input { cursor: pointer; }

  /* signal threshold table */
  .sig-table { width: 100%; border-collapse: collapse; }
  .sig-table thead th {
    font-size: 11px; font-weight: 600; color: #64748b;
    text-transform: uppercase; letter-spacing: .06em;
    padding: 0 8px 10px; text-align: center;
  }
  .sig-table thead th:first-child { text-align: left; }
  .sig-table tbody tr { border-top: 1px solid rgba(51,65,85,.35); }
  .sig-table tbody td { padding: 8px; font-size: 13px; color: #cbd5e1; vertical-align: middle; text-align: center; }
  .sig-table tbody td:first-child { text-align: left; }

  /* badges */
  .badge {
    display: inline-block; padding: 3px 9px; border-radius: 5px;
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
  }
  .badge-buy  { background: rgba(16,185,129,.15); color: #10b981; }
  .badge-sell { background: rgba(239,68,68,.15);  color: #ef4444; }
  .badge-hold { background: rgba(251,191,36,.12); color: #fbbf24; }
  .badge-neutral { background: rgba(100,116,139,.2); color: #94a3b8; }

  /* info bars */
  .info-bar {
    margin-top: 14px; padding: 10px 14px;
    background: rgba(59,130,246,.08); border: 1px solid rgba(59,130,246,.2);
    border-radius: 8px; font-size: 12px; color: #94a3b8;
  }
  .info-bar.warn { background: rgba(239,68,68,.08); border-color: rgba(239,68,68,.25); color: #ef4444; }

  /* remove number spinners */
  input[type=number]::-webkit-inner-spin-button,
  input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
  input[type=number] { -moz-appearance: textfield; appearance: textfield; }

  /* tooltip */
  [data-tip] { position: relative; cursor: help; }
  [data-tip]::after {
    content: attr(data-tip); position: absolute;
    bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%);
    background: #1e293b; border: 1px solid rgba(99,102,241,.4); border-radius: 6px;
    padding: 7px 11px; font-size: 12px; color: #cbd5e1;
    white-space: pre-wrap; max-width: 260px;
    pointer-events: none; opacity: 0; transition: opacity .15s; z-index: 10; text-align: left;
  }
  [data-tip]:hover::after { opacity: 1; }

  /* placeholder */
  .cfg-placeholder { text-align: center; padding: 48px; font-size: 14px; color: #475569; }
`;

// ── Shared options ────────────────────────────────────────────────────────────
const TF_OPTS = ['1m','5m','15m','1h','1d'];
const LB_OPTS = ['1d','2d','3d','7d','30d','180d'];

// ── Reusable row component ────────────────────────────────────────────────────
function ParamRow({ name, desc, tip, children }: {
  name: string; desc?: string; tip?: string; children: React.ReactNode;
}) {
  return (
    <div className="p-row">
      <div className="p-name" data-tip={tip}>{name}</div>
      <div className="p-desc">{desc}</div>
      <div className="p-ctrl">{children}</div>
    </div>
  );
}

function NumInput({ value, onChange, min, max, step, width = '80px' }: {
  value: number; onChange: (v: number) => void;
  min?: number; max?: number; step?: number; width?: string;
}) {
  return (
    <input
      className="p-input" type="number"
      min={min} max={max} step={step} value={value}
      style={{ width }}
      onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
    />
  );
}

function TfSelect({ value, onChange, opts = TF_OPTS }: {
  value: string; onChange: (v: string) => void; opts?: string[];
}) {
  return (
    <select className="p-input" value={value} onChange={(e) => onChange(e.target.value)}>
      {opts.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

// ── Sum validator banner ──────────────────────────────────────────────────────
function SumBar({ total, label = 'Összesen' }: { total: number; label?: string }) {
  const ok = total === 100;
  return (
    <div className={`info-bar${ok ? '' : ' warn'}`}>
      {ok ? 'ℹ️' : '⚠️'} {label}: <strong>{total}%</strong>
      {!ok && ' — 100%-ra kell összegezni!'}
    </div>
  );
}

// ── Indicator table row helper ────────────────────────────────────────────────
function IndRow({ icon, name, hint, period, onPeriod, periodMin = 1, periodMax = 300,
  tf, onTf, lb, onLb, extraPeriods }: any) {
  return (
    <tr>
      <td><div className="ind-name">{icon} {name}</div><div className="ind-hint">{hint}</div></td>
      <td>
        {extraPeriods ? extraPeriods : (
          <input className="ind-input" type="number" min={periodMin} max={periodMax}
            value={period} onChange={(e) => onPeriod(parseInt(e.target.value) || period)} />
        )}
      </td>
      <td>
        <select className="ind-input" value={tf} onChange={(e) => onTf(e.target.value)}>
          {TF_OPTS.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      </td>
      <td>
        <select className="ind-input" value={lb} onChange={(e) => onLb(e.target.value)}>
          {LB_OPTS.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      </td>
    </tr>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// TAB COMPONENTS
// ════════════════════════════════════════════════════════════════════════════

function NewsSourcesTab() {
  return (
    <div className="cfg-section">
      <div className="cfg-section-title">📰 News Source Configuration</div>
      <div className="cfg-section-desc">Configure news sources, credibility weights, and update frequency</div>
      <div className="cfg-placeholder">News source management coming in Phase 2</div>
    </div>
  );
}

function SentimentTab({ weights, setWeights, advConf: ac, setAdvConf: setAc }: any) {
  const items = [
    { key: 'fresh_0_2h',      label: '0–2 óra (Fresh)',     desc: 'Legfrissebb hírek – maximális relevancia', min: 50, max: 100,
      tip: 'A legfrissebb hírek – azonnal hatnak a jelzésre.' },
    { key: 'strong_2_6h',     label: '2–6 óra (Strong)',    desc: 'Erős intraday momentum', min: 20, max: 100,
      tip: 'Még élő intraday momentum – jelentős hatással bír.' },
    { key: 'intraday_6_12h',  label: '6–12 óra (Intraday)', desc: 'Csökkent relevanciájú intraday hír', min: 10, max: 80,
      tip: 'Nap közepi hírek – csökkent de még releváns.' },
    { key: 'overnight_12_24h',label: '12–24 óra (Overnight)',desc: 'Előző nap hírei – másnap nyitásra hatás', min: 0, max: 50,
      tip: 'Előző esti / éjszakai hírek – másnap nyitásra még számíthat.' },
  ];
  return (
    <div>
      <div className="cfg-section">
        <div className="cfg-section-title">💭 Sentiment Decay Weights</div>
        <div className="cfg-section-desc">Meghatározza, hogy az egyes korú hírek milyen súllyal számítanak a sentiment score-ba.</div>
        {items.map(it => (
          <ParamRow key={it.key} name={it.label} desc={it.desc} tip={it.tip}>
            <NumInput value={weights[it.key]} min={it.min} max={it.max}
              onChange={(v) => setWeights({ ...weights, [it.key]: v })} />
            <span className="p-unit">%</span>
          </ParamRow>
        ))}
        <div className="info-bar">ℹ️ A decay súlyok csökkentik a régi hírek hatását. 0% = teljesen figyelmen kívül hagyja.</div>
      </div>

      {/* Sentiment Confidence */}
      <div className="cfg-section">
        <div className="cfg-section-title">🎯 Sentiment Confidence Paraméterei</div>
        <div className="cfg-section-desc">Hány hír kell a teljes konfidenciához, és hogyan osztályozza a pozitív/negatív híreket.</div>
        <div className="cfg-sub">Hírszám → volume_factor tiers</div>
        <ParamRow name="Teljes confidence (1.0)" desc="Ennyi hír esetén volume_factor = 1.0" tip="Alapesetben 10 hír. Kevesebb hírnél kisebb faktor.">
          <NumInput value={ac.sentimentConfFullNewsCount} min={3} max={30} onChange={(v) => setAc({...ac, sentimentConfFullNewsCount: v})} />
          <span className="p-unit">db</span>
        </ParamRow>
        <ParamRow name="Magas confidence (0.85)" desc="Ennyi hír esetén volume_factor = 0.85" tip="Alapesetben 5 hír.">
          <NumInput value={ac.sentimentConfHighNewsCount} min={2} max={20} onChange={(v) => setAc({...ac, sentimentConfHighNewsCount: v})} />
          <span className="p-unit">db</span>
        </ParamRow>
        <ParamRow name="Közepes confidence (0.70)" desc="Ennyi hír esetén volume_factor = 0.70" tip="Alapesetben 3 hír.">
          <NumInput value={ac.sentimentConfMedNewsCount} min={1} max={10} onChange={(v) => setAc({...ac, sentimentConfMedNewsCount: v})} />
          <span className="p-unit">db</span>
        </ParamRow>
        <ParamRow name="Alacsony confidence (0.55)" desc="Ennyi hír esetén volume_factor = 0.55 (1 hír = 0.40)" tip="Alapesetben 2 hír.">
          <NumInput value={ac.sentimentConfLowNewsCount} min={1} max={5} onChange={(v) => setAc({...ac, sentimentConfLowNewsCount: v})} />
          <span className="p-unit">db</span>
        </ParamRow>
        <div className="cfg-sub">Pozitív/Negatív hír osztályozás</div>
        <ParamRow name="Pozitív küszöb" desc="FinBERT score ≥ ennyi → pozitív hírnek számít" tip="Alapesetben 0.20. A consistency számításhoz használt belső osztályozás.">
          <NumInput value={ac.sentimentPositiveThreshold} min={0.05} max={0.5} step={0.05} onChange={(v) => setAc({...ac, sentimentPositiveThreshold: v})} />
        </ParamRow>
        <ParamRow name="Negatív küszöb" desc="FinBERT score ≤ ennyi → negatív hírnek számít" tip="Alapesetben -0.20.">
          <NumInput value={ac.sentimentNegativeThreshold} min={-0.5} max={-0.05} step={0.05} onChange={(v) => setAc({...ac, sentimentNegativeThreshold: v})} />
        </ParamRow>
      </div>
    </div>
  );
}

function TechnicalTab({ weights, setWeights, indicatorParams: ip, setIndicatorParams: setIp,
  techComponentWeights: tcw, setTechComponentWeights: setTcw, advSignal: as, setAdvSignal: setAs,
  advConf: ac, setAdvConf: setAc }: any) {

  const tcwTotal = tcw.smaWeight + tcw.rsiWeight + tcw.macdWeight + tcw.bollingerWeight +
                   tcw.stochasticWeight + tcw.volumeWeight + tcw.cciWeight + tcw.adxWeight;

  const compWeights = [
    { key: 'smaWeight',        label: 'SMA Trend',      tip: 'SMA20 / SMA50 trend + Golden/Death Cross jelzések.' },
    { key: 'rsiWeight',        label: 'RSI',            tip: 'RSI – relative strength index. Túlvett/túladott és bullish zónák.' },
    { key: 'macdWeight',       label: 'MACD',           tip: 'MACD histogram és jelvonal keresztezések.' },
    { key: 'bollingerWeight',  label: 'Bollinger Bands',tip: 'Bollinger Band szűkülés és sávtörések.' },
    { key: 'stochasticWeight', label: 'Stochastic',     tip: 'Stochastic oscillator – rövid távú momentum.' },
    { key: 'volumeWeight',     label: 'Volume (OBV)',   tip: 'Volume OBV – megerősíti-e a volumen a trendet.' },
    { key: 'cciWeight',        label: 'CCI',            tip: 'Commodity Channel Index – 0% = letiltva.' },
    { key: 'adxWeight',        label: 'ADX',            tip: 'ADX – trend erősség. 0% = letiltva.' },
  ];

  const smaScores = [
    { key: 'sma20Bullish',  label: 'Price > SMA20 (Bullish)', desc: 'Ár az SMA20 felett – rövid trend bullish' },
    { key: 'sma20Bearish',  label: 'Price < SMA20 (Bearish)', desc: 'Ár az SMA20 alatt – rövid trend bearish' },
    { key: 'sma50Bullish',  label: 'Price > SMA50 (Bullish)', desc: 'Ár az SMA50 felett – közép trend bullish' },
    { key: 'sma50Bearish',  label: 'Price < SMA50 (Bearish)', desc: 'Ár az SMA50 alatt – közép trend bearish' },
    { key: 'goldenCross',   label: 'Golden Cross', desc: 'SMA20 > SMA50 keresztezés (bullish)',
      tip: 'SMA20 átmegy az SMA50 fölé – erős bullish jel.' },
    { key: 'deathCross',    label: 'Death Cross',  desc: 'SMA20 < SMA50 keresztezés (bearish)',
      tip: 'SMA20 az SMA50 alá süllyed – erős bearish jel.' },
  ];

  const rsiScores = [
    { key: 'rsiNeutral',     label: 'RSI Neutral (45–55)',      desc: 'Semleges zóna – kis hatás' },
    { key: 'rsiBullish',     label: 'RSI Bullish (55–70)',      desc: 'Erős bullish momentum' },
    { key: 'rsiWeakBullish', label: 'RSI Weak Bullish (30–45)', desc: 'Gyenge / helyreállási bullish' },
    { key: 'rsiOverbought',  label: 'RSI Overbought (≥70)',     desc: 'Túlvett – bearish korrekció (levonás)',
      tip: '≥70: bearish korrekció várható – vonja le a pontot.' },
    { key: 'rsiOversold',    label: 'RSI Oversold (≤30)',       desc: 'Túladott – bullish visszafordulás (hozzáadás)',
      tip: '≤30: bullish visszafordulás esélye nő.' },
  ];

  return (
    <div>
      {/* ── Indicator component weights ── */}
      <div className="cfg-section">
        <div className="cfg-section-title">⚖️ Indikátor-súlyok (összesített technical score)</div>
        <div className="cfg-section-desc">Az egyes indikátorok súlya a végső technical score-ban. Összegük: 100%.</div>
        {compWeights.map(cw => (
          <ParamRow key={cw.key} name={cw.label} desc="" tip={cw.tip}>
            <NumInput value={tcw[cw.key]} min={0} max={100}
              onChange={(v) => setTcw({ ...tcw, [cw.key]: v })} />
            <span className="p-unit">%</span>
          </ParamRow>
        ))}
        <SumBar total={tcwTotal} />
        <div className="info-bar" style={{ marginTop: '8px' }}>
          💡 Set to 0% to disable any indicator. Oversold signals only apply in bullish trends (Golden Cross).
        </div>
      </div>

      {/* ── SMA Signal Scores ── */}
      <div className="cfg-section">
        <div className="cfg-section-title">📊 SMA Szignál Pontértékek</div>
        <div className="cfg-section-desc">Az egyes SMA kondíciók mennyi pontot adnak / vonnak le a technical score-ból.</div>
        <div className="cfg-sub">Trend jelzések</div>
        {smaScores.slice(0, 4).map(s => (
          <ParamRow key={s.key} name={s.label} desc={s.desc} tip={s.tip}>
            <NumInput value={weights[s.key]} min={0} max={100}
              onChange={(v) => setWeights({ ...weights, [s.key]: v })} />
            <span className="p-unit">pont</span>
          </ParamRow>
        ))}
        <div className="cfg-sub">Keresztezések</div>
        {smaScores.slice(4).map(s => (
          <ParamRow key={s.key} name={s.label} desc={s.desc} tip={s.tip}>
            <NumInput value={weights[s.key]} min={0} max={100}
              onChange={(v) => setWeights({ ...weights, [s.key]: v })} />
            <span className="p-unit">pont</span>
          </ParamRow>
        ))}
        <div className="cfg-sub">RSI Zónák</div>
        {rsiScores.map(s => (
          <ParamRow key={s.key} name={s.label} desc={s.desc} tip={s.tip}>
            <NumInput value={weights[s.key]} min={0} max={100}
              onChange={(v) => setWeights({ ...weights, [s.key]: v })} />
            <span className="p-unit">pont</span>
          </ParamRow>
        ))}
        <div className="info-bar" style={{ marginTop: '14px' }}>
          ℹ️ RSI Overbought subtracts from score (bearish), RSI Oversold adds to score (bullish reversal).
        </div>
      </div>

      {/* ── Indicator Periods & Timeframes ── */}
      <div className="cfg-section">
        <div className="cfg-section-title">⚙️ Indikátor Periódusok &amp; Timeframe-ek</div>
        <div className="cfg-section-desc">Minden indikátor számítási periódusa, adatnézete és visszatekintési ablaka.</div>
        <table className="ind-table">
          <thead>
            <tr>
              <th>Indikátor</th>
              <th>Periódus</th>
              <th>Timeframe</th>
              <th>Lookback</th>
            </tr>
          </thead>
          <tbody>
            <IndRow icon="⚡" name="RSI" hint="Relative Strength Index"
              period={ip.rsiPeriod} onPeriod={(v: number) => setIp({...ip, rsiPeriod: v})} periodMin={5} periodMax={50}
              tf={ip.rsiTimeframe} onTf={(v: string) => setIp({...ip, rsiTimeframe: v})}
              lb={ip.rsiLookback} onLb={(v: string) => setIp({...ip, rsiLookback: v})} />
            <IndRow icon="📈" name="SMA Short" hint="Rövid mozgóátlag"
              period={ip.smaShortPeriod} onPeriod={(v: number) => setIp({...ip, smaShortPeriod: v})} periodMin={5} periodMax={100}
              tf={ip.smaShortTimeframe} onTf={(v: string) => setIp({...ip, smaShortTimeframe: v})}
              lb={ip.smaShortLookback} onLb={(v: string) => setIp({...ip, smaShortLookback: v})} />
            <IndRow icon="📈" name="SMA Medium" hint="Közepes mozgóátlag"
              period={ip.smaMediumPeriod} onPeriod={(v: number) => setIp({...ip, smaMediumPeriod: v})} periodMin={20} periodMax={200}
              tf={ip.smaMediumTimeframe} onTf={(v: string) => setIp({...ip, smaMediumTimeframe: v})}
              lb={ip.smaMediumLookback} onLb={(v: string) => setIp({...ip, smaMediumLookback: v})} />
            <IndRow icon="📈" name="SMA Long" hint="Hosszú mozgóátlag"
              period={ip.smaLongPeriod} onPeriod={(v: number) => setIp({...ip, smaLongPeriod: v})} periodMin={100} periodMax={300}
              tf={ip.smaLongTimeframe} onTf={(v: string) => setIp({...ip, smaLongTimeframe: v})}
              lb={ip.smaLongLookback} onLb={(v: string) => setIp({...ip, smaLongLookback: v})} />
            <IndRow icon="📉" name="MACD" hint="Fast / Slow / Signal"
              tf={ip.macdTimeframe} onTf={(v: string) => setIp({...ip, macdTimeframe: v})}
              lb={ip.macdLookback} onLb={(v: string) => setIp({...ip, macdLookback: v})}
              extraPeriods={
                <div style={{ display: 'flex', gap: '4px' }}>
                  <input className="ind-input" type="number" value={ip.macdFast} style={{ width: '42px' }} title="Fast"
                    onChange={(e) => setIp({...ip, macdFast: parseInt(e.target.value) || 12})} />
                  <input className="ind-input" type="number" value={ip.macdSlow} style={{ width: '42px' }} title="Slow"
                    onChange={(e) => setIp({...ip, macdSlow: parseInt(e.target.value) || 26})} />
                  <input className="ind-input" type="number" value={ip.macdSignal} style={{ width: '38px' }} title="Signal"
                    onChange={(e) => setIp({...ip, macdSignal: parseInt(e.target.value) || 9})} />
                </div>
              } />
            <IndRow icon="📊" name="Bollinger Bands" hint="Period + Std Dev"
              tf={ip.bbTimeframe} onTf={(v: string) => setIp({...ip, bbTimeframe: v})}
              lb={ip.bbLookback} onLb={(v: string) => setIp({...ip, bbLookback: v})}
              extraPeriods={
                <div style={{ display: 'flex', gap: '4px' }}>
                  <input className="ind-input" type="number" value={ip.bbPeriod} style={{ width: '52px' }} title="Period"
                    onChange={(e) => setIp({...ip, bbPeriod: parseInt(e.target.value) || 20})} />
                  <input className="ind-input" type="number" value={ip.bbStdDev} style={{ width: '42px' }} step={0.5} title="StdDev"
                    onChange={(e) => setIp({...ip, bbStdDev: parseFloat(e.target.value) || 2.0})} />
                </div>
              } />
            <IndRow icon="🌡️" name="ATR" hint="Average True Range"
              period={ip.atrPeriod} onPeriod={(v: number) => setIp({...ip, atrPeriod: v})} periodMin={5} periodMax={50}
              tf={ip.atrTimeframe} onTf={(v: string) => setIp({...ip, atrTimeframe: v})}
              lb={ip.atrLookback} onLb={(v: string) => setIp({...ip, atrLookback: v})} />
            <IndRow icon="🎯" name="Stochastic" hint="Momentum oszcillátor"
              period={ip.stochPeriod} onPeriod={(v: number) => setIp({...ip, stochPeriod: v})} periodMin={5} periodMax={50}
              tf={ip.stochTimeframe} onTf={(v: string) => setIp({...ip, stochTimeframe: v})}
              lb={ip.stochLookback} onLb={(v: string) => setIp({...ip, stochLookback: v})} />
            <IndRow icon="💪" name="ADX" hint="Trend erősség"
              period={ip.adxPeriod} onPeriod={(v: number) => setIp({...ip, adxPeriod: v})} periodMin={5} periodMax={50}
              tf={ip.adxTimeframe} onTf={(v: string) => setIp({...ip, adxTimeframe: v})}
              lb={ip.adxLookback} onLb={(v: string) => setIp({...ip, adxLookback: v})} />
          </tbody>
        </table>
      </div>

      {/* RSI / Stochastic Zone Boundaries */}
      <div className="cfg-section">
        <div className="cfg-section-title">📊 RSI &amp; Stochastic Zónahatárok</div>
        <div className="cfg-section-desc">Mikor számít az RSI/Stochastic oversold/overbought/neutral zónában.</div>
        <div className="cfg-sub">RSI Zónák</div>
        <ParamRow name="Overbought küszöb" desc="RSI ≥ ennyi → overbought (bearish)" tip="Alapesetben 70. Magasabb = szűkebb overbought zóna.">
          <NumInput value={as.rsiOverbought} min={60} max={90} onChange={(v) => setAs({...as, rsiOverbought: v})} />
        </ParamRow>
        <ParamRow name="Oversold küszöb" desc="RSI ≤ ennyi → oversold (bullish)" tip="Alapesetben 30. Alacsonyabb = szűkebb oversold zóna.">
          <NumInput value={as.rsiOversold} min={10} max={40} onChange={(v) => setAs({...as, rsiOversold: v})} />
        </ParamRow>
        <ParamRow name="Neutral zóna – alsó" desc="RSI neutral zóna alja (45–55 között)" tip="RSI e fölött és a Neutral High alatt → neutral zóna.">
          <NumInput value={as.rsiNeutralLow} min={30} max={55} onChange={(v) => setAs({...as, rsiNeutralLow: v})} />
        </ParamRow>
        <ParamRow name="Neutral zóna – felső" desc="RSI neutral zóna teteje" tip="RSI e felett → bullish zóna (ha < overbought).">
          <NumInput value={as.rsiNeutralHigh} min={45} max={70} onChange={(v) => setAs({...as, rsiNeutralHigh: v})} />
        </ParamRow>
        <div className="cfg-sub">Stochastic Zónák</div>
        <ParamRow name="Stoch Overbought" desc="Stoch %K ≥ ennyi → overbought" tip="Alapesetben 80.">
          <NumInput value={as.stochOverbought} min={60} max={95} onChange={(v) => setAs({...as, stochOverbought: v})} />
        </ParamRow>
        <ParamRow name="Stoch Oversold" desc="Stoch %K ≤ ennyi → oversold (bullish trend esetén)" tip="Alapesetben 20.">
          <NumInput value={as.stochOversold} min={5} max={40} onChange={(v) => setAs({...as, stochOversold: v})} />
        </ParamRow>
      </div>

      {/* Technical Confidence */}
      <div className="cfg-section">
        <div className="cfg-section-title">🎯 Technical Confidence Paraméterei</div>
        <div className="cfg-section-desc">Hogyan számítja a rendszer a technical score konfidenciáját az indikátor-egyezésből.</div>
        <div className="cfg-sub">RSI irányjelzés confidence-hoz</div>
        <ParamRow name="RSI Bullish küszöb" desc="RSI ≥ ennyi → bullish iránynak számít a confidence számításhoz" tip="Alapesetben 55.">
          <NumInput value={ac.techConfRsiBullish} min={50} max={70} onChange={(v) => setAc({...ac, techConfRsiBullish: v})} />
        </ParamRow>
        <ParamRow name="RSI Bearish küszöb" desc="RSI ≤ ennyi → bearish iránynak számít" tip="Alapesetben 45.">
          <NumInput value={ac.techConfRsiBearish} min={30} max={50} onChange={(v) => setAc({...ac, techConfRsiBearish: v})} />
        </ParamRow>
        <div className="cfg-sub">ADX boost</div>
        <ParamRow name="ADX Strong küszöb" desc="ADX ≥ ennyi → erős trend boost" tip="Alapesetben 25.">
          <NumInput value={ac.techConfAdxStrong} min={15} max={40} onChange={(v) => setAc({...ac, techConfAdxStrong: v})} />
        </ParamRow>
        <ParamRow name="ADX Moderate küszöb" desc="ADX ≥ ennyi → moderate trend boost" tip="Alapesetben 20.">
          <NumInput value={ac.techConfAdxModerate} min={10} max={30} onChange={(v) => setAc({...ac, techConfAdxModerate: v})} />
        </ParamRow>
        <ParamRow name="Strong ADX boost" desc="Confidence boost erős ADX esetén" tip="Alapesetben +0.15.">
          <NumInput value={ac.techConfAdxStrongBoost} min={0} max={0.3} step={0.05} onChange={(v) => setAc({...ac, techConfAdxStrongBoost: v})} />
        </ParamRow>
        <ParamRow name="Moderate ADX boost" desc="Confidence boost mérsékelt ADX esetén" tip="Alapesetben +0.10.">
          <NumInput value={ac.techConfAdxModerateBoost} min={0} max={0.2} step={0.05} onChange={(v) => setAc({...ac, techConfAdxModerateBoost: v})} />
        </ParamRow>
        <div className="cfg-sub">Alap confidence számítás</div>
        <ParamRow name="Alap confidence" desc="Minimális confidence indikátor-egyezés nélkül (0%)" tip="Alapesetben 0.50 = 50%.">
          <NumInput value={ac.techConfBase} min={0.3} max={0.7} step={0.05} onChange={(v) => setAc({...ac, techConfBase: v})} />
        </ParamRow>
        <ParamRow name="Alignment súly" desc="Mennyit adhat hozzá az indikátor-egyezés a confidence-hez" tip="Alapesetben 0.30: 50%+30%=max 80% alapból.">
          <NumInput value={ac.techConfAlignmentWeight} min={0.1} max={0.5} step={0.05} onChange={(v) => setAc({...ac, techConfAlignmentWeight: v})} />
        </ParamRow>
        <ParamRow name="Max confidence cap" desc="Technical confidence maximuma (ADX boosttal együtt)" tip="Alapesetben 0.90 = 90%.">
          <NumInput value={ac.techConfMax} min={0.7} max={1.0} step={0.05} onChange={(v) => setAc({...ac, techConfMax: v})} />
        </ParamRow>
      </div>
    </div>
  );
}

function SignalsTab({ componentWeights: cw, setComponentWeights: setCw, thresholds: th, setThresholds: setTh,
  advSignal: as, setAdvSignal: setAs }: any) {
  const cwTotal = cw.sentiment + cw.technical + cw.risk;
  const conf = (v: number) => Math.round(v * 100);
  const pct  = (v: number) => v / 100;

  return (
    <div>
      {/* component weights */}
      <div className="cfg-section">
        <div className="cfg-section-title">⚖️ Összetevők súlya (global signal)</div>
        <div className="cfg-section-desc">Sentiment, Technical és Risk rész aránya a végső jelzés score-ban. Összeg: 100%.</div>
        <ParamRow name="💭 Sentiment" desc="Hír-hangulat – fő trigger (FinBERT)"
          tip="FinBERT alapú hír-sentiment súlya. Fő vezérlő jel.">
          <NumInput value={cw.sentiment} min={0} max={100}
            onChange={(v) => setCw({...cw, sentiment: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="📈 Technical" desc="Technikai indikátorok – megerősítő jel"
          tip="Technikai indikátorok megerősítő súlya.">
          <NumInput value={cw.technical} min={0} max={100}
            onChange={(v) => setCw({...cw, technical: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="🛡️ Risk" desc="Kockázat / R:R minőség – stop-loss közelség"
          tip="Kockázati komponens – stop/take-profit távolság minőség.">
          <NumInput value={cw.risk} min={0} max={100}
            onChange={(v) => setCw({...cw, risk: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <SumBar total={cwTotal} />
      </div>

      {/* signal thresholds */}
      <div className="cfg-section">
        <div className="cfg-section-title">🎯 Signal Küszöbértékek</div>
        <div className="cfg-section-desc">Mekkora score és confidence szükséges az egyes jelzésekhez.</div>
        <table className="sig-table">
          <thead>
            <tr>
              <th>Jelzés típusa</th>
              <th>Min. Score</th>
              <th>Min. Confidence</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><span className="badge badge-hold">HOLD zóna (±)</span></td>
              <td>
                <input className="ind-input" type="number" value={th.holdZoneThreshold} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, holdZoneThreshold: parseInt(e.target.value) || 0})} />
                {' '}<span style={{ fontSize: '11px', color: '#64748b' }}>±</span>
              </td>
              <td style={{ color: '#475569' }}>–</td>
            </tr>
            <tr>
              <td><span className="badge badge-buy">STRONG BUY</span></td>
              <td>
                <input className="ind-input" type="number" value={th.strongBuyScore} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, strongBuyScore: parseInt(e.target.value) || 0})} />
              </td>
              <td>
                <input className="ind-input" type="number" value={conf(th.strongBuyConfidence)} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, strongBuyConfidence: pct(parseInt(e.target.value) || 0)})} />
                {' '}<span className="p-unit">%</span>
              </td>
            </tr>
            <tr>
              <td><span className="badge badge-buy" style={{ opacity: .7 }}>MODERATE BUY</span></td>
              <td>
                <input className="ind-input" type="number" value={th.moderateBuyScore} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, moderateBuyScore: parseInt(e.target.value) || 0})} />
              </td>
              <td>
                <input className="ind-input" type="number" value={conf(th.moderateBuyConfidence)} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, moderateBuyConfidence: pct(parseInt(e.target.value) || 0)})} />
                {' '}<span className="p-unit">%</span>
              </td>
            </tr>
            <tr>
              <td><span className="badge badge-sell">STRONG SELL</span></td>
              <td>
                <input className="ind-input" type="number" value={th.strongSellScore} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, strongSellScore: parseInt(e.target.value) || 0})} />
              </td>
              <td>
                <input className="ind-input" type="number" value={conf(th.strongSellConfidence)} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, strongSellConfidence: pct(parseInt(e.target.value) || 0)})} />
                {' '}<span className="p-unit">%</span>
              </td>
            </tr>
            <tr>
              <td><span className="badge badge-sell" style={{ opacity: .7 }}>MODERATE SELL</span></td>
              <td>
                <input className="ind-input" type="number" value={th.moderateSellScore} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, moderateSellScore: parseInt(e.target.value) || 0})} />
              </td>
              <td>
                <input className="ind-input" type="number" value={conf(th.moderateSellConfidence)} style={{ width: '70px' }}
                  onChange={(e) => setTh({...th, moderateSellConfidence: pct(parseInt(e.target.value) || 0)})} />
                {' '}<span className="p-unit">%</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div className="info-bar">
          ℹ️ HOLD ha −{th.holdZoneThreshold} &lt; score &lt; +{th.holdZoneThreshold} · MODERATE BUY ha ≥{th.moderateBuyScore} &amp; conf ≥{conf(th.moderateBuyConfidence)}% · STRONG BUY ha ≥{th.strongBuyScore} &amp; conf ≥{conf(th.strongBuyConfidence)}%
        </div>
      </div>

      {/* Alignment Bonus */}
      <div className="cfg-section">
        <div className="cfg-section-title">🔗 Alignment Bonus</div>
        <div className="cfg-section-desc">Mikor kapnak bónuszt az összetevők az egymást erősítő jelzések után.</div>
        <div className="cfg-sub">Erősség küszöbök (|score| &gt; X = "erős")</div>
        <ParamRow name="Tech erősség küszöb" desc="|technical_score| feletti érték szükséges TR/ST pár bónuszhoz" tip="Alapesetben 60. Ha a tech score abszolútértéke meghaladja ezt, 'erős'-nek számít.">
          <NumInput value={as.alignmentTechThreshold} min={20} max={80} onChange={(v) => setAs({...as, alignmentTechThreshold: v})} />
        </ParamRow>
        <ParamRow name="Sent erősség küszöb" desc="|sentiment_score| feletti érték a pár bónuszhoz" tip="Alapesetben 40.">
          <NumInput value={as.alignmentSentThreshold} min={20} max={80} onChange={(v) => setAs({...as, alignmentSentThreshold: v})} />
        </ParamRow>
        <ParamRow name="Risk erősség küszöb" desc="|risk_score| feletti érték a pár bónuszhoz" tip="Alapesetben 40.">
          <NumInput value={as.alignmentRiskThreshold} min={20} max={80} onChange={(v) => setAs({...as, alignmentRiskThreshold: v})} />
        </ParamRow>
        <div className="cfg-sub">Bónusz pontok</div>
        <ParamRow name="Mind 3 pár erős" desc="Bónusz ha Sent+Tech+Risk mind erős" tip="Maximum bónusz – mind a 3 komponens erősen egyezik.">
          <NumInput value={as.alignmentBonusAll} min={0} max={20} onChange={(v) => setAs({...as, alignmentBonusAll: v})} />
          <span className="p-unit">pont</span>
        </ParamRow>
        <ParamRow name="Tech+Risk pár" desc="Bónusz csak TR párnak (legjobb swing setup)" tip="Alapesetben 5 pont.">
          <NumInput value={as.alignmentBonusTr} min={0} max={15} onChange={(v) => setAs({...as, alignmentBonusTr: v})} />
          <span className="p-unit">pont</span>
        </ParamRow>
        <ParamRow name="Sent+Tech pár" desc="Bónusz ST párnak (erős megerősítés)" tip="Alapesetben 5 pont.">
          <NumInput value={as.alignmentBonusSt} min={0} max={15} onChange={(v) => setAs({...as, alignmentBonusSt: v})} />
          <span className="p-unit">pont</span>
        </ParamRow>
        <ParamRow name="Sent+Risk pár" desc="Bónusz SR párnak (gyengébb, nincs chart)" tip="Alapesetben 3 pont.">
          <NumInput value={as.alignmentBonusSr} min={0} max={15} onChange={(v) => setAs({...as, alignmentBonusSr: v})} />
          <span className="p-unit">pont</span>
        </ParamRow>
      </div>

      {/* Setup Quality */}
      <div className="cfg-section">
        <div className="cfg-section-title">✅ Setup Minőség Kritériumok</div>
        <div className="cfg-section-desc">Mikor számít egy swing trade setup "jónak" vagy "rossznak".</div>
        <div className="cfg-sub">Jó setup feltételei (mindhárom teljesül)</div>
        <ParamRow name="SL min. távolság" desc="Stop-loss legalább ennyire legyen az ártól" tip="Alapesetben 2%. Ha a stop túl közel van, könnyű kiütni.">
          <NumInput value={as.setupStopMinPct} min={0.5} max={5.0} step={0.5} onChange={(v) => setAs({...as, setupStopMinPct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="SL max. távolság" desc="Stop-loss legfeljebb ennyire legyen az ártól (jó setup)" tip="Alapesetben 6%. Ha a stop túl messze van, rossz R:R.">
          <NumInput value={as.setupStopMaxPct} min={2.0} max={15.0} step={0.5} onChange={(v) => setAs({...as, setupStopMaxPct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="TP min. távolság" desc="Take-profit legalább ennyire legyen az ártól" tip="Alapesetben 3%. Ha a target túl közel van, nem éri meg a trade.">
          <NumInput value={as.setupTargetMinPct} min={1.0} max={10.0} step={0.5} onChange={(v) => setAs({...as, setupTargetMinPct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <div className="cfg-sub">Rossz setup határok (bármelyik teljesül → poor)</div>
        <ParamRow name="SL hard max." desc="SL ennél távolabb → poor setup (support valószínűleg törött)" tip="Alapesetben 8%.">
          <NumInput value={as.setupStopHardMaxPct} min={5.0} max={20.0} step={0.5} onChange={(v) => setAs({...as, setupStopHardMaxPct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="TP hard min." desc="TP ennél közelebb → poor setup (target túl szűk)" tip="Alapesetben 2%.">
          <NumInput value={as.setupTargetHardMinPct} min={0.5} max={5.0} step={0.5} onChange={(v) => setAs({...as, setupTargetHardMinPct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
      </div>
    </div>
  );
}

function RiskTab({ params: rp, setParams: setRp, advSignal: as, setAdvSignal: setAs,
  advRisk: ar, setAdvRisk: setAr }: any) {
  const rwTotal = rp.volatilityWeight + rp.proximityWeight + rp.trendStrengthWeight;
  const rr = (rp.takeProfitAtrMult / rp.stopLossAtrMult).toFixed(2);

  return (
    <div>
      {/* Risk component weights */}
      <div className="cfg-section">
        <div className="cfg-section-title">⚖️ Risk Összetevők Súlya</div>
        <div className="cfg-section-desc">Volatilitás, S/R közelség és trend erőssége hogyan aránylik a risk score-ban. Összeg: 100%.</div>
        <ParamRow name="🌡️ Volatilitás (ATR)" desc="Átlagos ármozgás nagysága – magasabb = kockázatosabb"
          tip="ATR-alapú volatilitásmérés. Magas ATR = magasabb kockázat.">
          <NumInput value={rp.volatilityWeight} min={0} max={100}
            onChange={(v) => setRp({...rp, volatilityWeight: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="📍 S/R Közelség" desc="Közel van-e az ár support/resistance szinthez"
          tip="Mennyire közel van az ár egy S/R szinthez.">
          <NumInput value={rp.proximityWeight} min={0} max={100}
            onChange={(v) => setRp({...rp, proximityWeight: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="💪 Trend Erőssége (ADX)" desc="Mennyire erős az aktuális trend (ADX alapján)"
          tip="ADX érték alapján – erős trend = jobb jelzési minőség.">
          <NumInput value={rp.trendStrengthWeight} min={0} max={100}
            onChange={(v) => setRp({...rp, trendStrengthWeight: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <SumBar total={rwTotal} />
      </div>

      {/* SL/TP multipliers */}
      <div className="cfg-section">
        <div className="cfg-section-title">🎯 Stop-Loss / Take-Profit Multiplierek</div>
        <div className="cfg-section-desc">ATR-alapú multiplierek a stop-loss és take-profit szintek kiszámításához.</div>
        <ParamRow name="S/R Buffer (×ATR)" desc="Puffer a support szint alatt (stop buffer)"
          tip="A support szint alá ez az ATR-szorozó mértékével teszi le a stopot.">
          <NumInput value={rp.stopLossSrBuffer} min={0.1} max={2.0} step={0.1}
            onChange={(v) => setRp({...rp, stopLossSrBuffer: v})} />
          <span className="p-unit">× ATR</span>
        </ParamRow>
        <ParamRow name="Stop-Loss (×ATR)" desc="Fallback stop ha S/R messze van"
          tip="Ha nincs közeli S/R, ez a szorzó határozza meg a stop-loss távolságát.">
          <NumInput value={rp.stopLossAtrMult} min={0.5} max={5.0} step={0.5}
            onChange={(v) => setRp({...rp, stopLossAtrMult: v})} />
          <span className="p-unit">× ATR</span>
        </ParamRow>
        <ParamRow name="Take-Profit (×ATR)" desc="Fallback TP ha resistance messze van"
          tip="Ha nincs közeli resistance, ez a szorzó határozza meg a take-profit célt.">
          <NumInput value={rp.takeProfitAtrMult} min={1.0} max={10.0} step={0.5}
            onChange={(v) => setRp({...rp, takeProfitAtrMult: v})} />
          <span className="p-unit">× ATR</span>
        </ParamRow>
        <div className={`info-bar${parseFloat(rr) < 1.5 ? ' warn' : ''}`}>
          ℹ️ Risk:Reward arány: 1:<strong>{rr}</strong>
          {parseFloat(rr) < 1.5 && <span style={{ marginLeft: '10px' }}>⚠️ 1:1.5 alatt kockázatos!</span>}
        </div>
      </div>

      {/* S/R Distance Thresholds */}
      <div className="cfg-section">
        <div className="cfg-section-title">📏 S/R Távolság Korlátok</div>
        <div className="cfg-section-desc">Ha a support/resistance ennél messzebb van az ártól, ATR-alapú fallback lép érvénybe.</div>
        <ParamRow name="Support Max. Távolság" desc="Stop-loss: max ennyi %-ra lehet a support az ártól"
          tip="Ha a support ennél messzebb van az ártól (%), a rendszer ATR fallbacket használ stop-losshoz.">
          <NumInput value={rp.srSupportMaxDistPct} min={1} max={20} step={0.5}
            onChange={(v) => setRp({...rp, srSupportMaxDistPct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="Resistance Max. Távolság" desc="Take-profit: max ennyi %-ra lehet a resistance az ártól"
          tip="Ha a resistance ennél messzebb van az ártól (%), a rendszer ATR fallbacket használ take-profithoz.">
          <NumInput value={rp.srResistanceMaxDistPct} min={1} max={20} step={0.5}
            onChange={(v) => setRp({...rp, srResistanceMaxDistPct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
      </div>

      {/* DBSCAN */}
      <div className="cfg-section">
        <div className="cfg-section-title">🔍 S/R Detektálás (DBSCAN)</div>
        <div className="cfg-section-desc">Support/resistance szintek automatikus klaszterezési paraméterei.</div>
        <ParamRow name="Clustering EPS" desc="Pivoton belüli közelségi küszöb (nagyobb = kevesebb, szélesebb zóna)"
          tip="Ennyi %-on belüli pivot pontok kerülnek ugyanabba a klaszterbe. Nagyobb = kevesebb, szélesebb zóna.">
          <NumInput value={rp.srDbscanEps} min={1} max={10} step={0.5}
            onChange={(v) => setRp({...rp, srDbscanEps: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="Min. Klaszterméret" desc="Minimális pivotsűrűség egy érvényes szinthez (magasabb = erősebb)"
          tip="Ennyi pivot pont kell egy érvényes S/R szinthez. Magasabb = erősebb, teszteltebb szint.">
          <NumInput value={rp.srDbscanMinSamples} min={2} max={10}
            onChange={(v) => setRp({...rp, srDbscanMinSamples: v})} />
          <span className="p-unit">db</span>
        </ParamRow>
        <ParamRow name="Pivot Order" desc="Pivot megerősítő bárok mindkét oldalán (magasabb = ritkább, erősebb)"
          tip="Ennyi bar kell mindkét oldalon a pivot megerősítéséhez. Magasabb = simább, kevesebb hamis pivot.">
          <NumInput value={rp.srDbscanOrder} min={3} max={14}
            onChange={(v) => setRp({...rp, srDbscanOrder: v})} />
          <span className="p-unit">bár</span>
        </ParamRow>
        <ParamRow name="Lookback Ablak" desc="Visszatekintési időszak (hosszabb = fontosabb hosszú távú szintek)"
          tip="Ennyi napra visszamenőleg keresi a pivotos szinteket. Hosszabb = több hosszú távú szint.">
          <NumInput value={rp.srDbscanLookback} min={30} max={365} step={30}
            onChange={(v) => setRp({...rp, srDbscanLookback: v})} />
          <span className="p-unit">nap</span>
        </ParamRow>
      </div>

      {/* S/R Level Filtering */}
      <div className="cfg-section">
        <div className="cfg-section-title">📍 S/R Szint Szűrés</div>
        <div className="cfg-section-desc">Az ár közelében lévő S/R szintek szűrése és visszaadott szintek száma.</div>
        <ParamRow name="Min. távolság az ártól" desc="Ennél közelebb lévő S/R szinteket elveti a rendszer" tip="Ha az S/R túl közel van az árhoz, SL/TP elhelyezésre nem alkalmas.">
          <NumInput value={as.srMinDistancePct} min={0.1} max={5.0} step={0.1} onChange={(v) => setAs({...as, srMinDistancePct: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="Top N szint" desc="Hány legjobb S/R szintet adjon vissza a detektor" tip="Alapesetben 5. Több szint = pontosabb SL/TP, de lassabb számítás.">
          <NumInput value={as.srTopNLevels} min={1} max={20} onChange={(v) => setAs({...as, srTopNLevels: v})} />
          <span className="p-unit">db</span>
        </ParamRow>
      </div>

      {/* ATR Volatility Scaling */}
      <div className="cfg-section">
        <div className="cfg-section-title">🌡️ ATR Volatilitás Skála</div>
        <div className="cfg-section-desc">Az ATR% értékek alapján kategorizálja a volatilitást a risk score-hoz.</div>
        <ParamRow name="Very Low határ" desc="ATR% alatt → very low volatility (risk: +0.8)" tip="Alapesetben 1.5%.">
          <NumInput value={ar.atrVolVeryLow} min={0.5} max={3.0} step={0.5} onChange={(v) => setAr({...ar, atrVolVeryLow: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="Low határ" desc="ATR% alatt → low volatility (risk: +0.4)" tip="Alapesetben 2.5%.">
          <NumInput value={ar.atrVolLow} min={1.0} max={4.0} step={0.5} onChange={(v) => setAr({...ar, atrVolLow: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="Moderate határ" desc="ATR% alatt → moderate volatility (risk: 0)" tip="Alapesetben 3.5%.">
          <NumInput value={ar.atrVolModerate} min={2.0} max={6.0} step={0.5} onChange={(v) => setAr({...ar, atrVolModerate: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
        <ParamRow name="High határ" desc="ATR% felett → very high volatility (risk: -0.4 → -0.8)" tip="Alapesetben 5.0%.">
          <NumInput value={ar.atrVolHigh} min={3.0} max={10.0} step={0.5} onChange={(v) => setAr({...ar, atrVolHigh: v})} />
          <span className="p-unit">%</span>
        </ParamRow>
      </div>

      {/* ADX Trend Strength Scaling */}
      <div className="cfg-section">
        <div className="cfg-section-title">💪 ADX Trend Erőség Skála</div>
        <div className="cfg-section-desc">Az ADX értékek alapján kategorizálja a trend erőségét (risk score komponens).</div>
        <ParamRow name="Very Strong határ" desc="ADX ≥ ennyi → very strong trend (risk: +0.8)" tip="Alapesetben 40.">
          <NumInput value={ar.adxVeryStrong} min={30} max={60} onChange={(v) => setAr({...ar, adxVeryStrong: v})} />
        </ParamRow>
        <ParamRow name="Strong határ" desc="ADX ≥ ennyi → strong trend (risk: +0.5–0.8)" tip="Alapesetben 30.">
          <NumInput value={ar.adxStrong} min={20} max={50} onChange={(v) => setAr({...ar, adxStrong: v})} />
        </ParamRow>
        <ParamRow name="Moderate határ" desc="ADX ≥ ennyi → moderate trend (risk: +0.3–0.5)" tip="Alapesetben 25.">
          <NumInput value={ar.adxModerate} min={15} max={40} onChange={(v) => setAr({...ar, adxModerate: v})} />
        </ParamRow>
        <ParamRow name="Weak határ" desc="ADX ≥ ennyi → weak trend (risk: 0–0.3)" tip="Alapesetben 20.">
          <NumInput value={ar.adxWeak} min={10} max={35} onChange={(v) => setAr({...ar, adxWeak: v})} />
        </ParamRow>
        <ParamRow name="Very Weak határ" desc="ADX ≤ ennyi → very weak trend (risk: -0.3 → -0.8)" tip="Alapesetben 15.">
          <NumInput value={ar.adxVeryWeak} min={5} max={25} onChange={(v) => setAr({...ar, adxVeryWeak: v})} />
        </ParamRow>
        <div className="info-bar">ℹ️ A szintek között lineáris interpoláció történik a folyamatos skálázáshoz.</div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ════════════════════════════════════════════════════════════════════════════
export function Configuration() {
  const [activeTab, setActiveTab] = useState(0);
  const [saving, setSaving] = useState(false);

  const [sentimentWeights, setSentimentWeights] = useState({
    fresh_0_2h: 100, strong_2_6h: 85, intraday_6_12h: 60, overnight_12_24h: 35,
  });

  const [componentWeights, setComponentWeights] = useState({
    sentiment: 70, technical: 20, risk: 10,
  });

  const [thresholds, setThresholds] = useState({
    holdZoneThreshold: 15,
    strongBuyScore: 65,    strongBuyConfidence: 0.75,
    moderateBuyScore: 50,  moderateBuyConfidence: 0.65,
    strongSellScore: -65,  strongSellConfidence: 0.75,
    moderateSellScore: -50,moderateSellConfidence: 0.65,
  });

  const [technicalWeights, setTechnicalWeights] = useState({
    sma20Bullish: 25, sma20Bearish: 15, sma50Bullish: 20, sma50Bearish: 10,
    goldenCross: 15, deathCross: 15,
    rsiNeutral: 20, rsiBullish: 30, rsiWeakBullish: 10, rsiOverbought: 20, rsiOversold: 15,
  });

  const [techComponentWeights, setTechComponentWeights] = useState({
    smaWeight: 30, rsiWeight: 25, macdWeight: 20, bollingerWeight: 15,
    stochasticWeight: 5, volumeWeight: 5, cciWeight: 0, adxWeight: 0,
  });

  const [indicatorParams, setIndicatorParams] = useState({
    rsiPeriod: 14, rsiTimeframe: '5m', rsiLookback: '2d',
    smaShortPeriod: 20, smaShortTimeframe: '5m', smaShortLookback: '2d',
    smaMediumPeriod: 50, smaMediumTimeframe: '1h', smaMediumLookback: '30d',
    smaLongPeriod: 200, smaLongTimeframe: '1d', smaLongLookback: '180d',
    macdFast: 12, macdSlow: 26, macdSignal: 9, macdTimeframe: '15m', macdLookback: '3d',
    bbPeriod: 20, bbStdDev: 2.0, bbTimeframe: '1h', bbLookback: '7d',
    atrPeriod: 14, atrTimeframe: '1d', atrLookback: '180d',
    stochPeriod: 14, stochTimeframe: '15m', stochLookback: '3d',
    adxPeriod: 14, adxTimeframe: '1h', adxLookback: '30d',
  });

  const [riskParams, setRiskParams] = useState({
    volatilityWeight: 40, proximityWeight: 35, trendStrengthWeight: 25,
    stopLossSrBuffer: 0.5, stopLossAtrMult: 2.0, takeProfitAtrMult: 3.0,
    srSupportMaxDistPct: 5.0, srResistanceMaxDistPct: 8.0,
    srDbscanEps: 4.0, srDbscanMinSamples: 3, srDbscanOrder: 7, srDbscanLookback: 180,
  });

  const [advSignal, setAdvSignal] = useState({
    rsiOverbought: 70, rsiOversold: 30, rsiNeutralLow: 45, rsiNeutralHigh: 55,
    stochOverbought: 80, stochOversold: 20,
    srMinDistancePct: 0.5, srTopNLevels: 5,
    alignmentTechThreshold: 60, alignmentSentThreshold: 40, alignmentRiskThreshold: 40,
    alignmentBonusAll: 8, alignmentBonusTr: 5, alignmentBonusSt: 5, alignmentBonusSr: 3,
    setupStopMinPct: 2.0, setupStopMaxPct: 6.0, setupTargetMinPct: 3.0,
    setupStopHardMaxPct: 8.0, setupTargetHardMinPct: 2.0,
  });

  const [advRisk, setAdvRisk] = useState({
    atrVolVeryLow: 1.5, atrVolLow: 2.5, atrVolModerate: 3.5, atrVolHigh: 5.0,
    adxVeryStrong: 40, adxStrong: 30, adxModerate: 25, adxWeak: 20, adxVeryWeak: 15,
  });

  const [advConf, setAdvConf] = useState({
    techConfRsiBullish: 55, techConfRsiBearish: 45,
    techConfAdxStrong: 25, techConfAdxModerate: 20,
    techConfAdxStrongBoost: 0.15, techConfAdxModerateBoost: 0.10,
    techConfBase: 0.50, techConfAlignmentWeight: 0.30, techConfMax: 0.90,
    sentimentConfFullNewsCount: 10, sentimentConfHighNewsCount: 5,
    sentimentConfMedNewsCount: 3, sentimentConfLowNewsCount: 2,
    sentimentPositiveThreshold: 0.2, sentimentNegativeThreshold: -0.2,
  });

  // ── Load from backend ─────────────────────────────────────────────────────
  useEffect(() => { loadConfigFromBackend(); }, []);

  const loadConfigFromBackend = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/config/signal');
      if (response.ok) {
        const config = await response.json();
        setComponentWeights({
          sentiment: Math.round(config.sentiment_weight * 100),
          technical: Math.round(config.technical_weight * 100),
          risk: Math.round(config.risk_weight * 100),
        });
        setThresholds({
          holdZoneThreshold: config.hold_zone_threshold || 15,
          strongBuyScore: config.strong_buy_score,
          strongBuyConfidence: config.strong_buy_confidence,
          moderateBuyScore: config.moderate_buy_score,
          moderateBuyConfidence: config.moderate_buy_confidence,
          strongSellScore: config.strong_sell_score,
          strongSellConfidence: config.strong_sell_confidence,
          moderateSellScore: config.moderate_sell_score,
          moderateSellConfidence: config.moderate_sell_confidence,
        });
      }

      const decayResponse = await fetch('http://localhost:8000/api/v1/config/decay');
      if (decayResponse.ok) {
        const dc = await decayResponse.json();
        setSentimentWeights({
          fresh_0_2h: dc.fresh_0_2h, strong_2_6h: dc.strong_2_6h,
          intraday_6_12h: dc.intraday_6_12h, overnight_12_24h: dc.overnight_12_24h,
        });
      }

      const techResponse = await fetch('http://localhost:8000/api/v1/config/technical-weights');
      if (techResponse.ok) {
        const tc = await techResponse.json();
        setTechnicalWeights({
          sma20Bullish: tc.tech_sma20_bullish, sma20Bearish: tc.tech_sma20_bearish,
          sma50Bullish: tc.tech_sma50_bullish, sma50Bearish: tc.tech_sma50_bearish,
          goldenCross: tc.tech_golden_cross, deathCross: tc.tech_death_cross,
          rsiNeutral: tc.tech_rsi_neutral, rsiBullish: tc.tech_rsi_bullish,
          rsiWeakBullish: tc.tech_rsi_weak_bullish, rsiOverbought: tc.tech_rsi_overbought,
          rsiOversold: tc.tech_rsi_oversold,
        });

        const indResponse = await fetch('http://localhost:8000/api/v1/config/indicator-parameters');
        if (indResponse.ok) {
          const ic = await indResponse.json();
          setIndicatorParams({
            rsiPeriod: ic.rsi_period, rsiTimeframe: ic.rsi_timeframe, rsiLookback: ic.rsi_lookback,
            smaShortPeriod: ic.sma_short_period, smaShortTimeframe: ic.sma_short_timeframe, smaShortLookback: ic.sma_short_lookback,
            smaMediumPeriod: ic.sma_medium_period, smaMediumTimeframe: ic.sma_medium_timeframe, smaMediumLookback: ic.sma_medium_lookback,
            smaLongPeriod: ic.sma_long_period, smaLongTimeframe: ic.sma_long_timeframe, smaLongLookback: ic.sma_long_lookback,
            macdFast: ic.macd_fast, macdSlow: ic.macd_slow, macdSignal: ic.macd_signal, macdTimeframe: ic.macd_timeframe, macdLookback: ic.macd_lookback,
            bbPeriod: ic.bb_period, bbStdDev: ic.bb_std_dev, bbTimeframe: ic.bb_timeframe, bbLookback: ic.bb_lookback,
            atrPeriod: ic.atr_period, atrTimeframe: ic.atr_timeframe, atrLookback: ic.atr_lookback,
            stochPeriod: ic.stoch_period, stochTimeframe: ic.stoch_timeframe, stochLookback: ic.stoch_lookback,
            adxPeriod: ic.adx_period, adxTimeframe: ic.adx_timeframe, adxLookback: ic.adx_lookback,
          });

          const tcwResponse = await fetch('http://localhost:8000/api/v1/config/technical-component-weights');
          if (tcwResponse.ok) {
            const tcw = await tcwResponse.json();
            setTechComponentWeights({
              smaWeight: Math.round(tcw.tech_sma_weight * 100),
              rsiWeight: Math.round(tcw.tech_rsi_weight * 100),
              macdWeight: Math.round(tcw.tech_macd_weight * 100),
              bollingerWeight: Math.round(tcw.tech_bollinger_weight * 100),
              stochasticWeight: Math.round(tcw.tech_stochastic_weight * 100),
              volumeWeight: Math.round(tcw.tech_volume_weight * 100),
              cciWeight: Math.round(tcw.tech_cci_weight * 100),
              adxWeight: Math.round(tcw.tech_adx_weight * 100),
            });
          }

          const riskResponse = await fetch('http://localhost:8000/api/v1/config/risk-parameters');
          if (riskResponse.ok) {
            const rc = await riskResponse.json();
            setRiskParams({
              volatilityWeight: Math.round(rc.risk_volatility_weight * 100),
              proximityWeight: Math.round(rc.risk_proximity_weight * 100),
              trendStrengthWeight: Math.round(rc.risk_trend_strength_weight * 100),
              stopLossSrBuffer: rc.stop_loss_sr_buffer,
              stopLossAtrMult: rc.stop_loss_atr_mult,
              takeProfitAtrMult: rc.take_profit_atr_mult,
              srSupportMaxDistPct: rc.sr_support_max_distance_pct,
              srResistanceMaxDistPct: rc.sr_resistance_max_distance_pct,
              srDbscanEps: rc.sr_dbscan_eps,
              srDbscanMinSamples: rc.sr_dbscan_min_samples,
              srDbscanOrder: rc.sr_dbscan_order,
              srDbscanLookback: rc.sr_dbscan_lookback,
            });
          }
        }
      }
      const advSigResponse = await fetch('http://localhost:8000/api/v1/config/advanced-signal');
      if (advSigResponse.ok) {
        const as = await advSigResponse.json();
        setAdvSignal({
          rsiOverbought: as.rsi_overbought, rsiOversold: as.rsi_oversold,
          rsiNeutralLow: as.rsi_neutral_low, rsiNeutralHigh: as.rsi_neutral_high,
          stochOverbought: as.stoch_overbought, stochOversold: as.stoch_oversold,
          srMinDistancePct: as.sr_min_distance_pct, srTopNLevels: as.sr_top_n_levels,
          alignmentTechThreshold: as.alignment_tech_threshold,
          alignmentSentThreshold: as.alignment_sent_threshold,
          alignmentRiskThreshold: as.alignment_risk_threshold,
          alignmentBonusAll: as.alignment_bonus_all, alignmentBonusTr: as.alignment_bonus_tr,
          alignmentBonusSt: as.alignment_bonus_st, alignmentBonusSr: as.alignment_bonus_sr,
          setupStopMinPct: as.setup_stop_min_pct, setupStopMaxPct: as.setup_stop_max_pct,
          setupTargetMinPct: as.setup_target_min_pct,
          setupStopHardMaxPct: as.setup_stop_hard_max_pct,
          setupTargetHardMinPct: as.setup_target_hard_min_pct,
        });
      }

      const advRiskResponse = await fetch('http://localhost:8000/api/v1/config/advanced-risk-scoring');
      if (advRiskResponse.ok) {
        const ar = await advRiskResponse.json();
        setAdvRisk({
          atrVolVeryLow: ar.atr_vol_very_low, atrVolLow: ar.atr_vol_low,
          atrVolModerate: ar.atr_vol_moderate, atrVolHigh: ar.atr_vol_high,
          adxVeryStrong: ar.adx_very_strong, adxStrong: ar.adx_strong,
          adxModerate: ar.adx_moderate, adxWeak: ar.adx_weak, adxVeryWeak: ar.adx_very_weak,
        });
      }

      const advConfResponse = await fetch('http://localhost:8000/api/v1/config/advanced-confidence');
      if (advConfResponse.ok) {
        const ac = await advConfResponse.json();
        setAdvConf({
          techConfRsiBullish: ac.tech_conf_rsi_bullish, techConfRsiBearish: ac.tech_conf_rsi_bearish,
          techConfAdxStrong: ac.tech_conf_adx_strong, techConfAdxModerate: ac.tech_conf_adx_moderate,
          techConfAdxStrongBoost: ac.tech_conf_adx_strong_boost,
          techConfAdxModerateBoost: ac.tech_conf_adx_moderate_boost,
          techConfBase: ac.tech_conf_base, techConfAlignmentWeight: ac.tech_conf_alignment_weight,
          techConfMax: ac.tech_conf_max,
          sentimentConfFullNewsCount: ac.sentiment_conf_full_news_count,
          sentimentConfHighNewsCount: ac.sentiment_conf_high_news_count,
          sentimentConfMedNewsCount: ac.sentiment_conf_med_news_count,
          sentimentConfLowNewsCount: ac.sentiment_conf_low_news_count,
          sentimentPositiveThreshold: ac.sentiment_positive_threshold,
          sentimentNegativeThreshold: ac.sentiment_negative_threshold,
        });
      }
    } catch (error) {
      console.error('⚠️ Error loading config:', error);
    }
  };

  // ── Save ──────────────────────────────────────────────────────────────────
  const handleSaveAll = async () => {
    setSaving(true);
    try {
      const total = componentWeights.sentiment + componentWeights.technical + componentWeights.risk;
      if (total !== 100) {
        alert(`⚠️ Weights must sum to 100%, currently: ${total}%`);
        setSaving(false);
        return;
      }

      const signalPayload = {
        sentiment_weight: componentWeights.sentiment / 100,
        technical_weight: componentWeights.technical / 100,
        risk_weight: componentWeights.risk / 100,
        hold_zone_threshold: thresholds.holdZoneThreshold,
        strong_buy_score: thresholds.strongBuyScore,
        strong_buy_confidence: thresholds.strongBuyConfidence,
        moderate_buy_score: thresholds.moderateBuyScore,
        moderate_buy_confidence: thresholds.moderateBuyConfidence,
        strong_sell_score: thresholds.strongSellScore,
        strong_sell_confidence: thresholds.strongSellConfidence,
        moderate_sell_score: thresholds.moderateSellScore,
        moderate_sell_confidence: thresholds.moderateSellConfidence,
      };

      const response = await fetch('http://localhost:8000/api/v1/config/signal', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signalPayload),
      });

      if (!response.ok) {
        const error = await response.json();
        alert(`❌ Error saving configuration:\n${error.detail || 'Unknown error'}`);
        setSaving(false);
        return;
      }

      await fetch('http://localhost:8000/api/v1/config/decay', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fresh_0_2h: sentimentWeights.fresh_0_2h,
          strong_2_6h: sentimentWeights.strong_2_6h,
          intraday_6_12h: sentimentWeights.intraday_6_12h,
          overnight_12_24h: sentimentWeights.overnight_12_24h,
        }),
      });

      await fetch('http://localhost:8000/api/v1/config/technical-weights', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tech_sma20_bullish: technicalWeights.sma20Bullish,
          tech_sma20_bearish: technicalWeights.sma20Bearish,
          tech_sma50_bullish: technicalWeights.sma50Bullish,
          tech_sma50_bearish: technicalWeights.sma50Bearish,
          tech_golden_cross: technicalWeights.goldenCross,
          tech_death_cross: technicalWeights.deathCross,
          tech_rsi_neutral: technicalWeights.rsiNeutral,
          tech_rsi_bullish: technicalWeights.rsiBullish,
          tech_rsi_weak_bullish: technicalWeights.rsiWeakBullish,
          tech_rsi_overbought: technicalWeights.rsiOverbought,
          tech_rsi_oversold: technicalWeights.rsiOversold,
        }),
      });

      const ip = indicatorParams;
      await fetch('http://localhost:8000/api/v1/config/indicator-parameters', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rsi_period: ip.rsiPeriod, rsi_timeframe: ip.rsiTimeframe, rsi_lookback: ip.rsiLookback,
          sma_short_period: ip.smaShortPeriod, sma_short_timeframe: ip.smaShortTimeframe, sma_short_lookback: ip.smaShortLookback,
          sma_medium_period: ip.smaMediumPeriod, sma_medium_timeframe: ip.smaMediumTimeframe, sma_medium_lookback: ip.smaMediumLookback,
          sma_long_period: ip.smaLongPeriod, sma_long_timeframe: ip.smaLongTimeframe, sma_long_lookback: ip.smaLongLookback,
          macd_fast: ip.macdFast, macd_slow: ip.macdSlow, macd_signal: ip.macdSignal, macd_timeframe: ip.macdTimeframe, macd_lookback: ip.macdLookback,
          bb_period: ip.bbPeriod, bb_std_dev: ip.bbStdDev, bb_timeframe: ip.bbTimeframe, bb_lookback: ip.bbLookback,
          atr_period: ip.atrPeriod, atr_timeframe: ip.atrTimeframe, atr_lookback: ip.atrLookback,
          stoch_period: ip.stochPeriod, stoch_timeframe: ip.stochTimeframe, stoch_lookback: ip.stochLookback,
          adx_period: ip.adxPeriod, adx_timeframe: ip.adxTimeframe, adx_lookback: ip.adxLookback,
        }),
      });

      const tcw = techComponentWeights;
      const tcwTotal = tcw.smaWeight + tcw.rsiWeight + tcw.macdWeight + tcw.bollingerWeight +
                       tcw.stochasticWeight + tcw.volumeWeight + tcw.cciWeight + tcw.adxWeight;
      if (tcwTotal !== 100) {
        alert(`⚠️ Technical component weights must sum to 100%, currently: ${tcwTotal}%`);
        setSaving(false);
        return;
      }
      await fetch('http://localhost:8000/api/v1/config/technical-component-weights', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tech_sma_weight: tcw.smaWeight / 100,
          tech_rsi_weight: tcw.rsiWeight / 100,
          tech_macd_weight: tcw.macdWeight / 100,
          tech_bollinger_weight: tcw.bollingerWeight / 100,
          tech_stochastic_weight: tcw.stochasticWeight / 100,
          tech_volume_weight: tcw.volumeWeight / 100,
          tech_cci_weight: tcw.cciWeight / 100,
          tech_adx_weight: tcw.adxWeight / 100,
        }),
      });

      const rp = riskParams;
      const rwTotal = rp.volatilityWeight + rp.proximityWeight + rp.trendStrengthWeight;
      if (rwTotal !== 100) {
        alert(`⚠️ Risk component weights must sum to 100%, currently: ${rwTotal}%`);
        setSaving(false);
        return;
      }
      await fetch('http://localhost:8000/api/v1/config/risk-parameters', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          risk_volatility_weight: rp.volatilityWeight / 100,
          risk_proximity_weight: rp.proximityWeight / 100,
          risk_trend_strength_weight: rp.trendStrengthWeight / 100,
          stop_loss_sr_buffer: rp.stopLossSrBuffer,
          stop_loss_atr_mult: rp.stopLossAtrMult,
          take_profit_atr_mult: rp.takeProfitAtrMult,
          sr_support_max_distance_pct: rp.srSupportMaxDistPct,
          sr_resistance_max_distance_pct: rp.srResistanceMaxDistPct,
          sr_dbscan_eps: rp.srDbscanEps,
          sr_dbscan_min_samples: rp.srDbscanMinSamples,
          sr_dbscan_order: rp.srDbscanOrder,
          sr_dbscan_lookback: rp.srDbscanLookback,
        }),
      });

      const as = advSignal;
      await fetch('http://localhost:8000/api/v1/config/advanced-signal', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rsi_overbought: as.rsiOverbought, rsi_oversold: as.rsiOversold,
          rsi_neutral_low: as.rsiNeutralLow, rsi_neutral_high: as.rsiNeutralHigh,
          stoch_overbought: as.stochOverbought, stoch_oversold: as.stochOversold,
          sr_min_distance_pct: as.srMinDistancePct, sr_top_n_levels: as.srTopNLevels,
          alignment_tech_threshold: as.alignmentTechThreshold,
          alignment_sent_threshold: as.alignmentSentThreshold,
          alignment_risk_threshold: as.alignmentRiskThreshold,
          alignment_bonus_all: as.alignmentBonusAll, alignment_bonus_tr: as.alignmentBonusTr,
          alignment_bonus_st: as.alignmentBonusSt, alignment_bonus_sr: as.alignmentBonusSr,
          setup_stop_min_pct: as.setupStopMinPct, setup_stop_max_pct: as.setupStopMaxPct,
          setup_target_min_pct: as.setupTargetMinPct,
          setup_stop_hard_max_pct: as.setupStopHardMaxPct,
          setup_target_hard_min_pct: as.setupTargetHardMinPct,
        }),
      });

      const ar = advRisk;
      await fetch('http://localhost:8000/api/v1/config/advanced-risk-scoring', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          atr_vol_very_low: ar.atrVolVeryLow, atr_vol_low: ar.atrVolLow,
          atr_vol_moderate: ar.atrVolModerate, atr_vol_high: ar.atrVolHigh,
          adx_very_strong: ar.adxVeryStrong, adx_strong: ar.adxStrong,
          adx_moderate: ar.adxModerate, adx_weak: ar.adxWeak, adx_very_weak: ar.adxVeryWeak,
        }),
      });

      const ac = advConf;
      await fetch('http://localhost:8000/api/v1/config/advanced-confidence', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tech_conf_rsi_bullish: ac.techConfRsiBullish, tech_conf_rsi_bearish: ac.techConfRsiBearish,
          tech_conf_adx_strong: ac.techConfAdxStrong, tech_conf_adx_moderate: ac.techConfAdxModerate,
          tech_conf_adx_strong_boost: ac.techConfAdxStrongBoost,
          tech_conf_adx_moderate_boost: ac.techConfAdxModerateBoost,
          tech_conf_base: ac.techConfBase, tech_conf_alignment_weight: ac.techConfAlignmentWeight,
          tech_conf_max: ac.techConfMax,
          sentiment_conf_full_news_count: ac.sentimentConfFullNewsCount,
          sentiment_conf_high_news_count: ac.sentimentConfHighNewsCount,
          sentiment_conf_med_news_count: ac.sentimentConfMedNewsCount,
          sentiment_conf_low_news_count: ac.sentimentConfLowNewsCount,
          sentiment_positive_threshold: ac.sentimentPositiveThreshold,
          sentiment_negative_threshold: ac.sentimentNegativeThreshold,
        }),
      });

      alert('✅ Configuration saved successfully!');
      await loadConfigFromBackend();
    } catch (error) {
      console.error('❌ Error saving config:', error);
      alert('❌ Failed to save configuration.\nCheck console for details.');
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: 0, label: '📊 Tickers' },
    { id: 1, label: '📰 News Sources' },
    { id: 2, label: '💭 Sentiment' },
    { id: 3, label: '📈 Technical' },
    { id: 4, label: '🎯 Signals' },
    { id: 5, label: '🛡️ Risk' },
  ];

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)', color: '#e0e7ff' }}>
      <style>{CSS}</style>
      <div className="cfg-container">

        {/* Header */}
        <div className="cfg-header">
          <Link to="/" className="cfg-back">← Dashboard</Link>
          <div className="cfg-title">⚙️ Configuration</div>
          <button className="cfg-save" onClick={handleSaveAll} disabled={saving}>
            💾 {saving ? 'Saving...' : 'Save All Changes'}
          </button>
        </div>

        {/* Tabs */}
        <div className="cfg-tabs">
          {tabs.map(tab => (
            <button key={tab.id} className={`cfg-tab${activeTab === tab.id ? ' active' : ''}`}
              onClick={() => setActiveTab(tab.id)}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {activeTab === 0 && <TickerManagement />}
        {activeTab === 1 && <NewsSourcesTab />}
        {activeTab === 2 && (
          <SentimentTab
            weights={sentimentWeights} setWeights={setSentimentWeights}
            advConf={advConf} setAdvConf={setAdvConf}
          />
        )}
        {activeTab === 3 && (
          <TechnicalTab
            weights={technicalWeights} setWeights={setTechnicalWeights}
            indicatorParams={indicatorParams} setIndicatorParams={setIndicatorParams}
            techComponentWeights={techComponentWeights} setTechComponentWeights={setTechComponentWeights}
            advSignal={advSignal} setAdvSignal={setAdvSignal}
            advConf={advConf} setAdvConf={setAdvConf}
          />
        )}
        {activeTab === 4 && (
          <SignalsTab
            componentWeights={componentWeights} setComponentWeights={setComponentWeights}
            thresholds={thresholds} setThresholds={setThresholds}
            advSignal={advSignal} setAdvSignal={setAdvSignal}
          />
        )}
        {activeTab === 5 && (
          <RiskTab
            params={riskParams} setParams={setRiskParams}
            advSignal={advSignal} setAdvSignal={setAdvSignal}
            advRisk={advRisk} setAdvRisk={setAdvRisk}
          />
        )}
      </div>
    </div>
  );
}
