import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';
import { riskMeta } from '../../lib/format';
import { cn } from '../../lib/cn';

const ICONS = {
  low: ShieldCheck,
  moderate: Shield,
  high: ShieldAlert,
};

// The risk level as a coloured pill. We show the level plainly but lead with the
// reflective framing elsewhere, so this reads as a signal, not a verdict.
export default function RiskBadge({ level, size = 'md' }) {
  const meta = riskMeta(level);
  const Icon = ICONS[meta.key] || Shield;
  const padding = size === 'lg' ? 'px-4 py-2 text-sm' : 'px-3 py-1.5 text-xs';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full font-semibold ring-1',
        meta.bg,
        meta.text,
        meta.ring,
        padding
      )}
    >
      <Icon size={size === 'lg' ? 18 : 15} />
      {level || 'Unknown'}
    </span>
  );
}
