import { riskMeta, clamp } from '../../lib/format';

// A semicircular gauge for the indicative score. Drawn as two stroked arcs (a
// grey track and a coloured value) so it stays light and crisp at any size.
// The colour follows the risk level, so the score and the risk read as one idea.

function polar(cx, cy, r, deg) {
  const a = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) };
}

function arcPath(cx, cy, r, startDeg, endDeg) {
  const start = polar(cx, cy, r, startDeg);
  const end = polar(cx, cy, r, endDeg);
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  const sweep = startDeg > endDeg ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} ${sweep} ${end.x} ${end.y}`;
}

export default function ScoreMeter({ score, riskLevel, note }) {
  const value = clamp(Number(score) || 0, 0, 100);
  const fraction = value / 100;
  const meta = riskMeta(riskLevel);

  const cx = 100;
  const cy = 100;
  const r = 82;
  const endAngle = 180 * (1 - fraction);

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full max-w-[240px]">
        <svg viewBox="0 0 200 116" className="w-full">
          <path
            d={arcPath(cx, cy, r, 180, 0)}
            fill="none"
            stroke="#eceef2"
            strokeWidth="14"
            strokeLinecap="round"
          />
          {fraction > 0 && (
            <path
              d={arcPath(cx, cy, r, 180, endAngle)}
              fill="none"
              stroke={meta.color}
              strokeWidth="14"
              strokeLinecap="round"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
          <span className="text-4xl font-bold tracking-tight text-ink-900">{value}</span>
          <span className="text-xs font-medium uppercase tracking-wide text-ink-400">
            out of 100
          </span>
        </div>
      </div>
      {note && <p className="mt-3 max-w-xs text-center text-xs leading-relaxed text-ink-500">{note}</p>}
    </div>
  );
}
