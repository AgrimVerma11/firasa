import { cn } from '../../lib/cn';
import FirasaMark from '../FirasaMark';

// The Firasa logo: the mark set beside the wordmark. The name is lowercase in
// the product. At header size the mark uses a heavier stroke so its lines and
// the focal dot stay legible; the large watermark elsewhere keeps the hairline
// weight. The gap between mark and wordmark is half the mark's height.
export default function Logo({ className, showWord = true, size = 32 }) {
  return (
    <span
      className={cn('inline-flex items-center text-ink-900', className)}
      style={{ gap: size * 0.42 }}
    >
      <FirasaMark size={size} strokeScale={1.9} />
      {showWord && (
        <span
          className="font-medium leading-none"
          style={{ fontSize: Math.round(size * 0.6), letterSpacing: '-0.01em' }}
        >
          firasa
        </span>
      )}
    </span>
  );
}
