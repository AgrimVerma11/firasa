import { cn } from '../../lib/cn';

export default function Badge({ className, children, tone = 'neutral' }) {
  const tones = {
    neutral: 'bg-ink-100 text-ink-600',
    brand: 'bg-brand-50 text-brand-700',
    low: 'bg-risk-low/10 text-risk-low',
    moderate: 'bg-risk-moderate/10 text-risk-moderate',
    high: 'bg-risk-high/10 text-risk-high',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        tones[tone] || tones.neutral,
        className
      )}
    >
      {children}
    </span>
  );
}
