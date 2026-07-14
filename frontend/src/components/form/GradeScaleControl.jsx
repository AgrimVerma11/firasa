import { useState } from 'react';
import { cn } from '../../lib/cn';

// The grades question, with a scale switch so a student on a US 4.0 GPA or a
// percentage system can find their band without guessing. The value stored and
// sent is always the 10-point CGPA band the model was trained on; the tabs only
// relabel the same four bands.
export default function GradeScaleControl({ value, onChange, scales = [], options = [], name }) {
  const [scale, setScale] = useState(scales[0]?.id);

  return (
    <div>
      <div className="mb-2.5 inline-flex rounded-lg bg-ink-100 p-0.5">
        {scales.map((s) => {
          const on = scale === s.id;
          return (
            <button
              key={s.id}
              type="button"
              aria-pressed={on}
              onClick={() => setScale(s.id)}
              className={cn(
                'rounded-md px-3 py-1 text-xs font-semibold transition-colors',
                on ? 'bg-white text-brand-700 shadow-sm' : 'text-ink-500 hover:text-ink-800'
              )}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label={name}>
        {options.map((option) => {
          const selected = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(option.value)}
              className={cn(
                'rounded-xl border px-3 py-2.5 text-center text-sm font-semibold transition-all duration-150',
                selected
                  ? 'border-brand-600 bg-brand-600 text-white shadow-sm'
                  : 'border-ink-200 bg-white text-ink-700 hover:border-brand-300'
              )}
            >
              {option[scale]}
            </button>
          );
        })}
      </div>

      <p className="mt-2 text-xs text-ink-400">
        Pick the range that matches your most recent overall score.
      </p>
    </div>
  );
}
