import { cn } from '../../lib/cn';

// A short set of clearly described bands, used where a bare 1..5 scale reads as
// vague (stress, energy). Each option still sends the plain numeric value the
// model already understands, but the student chooses against a description
// instead of an unlabelled number. The accent dot runs light to deep across the
// bands to hint at intensity, deliberately not a red / amber / green verdict.
const ACCENTS = ['bg-brand-300', 'bg-brand-500', 'bg-brand-700'];

export default function BandControl({ value, onChange, options = [], name }) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-3" role="radiogroup" aria-label={name}>
      {options.map((option, i) => {
        const selected = Number(value) === Number(option.value);
        const accent = ACCENTS[Math.min(i, ACCENTS.length - 1)];
        return (
          <button
            key={String(option.value)}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              'flex h-full flex-col rounded-xl border p-3.5 text-left transition-all duration-150',
              selected
                ? 'border-brand-600 bg-brand-50 shadow-sm ring-1 ring-brand-200'
                : 'border-ink-200 bg-white hover:border-brand-300 hover:bg-ink-50/40'
            )}
          >
            <span className="flex items-center gap-2">
              <span className={cn('h-2 w-2 shrink-0 rounded-full', accent)} />
              <span
                className={cn('text-sm font-semibold', selected ? 'text-brand-700' : 'text-ink-900')}
              >
                {option.label}
              </span>
            </span>
            <span className="mt-1.5 text-xs leading-relaxed text-ink-500">{option.detail}</span>
          </button>
        );
      })}
    </div>
  );
}
