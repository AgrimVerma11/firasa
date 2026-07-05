import { Minus, Plus } from 'lucide-react';
import { clamp } from '../../lib/format';

// A bounded number picker with stepper buttons. Used for age. Keeps the value
// inside [min, max] whether it is changed by button or by typing.
export default function NumberStepper({ value, onChange, min = 0, max = 100, name }) {
  const current = Number.isFinite(Number(value)) ? Number(value) : min;

  const set = (next) => onChange(clamp(next, min, max));

  return (
    <div className="inline-flex items-center rounded-xl border border-ink-200 bg-white">
      <button
        type="button"
        aria-label="Decrease"
        onClick={() => set(current - 1)}
        disabled={current <= min}
        className="flex h-11 w-11 items-center justify-center rounded-l-xl text-ink-500 transition-colors hover:bg-ink-50 hover:text-ink-900 disabled:text-ink-200"
      >
        <Minus size={16} />
      </button>
      <input
        id={name}
        type="number"
        inputMode="numeric"
        value={current}
        min={min}
        max={max}
        onChange={(e) => set(parseInt(e.target.value, 10))}
        className="h-11 w-16 border-x border-ink-100 text-center text-sm font-semibold text-ink-900 focus:outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      />
      <button
        type="button"
        aria-label="Increase"
        onClick={() => set(current + 1)}
        disabled={current >= max}
        className="flex h-11 w-11 items-center justify-center rounded-r-xl text-ink-500 transition-colors hover:bg-ink-50 hover:text-ink-900 disabled:text-ink-200"
      >
        <Plus size={16} />
      </button>
    </div>
  );
}
