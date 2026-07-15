import { motion, useReducedMotion } from 'framer-motion';
import { clamp } from '../../lib/format';

// The momentum index: one number on a 0-10 scale, the tier word it lands in, and
// a bar with the tier boundaries ticked so that word is grounded in something the
// student can see. The ticks sit near-invisible on the empty track and catch the
// light as the fill passes them, which is what makes "how far to the next band"
// readable at a glance.
//
// Colour follows the tier, not the risk level. The two answer different
// questions, so a green "On track" bar under an amber risk badge is not a
// contradiction, and collapsing one into the other would hide that.

// Keys mirror MOMENTUM_TIERS in ml/config.py. The tier word itself comes from the
// API, so the backend stays the source of truth and this is only the paint.
const TIER_STYLE = {
  'Strongly positive': { fill: '#534ab7', dot: 'bg-brand-600' },
  'On track': { fill: '#1d9e75', dot: 'bg-risk-low' },
  'Needs attention': { fill: '#ef9f27', dot: 'bg-risk-moderate' },
  'At risk': { fill: '#d85a30', dot: 'bg-risk-high' },
};

const FALLBACK_STYLE = { fill: '#65748c', dot: 'bg-ink-400' };

// The band floors as a fraction of the scale, also from MOMENTUM_TIERS.
const TIER_MARKS = [0.5, 0.7, 0.9];

export default function MomentumIndex({ index, tier, scaleMax = 10, note }) {
  const value = clamp(Number(index) || 0, 0, scaleMax);
  const fraction = value / scaleMax;
  const style = TIER_STYLE[tier] || FALLBACK_STYLE;
  const reduceMotion = useReducedMotion();

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-baseline gap-2">
        <span className="text-6xl font-bold tracking-tight text-ink-900 tabular-nums">
          {value.toFixed(1)}
        </span>
        <span className="text-xl font-medium text-ink-400">/ {scaleMax}</span>
      </div>

      {tier && (
        <div className="mt-2.5 flex items-center gap-2">
          <span className={`h-2 w-2 shrink-0 rounded-full ${style.dot}`} />
          <span className="text-sm text-ink-600">{tier}</span>
        </div>
      )}

      <div
        className="relative mb-5 mt-4 h-2 w-full overflow-hidden rounded-full bg-ink-100"
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={scaleMax}
        aria-valuetext={`${value.toFixed(1)} out of ${scaleMax}${tier ? `, ${tier}` : ''}`}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundImage: `linear-gradient(90deg, ${style.fill}b3, ${style.fill})` }}
          initial={{ width: reduceMotion ? `${fraction * 100}%` : 0 }}
          animate={{ width: `${fraction * 100}%` }}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.7, ease: 'easeOut' }}
        />
        {TIER_MARKS.map((mark) => (
          <span
            key={mark}
            className="absolute top-0 h-full w-px bg-white/80"
            style={{ left: `${mark * 100}%` }}
          />
        ))}
      </div>

      {/* mt-auto keeps the note on the card floor when a taller sibling stretches
          this card, so the gap opens above the divider instead of below the text. */}
      {note && (
        <div className="mt-auto border-t border-ink-100 pt-4">
          <p className="text-sm leading-relaxed text-ink-600">{note}</p>
        </div>
      )}
    </div>
  );
}
