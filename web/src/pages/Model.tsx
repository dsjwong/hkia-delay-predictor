import { useState } from 'react'
import { Tile } from '@/components/ui/tile'
import { Segmented } from '@/components/ui/segmented'
import { HBar } from '@/charts/HBar'
import { Reliability } from '@/charts/ModelCharts'
import { ChartHead } from '@/charts/theme'
import { useModel } from '@/lib/data'
import type { MetricSet } from '@/lib/types'
import { num, signed } from '@/lib/time'

function f3(x: number | null | undefined) {
  return x == null ? '—' : x.toFixed(3)
}

function MetricTable({ rows }: { rows: { label: string; m: MetricSet | undefined }[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="hk-kicker text-left border-b border-border">
          <th className="py-1 font-normal">predictor</th>
          <th className="py-1 font-normal">AUC ↑</th>
          <th className="py-1 font-normal">Brier ↓</th>
          <th className="py-1 font-normal">log loss ↓</th>
          <th className="py-1 font-normal">MAE min ↓</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.label} className="border-b border-border/50">
            <td className="py-0.5">{r.label}</td>
            <td className="py-0.5 hk-num">{f3(r.m?.auc)}</td>
            <td className="py-0.5 hk-num">{f3(r.m?.brier)}</td>
            <td className="py-0.5 hk-num">{f3(r.m?.logloss)}</td>
            <td className="py-0.5 hk-num">{r.m?.mae == null ? '—' : r.m.mae.toFixed(1)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Minimal markdown -> blocks for the hand-written interpretation (headings, bullets, bold, code). */
function Md({ text }: { text: string }) {
  const inline = (s: string) =>
    s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) =>
      part.startsWith('**') ? (
        <b key={i}>{part.slice(2, -2)}</b>
      ) : part.startsWith('`') ? (
        <code key={i} className="font-mono text-[0.8em] bg-surface-3 px-1 rounded">
          {part.slice(1, -1)}
        </code>
      ) : (
        <span key={i}>{part}</span>
      ),
    )
  return (
    <div className="space-y-1.5 text-sm text-ink-2">
      {text
        .split('\n')
        .filter((l) => l.trim())
        .map((l, i) =>
          l.startsWith('## ') ? (
            <h4 key={i} className="text-ink font-semibold mt-1">
              {l.slice(3)}
            </h4>
          ) : l.startsWith('- ') ? (
            <div key={i} className="pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-muted">
              {inline(l.slice(2))}
            </div>
          ) : (
            <p key={i}>{inline(l)}</p>
          ),
        )}
    </div>
  )
}

export default function Model() {
  const { data: md, error, loading } = useModel()
  const [which, setWhich] = useState<'clf' | 'reg'>('clf')
  const [showAll, setShowAll] = useState(false)
  const [showInterp, setShowInterp] = useState(false)
  if (error) return <div className="text-sm text-critical">Could not load model.json: {error}</div>
  if (loading || !md) return <div className="text-sm text-muted">Loading…</div>
  const man = md.manifest
  if (!man) return <div className="text-sm text-muted">models/MANIFEST.json not found in the snapshot.</div>
  const sp = man.split
  const x = man.metrics['XGB/test'] ?? {}
  const b = man.metrics['B_airline_hour/test'] ?? {}
  const med = man.metrics['median_train/test'] ?? {}
  const fi = md.feature_importance
  const imp = fi
    ? Object.entries(which === 'clf' ? fi.clf_delayed15 : fi.reg_delay_min)
        .sort((a, c) => c[1] - a[1])
        .map(([k, v]) => ({ label: k, value: v }))
    : []
  const ev = md.live_eval
  const d = (a?: number | null, c?: number | null, digits = 3) => (a == null || c == null ? '' : signed(a - c, digits))

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Model performance</h2>
        <p className="text-xs text-muted">
          XGBoost trained {man.created_at.slice(0, 10)} (git <code className="font-mono">{man.git_sha}</code>, xgboost{' '}
          {man.xgboost}, {man.n_features} features). Date-ordered split, no shuffling: train {sp.train.date_min}→
          {sp.train.date_max} ({num(sp.train.n_rows)}), val {sp.val.date_min}→{sp.val.date_max} ({num(sp.val.n_rows)}),{' '}
          <b className="text-ink-2">
            test {sp.test.date_min}→{sp.test.date_max} ({num(sp.test.n_rows)} departures)
          </b>
          .
        </p>
      </div>

      <h3 className="hk-kicker">Held-out test — XGBoost vs airline × hour baseline</h3>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-2">
        <Tile
          label="AUC"
          value={f3(x.auc)}
          sub={`${d(x.auc, b.auc)} vs baseline ${f3(b.auc)}`}
          hint="Probability the model ranks a random delayed flight above a random on-time one. 0.5 = coin flip."
        />
        <Tile
          label="Brier"
          value={f3(x.brier)}
          sub={`${d(x.brier, b.brier)} vs baseline ${f3(b.brier)}`}
          hint="Mean squared error of the probabilities; lower is better, rewards calibration."
        />
        <Tile
          label="Log loss"
          value={f3(x.logloss)}
          sub={`${d(x.logloss, b.logloss)} vs baseline ${f3(b.logloss)}`}
          hint="Penalises confident wrong probabilities; lower is better."
        />
        <Tile
          label="MAE (min)"
          value={x.mae == null ? '—' : x.mae.toFixed(1)}
          sub={`${d(x.mae, b.mae, 1)} vs baseline ${b.mae?.toFixed(1)} · median ${med.mae?.toFixed(1)}`}
          hint="Typical error in predicted delay minutes. Delays are heavy-tailed, so beating the median constant is hard."
        />
      </div>
      <p className="text-xs text-muted">
        AUC {f3(x.auc)}: pick a random delayed and a random on-time flight, the model ranks the delayed one higher{' '}
        {Math.round((x.auc ?? 0) * 100)} % of the time (0.5 = coin flip; the airline × hour lookup gets{' '}
        {Math.round((b.auc ?? 0) * 100)} %). Brier / log loss reward calibrated probabilities; MAE is the typical error
        in predicted delay minutes. Delays are heavy-tailed — modest, honest gains, not a crystal ball.
      </p>
      <div className="hk-card p-3">
        <button
          className="text-sm text-accent cursor-pointer"
          onClick={() => setShowAll((v) => !v)}
          aria-expanded={showAll}
        >
          {showAll ? 'Hide' : 'Show'} full metric table — all baselines
        </button>
        {showAll && (
          <div className="mt-2">
            <MetricTable
              rows={[
                { label: 'A: global rate / mean', m: man.metrics['A_global/test'] },
                { label: 'B: airline × hour mean (train only)', m: man.metrics['B_airline_hour/test'] },
                { label: 'train median delay', m: man.metrics['median_train/test'] },
                { label: 'XGBoost', m: man.metrics['XGB/test'] },
              ]}
            />
          </div>
        )}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="hk-card p-3">
          <ChartHead
            title="Reliability diagram"
            sub="observed rate (y) vs mean predicted P(delay > 15) (x); 10 equal-width bins on test, marker size ~ bin count"
          />
          {md.calibration.length ? (
            <Reliability bins={md.calibration} />
          ) : (
            <div className="text-xs text-muted">no calibration table in the snapshot</div>
          )}
        </div>
        <div className="hk-card p-3">
          <ChartHead
            title="Feature importance (XGBoost gain, top 15)"
            right={
              <Segmented
                value={which}
                onChange={setWhich}
                label="Model"
                options={[
                  { value: 'clf', label: 'P(delay > 15) classifier' },
                  { value: 'reg', label: 'delay-minutes regressor' },
                ]}
              />
            }
          />
          {imp.length ? (
            <HBar rows={imp} fmt={(v) => num(v, 1)} unit="gain" height={330} />
          ) : (
            <div className="text-xs text-muted">no feature importance in the snapshot</div>
          )}
        </div>
      </div>

      {man.ablation_test && (
        <div className="hk-card p-3">
          <ChartHead title="Ablation on test — remove a feature group" />
          <table className="w-full text-sm max-w-[640px]">
            <thead>
              <tr className="hk-kicker text-left border-b border-border">
                <th className="py-1 font-normal">variant</th>
                <th className="py-1 font-normal">features</th>
                <th className="py-1 font-normal">AUC</th>
                <th className="py-1 font-normal">log loss</th>
                <th className="py-1 font-normal">Brier</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(man.ablation_test).map(([k, v]) => (
                <tr key={k} className="border-b border-border/50">
                  <td className="py-0.5">{k}</td>
                  <td className="py-0.5 hk-num">{v.n_features}</td>
                  <td className="py-0.5 hk-num">{f3(v.auc)}</td>
                  <td className="py-0.5 hk-num">{f3(v.logloss)}</td>
                  <td className="py-0.5 hk-num">{f3(v.brier)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-muted mt-1">
            Weather is worth ~+0.013 AUC in a test window without a typhoon; the point-in-time rolling delay features do
            not help AUC on test.
          </p>
        </div>
      )}

      <div className="hk-card p-3 space-y-2">
        <ChartHead
          title="Live evaluation — predictions vs what actually happened"
          sub={`rolling ${ev.window_days}-day window; per flight, the last score written before it departed`}
        />
        {ev.status !== 'ok' ? (
          <p className="text-sm text-ink-2">
            Collecting — <b>{ev.n_matured}</b> matured predictions so far (need ≥ {ev.min_n}). A prediction 'matures'
            when its flight departs; the metric is the last score written before departure. The cron started scoring on
            2026-08-17, so a week of numbers appears after a few days.
          </p>
        ) : (
          <>
            <p className="text-xs text-muted">
              Flights departed {ev.date_min} → {ev.date_max}, n = {num(ev.n_matured)}, observed P(delay &gt; 15) ={' '}
              {ev.delayed15_rate?.toFixed(2)}, median lead time between last score and departure{' '}
              {Math.round(ev.median_lead_min ?? 0)} min.
            </p>
            <MetricTable
              rows={[
                { label: 'XGBoost (live)', m: ev.model },
                {
                  label: 'airline × hour baseline',
                  m: ev.baseline_airline_hour && !ev.baseline_airline_hour.error ? ev.baseline_airline_hour : undefined,
                },
                { label: 'observed rate / median', m: ev.naive_rate },
              ]}
            />
          </>
        )}
      </div>

      <div className="hk-card p-3">
        <button
          className="text-sm text-accent cursor-pointer"
          onClick={() => setShowInterp((v) => !v)}
          aria-expanded={showInterp}
        >
          {showInterp ? 'Hide' : 'Show'} interpretation from the M2 report
        </button>
        {showInterp && (
          <div className="mt-2">
            <Md text={md.interpretation_md || '_reports/M2-results.md not found_'} />
          </div>
        )}
      </div>

      <div className="hk-card p-3">
        <h3 className="text-[0.92rem] font-semibold mb-1">Limitations</h3>
        <ul className="list-disc pl-5 space-y-1 text-sm text-ink-2">
          {md.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
