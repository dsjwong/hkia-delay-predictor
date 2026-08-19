import { useMetaCtx } from '@/lib/meta-context'
import { Badge } from './ui/badge'
import { Tooltip } from './ui/tooltip'
import { hm } from '@/lib/time'

/** Latest METAR (raw) + HKO warnings / TC signal. */
export function WeatherStrip({ compact = false }: { compact?: boolean }) {
  const { weather } = useMetaCtx()
  const w = weather.data
  if (!w)
    return <div className="text-xs text-muted">{weather.error ? `weather: ${weather.error}` : 'loading weather…'}</div>
  const tc = w.tc_active
  const warns = tc.length ? w.hko_warnings.filter((x) => x.code !== 'WTCSGNL') : w.hko_warnings
  return (
    <div className="space-y-1.5">
      {w.metar && (
        <Tooltip
          content={`VHHH METAR issued ${hm(w.metar.report_time)} HKT · ${w.metar.flt_cat ?? '?'} · wind ${w.metar.wdir ?? 'VRB'}°/${w.metar.wspd_kt ?? '—'} kt${w.metar.wgst_kt ? ' G' + w.metar.wgst_kt : ''} · vis ${w.metar.visib ?? '—'} sm · ${w.metar.temp_c ?? '—'}°C`}
          side="bottom"
          className="w-full"
        >
          <div className={`hk-strip w-full ${compact ? 'text-[0.7rem]' : ''}`} tabIndex={0}>
            {w.metar.raw_ob}
          </div>
        </Tooltip>
      )}
      <div className="flex flex-wrap gap-1">
        {tc.map((t) => (
          <Badge key={t.signal + t.start_ts} variant="crit">
            TC signal {t.signal} {t.tc_name ?? ''}
          </Badge>
        ))}
        {warns.map((x) => (
          <Badge
            key={x.code}
            variant="warn"
            title={`HKO ${x.code} ${x.action}${x.issue_time ? ' · issued ' + hm(x.issue_time) + ' HKT' : ''}`}
          >
            {x.name}
          </Badge>
        ))}
        {!tc.length && !warns.length && <Badge variant="ok">HKO: no warnings in force</Badge>}
      </div>
    </div>
  )
}
