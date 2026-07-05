import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/cn';

// A styled native select. Native is the right call for long option lists: it is
// accessible for free, works well on touch devices, and does not trap focus.
export default function SelectControl({ value, onChange, options, name, invalid, placeholder }) {
  return (
    <div className="relative">
      <select
        id={name}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'w-full appearance-none rounded-xl border bg-white px-3.5 py-2.5 pr-10 text-sm text-ink-900',
          'transition-colors focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200',
          invalid ? 'border-risk-high/50' : 'border-ink-200 hover:border-ink-300'
        )}
      >
        <option value="" disabled>
          {placeholder || 'Select an option'}
        </option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <ChevronDown
        size={18}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-400"
      />
    </div>
  );
}
