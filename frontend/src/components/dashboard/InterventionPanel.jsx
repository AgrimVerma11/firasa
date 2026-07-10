import { useState } from 'react';
import { ArrowRight, CheckCircle2, ChevronDown, Sparkles, LifeBuoy, Link2 } from 'lucide-react';
import { featureLabel, impactMeta, toPercent, strengthLabel } from '../../lib/format';
import { cn } from '../../lib/cn';

// One recommendation, tied to a habit currently working against the student.
// Leads with a sharp title and a personal reason, gives a single concrete first
// step, shows the estimated effect on the risk signal, and tucks the "why this
// works" behind a toggle so the card stays calm at a glance.
function InterventionCard({ item }) {
  const [open, setOpen] = useState(false);
  const impact = impactMeta(item.expected_impact);
  const drop = item.risk_drop;

  return (
    <li
      className={cn(
        'rounded-xl border bg-white p-4 transition-shadow hover:shadow-card',
        item.is_primary ? 'border-brand-200 ring-1 ring-brand-100' : 'border-ink-100'
      )}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
          {item.priority}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {item.is_primary && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-brand-700">
                <Sparkles size={11} /> Start here
              </span>
            )}
            {item.acknowledged && (
              <span className="inline-flex items-center rounded-full bg-ink-100 px-2 py-0.5 text-[11px] font-medium text-ink-600">
                You named this
              </span>
            )}
            <span className="text-sm font-semibold text-ink-900">
              {item.title || featureLabel(item.feature)}
            </span>
          </div>

          {item.current_value != null && item.current_value !== '' && (
            <span className="mt-1 inline-flex items-center gap-1 text-xs text-ink-400">
              {featureLabel(item.feature)}
              <ArrowRight size={12} /> currently {String(item.current_value)}
            </span>
          )}

          {item.why && <p className="mt-2 text-sm leading-relaxed text-ink-600">{item.why}</p>}

          {item.bridge && (
            <p className="mt-2 flex items-start gap-1.5 text-xs italic leading-relaxed text-brand-700">
              <Link2 size={13} className="mt-0.5 shrink-0" />
              {item.bridge}
            </p>
          )}

          {item.first_step && (
            <div className="mt-3 rounded-lg bg-ink-50 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-700">
                Your first step
              </p>
              <p className="mt-1 text-sm leading-relaxed text-ink-700">{item.first_step}</p>
            </div>
          )}

          {item.safety && (
            <div className="mt-2 flex items-start gap-2 rounded-lg bg-risk-moderate/10 p-3 text-sm leading-relaxed text-ink-700">
              <LifeBuoy size={16} className="mt-0.5 shrink-0 text-risk-moderate" />
              <span>{item.safety}</span>
            </div>
          )}

          <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            {drop ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-risk-low">
                <span className="h-1.5 w-1.5 rounded-full bg-risk-low" />
                Could lower your risk signal from {toPercent(drop.from)}% to {toPercent(drop.to)}%
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-500">
                <span className={cn('h-1.5 w-1.5 rounded-full', impact.dot)} />
                {impact.label}
              </span>
            )}

            {item.reframe && (
              <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                className="inline-flex items-center gap-1 text-xs font-medium text-ink-400 hover:text-ink-700"
                aria-expanded={open}
              >
                Why this works
                <ChevronDown
                  size={13}
                  className={cn('transition-transform', open && 'rotate-180')}
                />
              </button>
            )}
          </div>

          {open && item.reframe && (
            <div className="mt-2 rounded-lg border border-ink-100 bg-ink-50/60 p-3">
              <p className="text-sm leading-relaxed text-ink-600">{item.reframe}</p>
              {item.evidence && (
                <p className="mt-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-400">
                  Based on {item.evidence}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

// Shown when there is nothing urgent to fix: a positive read, the student's own
// strongest habits named as anchors, and a few persona-tailored habits for
// staying consistent, so a well-doing student gets forward guidance rather than a
// dead end.
function MaintenanceView({ maintenance }) {
  const strengths = maintenance?.strengths || [];
  const habits = maintenance?.habits || [];

  return (
    <div>
      <div className="flex items-start gap-3 rounded-xl bg-risk-low/5 p-4">
        <CheckCircle2 className="mt-0.5 shrink-0 text-risk-low" size={20} />
        <div>
          <p className="text-sm font-medium text-ink-800">
            Your habits are working in your favour.
          </p>
          <p className="mt-1 text-sm text-ink-500">
            There is nothing urgent to fix. These are about protecting what is working and staying
            consistent.
          </p>
        </div>
      </div>

      {strengths.length > 0 && (
        <div className="mt-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-400">
            Your anchors right now
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {strengths.map((strength) => (
              <span
                key={strength.feature}
                className="rounded-full bg-risk-low/10 px-2.5 py-1 text-xs font-medium text-risk-low"
              >
                {strengthLabel(strength.feature)}
              </span>
            ))}
          </div>
        </div>
      )}

      {habits.length > 0 && (
        <ol className="mt-4 space-y-3">
          {habits.map((habit) => (
            <li key={habit.title} className="rounded-xl border border-ink-100 bg-white p-4">
              <p className="text-sm font-semibold text-ink-900">{habit.title}</p>
              <p className="mt-1 text-sm leading-relaxed text-ink-600">{habit.detail}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// The actionable side of the result: a short, ranked set of things a student
// could try, each tied to a habit that is currently working against them. It
// opens with a persona-aware line, and for students already under pressure it
// leads with a single step and holds the rest back until they are ready. When
// there is nothing to fix, it becomes a maintenance plan instead. Kept concrete
// and encouraging rather than clinical.
export default function InterventionPanel({ interventions, guidance, maintenance }) {
  if (!interventions || interventions.length === 0) {
    return <MaintenanceView maintenance={maintenance} />;
  }

  const intro = guidance?.intro;
  const focusOne = Boolean(guidance?.focus_one) && interventions.length > 1;
  const [primary, ...rest] = interventions;

  return (
    <div>
      {intro && <p className="mb-4 text-sm leading-relaxed text-ink-600">{intro}</p>}

      {focusOne ? (
        <div className="space-y-3">
          <ol className="space-y-3">
            <InterventionCard item={primary} />
          </ol>
          {rest.length > 0 && (
            <>
              <p className="pt-1 text-xs font-medium uppercase tracking-wide text-ink-400">
                When you are ready, a couple more
              </p>
              <ol className="space-y-3">
                {rest.map((item) => (
                  <InterventionCard key={item.feature} item={item} />
                ))}
              </ol>
            </>
          )}
        </div>
      ) : (
        <ol className="space-y-3">
          {interventions.map((item) => (
            <InterventionCard key={item.feature} item={item} />
          ))}
        </ol>
      )}
    </div>
  );
}
