import { cn } from '../../lib/cn';

// The Firasa mark: a small graduation-cap glyph plus the wordmark. Kept as an
// inline SVG so it stays crisp and needs no image request.
export default function Logo({ className, showWord = true }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <svg width="28" height="28" viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="16" fill="#534ab7" />
        <path
          d="M20 40V26l12-6 12 6v14"
          fill="none"
          stroke="#fff"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="32" cy="34" r="4.5" fill="#fff" />
      </svg>
      {showWord && (
        <span className="text-lg font-semibold tracking-tight text-ink-900">
          Fir<span className="text-brand-600">asa</span>
        </span>
      )}
    </span>
  );
}
