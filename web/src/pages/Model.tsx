import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Tile } from '@/components/ui/tile'
import { Segmented } from '@/components/ui/segmented'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty } from '@/components/ui/empty'
import { SkeletonCard } from '@/components/ui/skeleton'
import { HBar } from '@/charts/HBar'
import { Reliability } from '@/charts/ModelCharts'
import { ReportCard } from '@/components/ReportCard'
import { useModel } from '@/lib/data'
import type { MetricSet } from '@/lib/types'
import { num, signed } from '@/lib/time'

function f3(x: number | null | undefined) {
  return x == null ? '—' : x.toFixed(3)
}

function MetricTable({ rows }: { rows: { label: string; m: MetricSet | undefined }[] }) {
  return (
    <div className="rounded-lg border border-border overflow-auto">
      <table className="hk-table">
        <thead>
          <tr>
            <th>predictor</th>
            <th className="text-right">AUC ↑</th>
            <th className="text-right">Brier ↓</th>
            <th className="text-right">log loss ↓</th>
            <th className="text-right">MAE min ↓</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td>{r.label}</td>
              <td className="hk-num text-right">{f3(r.m?.auc)}</td>
              <td className="hk-num text-right">{f3(r.m?.brier)}</td>
              <td className="hk-num text-right">{f3(r.m?.logloss)}</td>
              <td className="hk-num text-right">{r.m?.mae == null ? '—' : r.m.mae.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Minimal markdown -> blocks for the hand-written interpretation (headings, bullets, bold, code). */
function Md({ text }: { text: string }) {
  const inline = (s: string) =>
    s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) =>
      part.startsWith('**') ? (
        <b key={i} className="text-ink">
          {part.slice(2, -2)}
        </b>
      ) : part.startsWith('`') ? (
        <code key={i} className="font-mono text-[0.8em] bg-elev px-1 rounded">
          {part.slice(1, -1)}
        </code>
      ) : (
        <span key={i}>{part}</span>
      ),
    )
  return (
    <div className="space-y-1.5 text-sm text-ink-2 leading-relaxed">
      {text
        .split('\n')
        .filter((l) => l.trim())
        .map((l, i) =>
          l.startsWith('## ') ? (
            <h4 key={i} className="text-ink font-semibold mt-2 tracking-tight">
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

function Toggle({ open, onClick, children }: { open: boolean; onClick: () => void; children: React.ReactNode }) {
  const Chevron = open ? ChevronDown : ChevronRight
  return (
    <Button variant="ghost" size="sm" onClick={onClick} aria-expanded={open}>
      <Chevron size={14} aria-hidden="true" />
      {children}
    </Button>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <div className="hk-skeleton h-6 w-56" />
        <div className="hk-skeleton h-3.5 w-[520px] max-w-full" />
      </div>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <Tile key={i} label=" " value="" loading />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <SkeletonCard body="h-72" />
        <SkeletonCard body="h-72" />
      </div>
      <SkeletonCard body="h-40" />
    </div>
  )
}

export default function Model() {
  const { data: md, error, loading } = useModel()
  const [which, setWhich] = useState<'clf' | 'reg'>('clf')
  const [showAll, setShowAll] = useState(false)
  const [showInterp, setShowInterp] = useState(false)
  if (error) return <Empty tone="error" className="py-16" title="Could not load model.json" detail={error} />
  if (loading || !md) return <PageSkeleton />
  const man = md.manifest
  if (!man)
    return (
      <Empty
        className="py-16"
        title="models/MANIFEST.json not found in the snapshot."
        detail="Run hkia.train and hkia.export_json to publish a model."
      />
    )
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
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Model performance</h2>
        <p className="text-xs text-muted mt-1 leading-relaxed">
          XGBoost trained {man.created_at.slice(0, 10)} (git <code className="font-mono">{man.git_sha}</code>, xgboost{' '}
          {man.xgboost}, {man.n_features} features). Date-ordered split, no shuffling: train {sp.train.date_min}→
          {sp.train.date_max} ({num(sp.train.n_rows)}), val {sp.val.date_min}→{sp.val.date_max} ({num(sp.val.n_rows)}),{' '}
          <b className="text-ink-2">
            test {sp.test.date_min}→{sp.test.date_max} ({num(sp.test.n_rows)} departures)
          </b>
          .
        </p>
      </div>

      <ReportCard ev={ev} />

      <hr className="border-border" />

      <section className="space-y-3" aria-labelledby="heldout-h">
        <h3 id="heldout-h" className="hk-kicker">
          Held-out test — XGBoost vs airline × hour baseline
        </h3>
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
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
        <p className="text-xs text-muted leading-relaxed">
          AUC {f3(x.auc)}: pick a random delayed and a random on-time flight, the model ranks the delayed one higher{' '}
          {Math.round((x.auc ?? 0) * 100)} % of the time (0.5 = coin flip; the airline × hour lookup gets{' '}
          {Math.round((b.auc ?? 0) * 100)} %). Brier / log loss reward calibrated probabilities; MAE is the typical
          error in predicted delay minutes. Delays are heavy-tailed — modest, honest gains, not a crystal ball.
        </p>
        <Card>
          <div className="px-2 py-1.5">
            <Toggle open={showAll} onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Hide' : 'Show'} full metric table — all baselines
            </Toggle>
          </div>
          {showAll && (
            <div className="px-4 pb-4">
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
        </Card>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Reliability diagram</CardTitle>
              <CardDescription>
                observed rate (y) vs mean predicted P(delay &gt; 15) (x); 10 equal-width bins on test, marker size ~ bin
                count
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {md.calibration.length ? (
              <Reliability bins={md.calibration} />
            ) : (
              <Empty title="no calibration table in the snapshot" />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Feature importance</CardTitle>
              <CardDescription>XGBoost gain, top 15</CardDescription>
            </div>
            <Segmented
              value={which}
              onChange={setWhich}
              label="Model"
              options={[
                { value: 'clf', label: 'P(delay > 15)' },
                { value: 'reg', label: 'delay minutes' },
              ]}
            />
          </CardHeader>
          <CardContent>
            {imp.length ? (
              <HBar rows={imp} fmt={(v) => num(v, 1)} unit="gain" height={330} />
            ) : (
              <Empty title="no feature importance in the snapshot" />
            )}
          </CardContent>
        </Card>
      </div>

      {man.ablation_test && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Ablation on test — remove a feature group</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-border overflow-auto max-w-[720px]">
              <table className="hk-table">
                <thead>
                  <tr>
                    <th>variant</th>
                    <th className="text-right">features</th>
                    <th className="text-right">AUC</th>
                    <th className="text-right">log loss</th>
                    <th className="text-right">Brier</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(man.ablation_test).map(([k, v]) => (
                    <tr key={k}>
                      <td>{k}</td>
                      <td className="hk-num text-right">{v.n_features}</td>
                      <td className="hk-num text-right">{f3(v.auc)}</td>
                      <td className="hk-num text-right">{f3(v.logloss)}</td>
                      <td className="hk-num text-right">{f3(v.brier)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted mt-2">
              Weather is worth ~+0.013 AUC in a test window without a typhoon; the point-in-time rolling delay features
              do not help AUC on test.
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Live evaluation — full metric table</CardTitle>
            <CardDescription>
              the same rolling {ev.window_days}-day window as the report card, with log loss and the naive predictors
              ("always the observed rate" / "always the median delay") for reference
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {ev.status !== 'ok' ? (
            <Empty
              title={
                <>
                  Collecting — <b className="text-ink">{ev.n_matured}</b> matured predictions so far (need ≥ {ev.min_n})
                </>
              }
              detail="A prediction 'matures' when its flight departs; the metric is the last score written before departure. The cron started scoring on 2026-08-17, so a week of numbers appears after a few days."
            />
          ) : (
            <div className="space-y-3">
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
                    m:
                      ev.baseline_airline_hour && !ev.baseline_airline_hour.error
                        ? ev.baseline_airline_hour
                        : undefined,
                  },
                  { label: 'observed rate / median', m: ev.naive_rate },
                ]}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <div className="px-2 py-1.5">
          <Toggle open={showInterp} onClick={() => setShowInterp((v) => !v)}>
            {showInterp ? 'Hide' : 'Show'} interpretation from the M2 report
          </Toggle>
        </div>
        {showInterp && (
          <div className="px-4 pb-4">
            <Md text={md.interpretation_md || '_reports/M2-results.md not found_'} />
          </div>
        )}
      </Card>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Limitations</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 space-y-1.5 text-sm text-ink-2 leading-relaxed">
            {md.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
