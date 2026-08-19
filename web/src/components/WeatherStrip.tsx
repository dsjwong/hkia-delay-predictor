import { useMetaCtx } from '@/lib/meta-context'
import { Badge } from './ui/badge'
import { Tooltip } from './ui/tooltip'
import { Skeleton } from './ui/skeleton'
import { hm } from '@/lib/time'
import { cn } from '@/lib/utils'

/** Latest METAR (raw, mono) + HKO warnings / TC signal. */
export function WeatherStrip({ compact = false, className }: { compact?: boolean; className?: string }) {
  const { weather } = useMetaCtx()
  const w = weather.data
  if (!w)
    return weather.error ? (
      <div className={cn('text-xs text-muted', className)}>weather: {weather.error}</div>
    ) : (
      <div className={cn('space-y-1.5', className)} role="status" aria-label="loading weather">
        <Skeleton className="h-8" />
        <Skeleton className="h-4 w-40" />
      </div>
    )
  const tc = w.tc_active
  const warns = tc.length ? w.hko_warnings.filter((x) => x.code !== 'WTCSGNL') : w.hko_warnings
  return (
    <div className={cn('space-y-1.5', className)}>
      {w.metar && (
        <Tooltip
          content={`VHHH METAR issued ${hm(w.metar.report_time)} HKT · ${w.metar.flt_cat ?? '?'} · wind ${w.metar.wdir ?? 'VRB'}°/${w.metar.wspd_kt ?? '—'} kt${w.metar.wgst_kt ? ' G' + w.metar.wgst_kt : ''} · vis ${w.metar.visib ?? '—'} sm · ${w.metar.temp_c ?? '—'}°C`}
          side="bottom"
          className="w-full"
        >
          <div className={cn('hk-strip w-full', compact && 'text-[0.7rem] py-1.5')} tabIndex={0}>
            {w.metar.raw_ob}
          </div>
        </Tooltip>
      )}
      <div className="flex flex-wrap gap-1">
        {tc.map((t) => (
          <Badge key={t.signal + t.start_ts} variant="crit" dot>
            TC signal {t.signal} {t.tc_name ?? ''}
          </Badge>
        ))}
        {warns.map((x) => (
          <Badge
            key={x.code}
            variant="warn"
            dot
            title={`HKO ${x.code} ${x.action}${x.issue_time ? ' · issued ' + hm(x.issue_time) + ' HKT' : ''}`}
          >
            {x.name}
          </Badge>
        ))}
        {!tc.length && !warns.length && (
          <Badge variant="ok" dot>
            HKO: no warnings in force
          </Badge>
        )}
      </div>
    </div>
  )
}
