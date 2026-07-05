import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { featureLabel, impactMeta } from '../../lib/format';
import { cn } from '../../lib/cn';

// The actionable side of the result: a short, ranked list of things a student
// could try, each tied to a habit that is currently working against them. Kept
// concrete and encouraging rather than clinical.
export default function InterventionPanel({ interventions }) {
  if (!interventions || interventions.length === 0) {
    return (
      <div className="flex items-start gap-3 rounded-xl bg-risk-low/5 p-4">
        <CheckCircle2 className="mt-0.5 shrink-0 text-risk-low" size={20} />
        <div>
          <p className="text-sm font-medium text-ink-800">No priority changes right now.</p>
          <p className="mt-1 text-sm text-ink-500">
            Your habits look balanced. A good next step is simply to keep the routines that are
            working and check back in a few weeks.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ol className="space-y-3">
      {interventions.map((item) => {
        const impact = impactMeta(item.expected_impact);
        return (
          <li
            key={item.feature}
            className="rounded-xl border border-ink-100 bg-white p-4 transition-shadow hover:shadow-card"
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
                {item.priority}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-sm font-semibold text-ink-900">
                    {featureLabel(item.feature)}
                  </span>
                  {item.current_value != null && item.current_value !== '' && (
                    <span className="inline-flex items-center gap-1 text-xs text-ink-400">
                      <ArrowRight size={12} /> currently {String(item.current_value)}
                    </span>
                  )}
                </div>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{item.recommendation}</p>
                <div className="mt-2.5 flex items-center gap-1.5">
                  <span className={cn('h-1.5 w-1.5 rounded-full', impact.dot)} />
                  <span className="text-xs font-medium text-ink-500">{impact.label}</span>
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
