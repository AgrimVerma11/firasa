import { cn } from '../../lib/cn';

export default function ProgressBar({ value, max = 100, className }) {
  const pct = Math.round((Math.min(value, max) / max) * 100);
  return (
    <div
      className={cn('h-1.5 w-full overflow-hidden rounded-full bg-ink-100', className)}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full bg-brand-600 transition-[width] duration-500 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
