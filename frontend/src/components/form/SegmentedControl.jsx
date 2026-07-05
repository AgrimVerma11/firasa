import { cn } from '../../lib/cn';

// A row of selectable pills. Good for short option sets where seeing all the
// choices at once helps the student answer quickly. Wraps on narrow screens.
export default function SegmentedControl({ value, onChange, options, name, invalid }) {
  return (
    <div
      className={cn(
        'flex flex-wrap gap-2',
        invalid && 'rounded-xl ring-1 ring-risk-high/40 ring-offset-2'
      )}
      role="radiogroup"
      aria-label={name}
    >
      {options.map((option) => {
        const selected = value === option;
        return (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option)}
            className={cn(
              'rounded-xl border px-3.5 py-2 text-sm font-medium transition-all duration-150',
              selected
                ? 'border-brand-600 bg-brand-600 text-white shadow-sm'
                : 'border-ink-200 bg-white text-ink-600 hover:border-brand-300 hover:text-ink-900'
            )}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}
