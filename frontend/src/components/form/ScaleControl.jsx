import { cn } from '../../lib/cn';

// A discrete 1..N scale rendered as numbered buttons with labelled ends. Used
// for the Likert-style inputs (productivity, stress, energy, routine).
export default function ScaleControl({ value, onChange, min = 1, max = 5, labels = {}, name }) {
  const steps = [];
  for (let i = min; i <= max; i += 1) steps.push(i);

  return (
    <div>
      <div className="flex gap-2" role="radiogroup" aria-label={name}>
        {steps.map((step) => {
          const selected = Number(value) === step;
          const midLabel = labels[step];
          return (
            <button
              key={step}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(step)}
              className={cn(
                'flex h-11 flex-1 flex-col items-center justify-center rounded-xl border text-sm font-semibold transition-all duration-150',
                selected
                  ? 'border-brand-600 bg-brand-600 text-white shadow-sm'
                  : 'border-ink-200 bg-white text-ink-600 hover:border-brand-300 hover:text-ink-900'
              )}
              title={midLabel || String(step)}
            >
              {step}
            </button>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between text-xs text-ink-400">
        <span>{labels[min] || min}</span>
        <span>{labels[max] || max}</span>
      </div>
    </div>
  );
}
