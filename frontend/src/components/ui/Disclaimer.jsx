import { Info } from 'lucide-react';
import { cn } from '../../lib/cn';

// The safety framing shown near any result. Text comes from the API (config
// DISCLAIMER) so the wording stays in one place; a shorter fallback is used if
// the API did not send it.
const FALLBACK =
  'Firasa is a self-reflection aid based on self-reported study habits and wellbeing. ' +
  'It is not a medical, psychological, or academic assessment and does not predict grades. ' +
  'Use it to reflect and to start a conversation with a mentor.';

export default function Disclaimer({ text, className, compact = false }) {
  return (
    <div
      className={cn(
        'flex gap-3 rounded-xl border border-ink-200 bg-white/70 text-ink-600',
        compact ? 'p-3 text-xs' : 'p-4 text-sm',
        className
      )}
      role="note"
    >
      <Info size={compact ? 16 : 18} className="mt-0.5 shrink-0 text-brand-500" />
      <p className="leading-relaxed">{text || FALLBACK}</p>
    </div>
  );
}
