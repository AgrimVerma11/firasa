import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Sparkles } from 'lucide-react';
import { featureLabel } from '../../lib/format';

const IMPACT_COLOR = {
  high: '#d85a30',
  medium: '#ef9f27',
  low: '#1d9e75',
};

function DriverTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-lg border border-ink-100 bg-white px-3 py-2 text-xs shadow-lift">
      <p className="font-semibold text-ink-900">{point.name}</p>
      <p className="mt-0.5 text-ink-500">Currently: {point.current}</p>
      <p className="text-ink-500">Relative weight: {point.value.toFixed(2)}</p>
    </div>
  );
}

// Charts the habits currently pushing a student's risk up, ranked by their SHAP
// weight. Only risk-increasing drivers come back from the API, so an empty list
// is genuinely good news and gets an encouraging message instead of a blank box.
export default function FeatureImportanceChart({ interventions }) {
  const data = (interventions || []).map((item) => ({
    name: featureLabel(item.feature),
    value: Math.abs(item.shap_impact),
    current: item.current_value,
    impact: item.expected_impact,
  }));

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl bg-risk-low/5 py-10 text-center">
        <Sparkles className="mb-2 text-risk-low" size={22} />
        <p className="text-sm font-medium text-ink-800">Nothing is pushing your risk up right now.</p>
        <p className="mt-1 max-w-xs text-xs text-ink-500">
          Your current habits are working in your favour. Keep protecting the routines that got you
          here.
        </p>
      </div>
    );
  }

  return (
    <div style={{ height: data.length * 56 + 16 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <XAxis type="number" hide domain={[0, 'dataMax']} />
          <YAxis
            type="category"
            dataKey="name"
            width={150}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 13, fill: '#505d73' }}
          />
          <Tooltip cursor={{ fill: 'rgba(83,74,183,0.05)' }} content={<DriverTooltip />} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={22}>
            {data.map((entry, index) => (
              <Cell key={index} fill={IMPACT_COLOR[entry.impact] || '#8479d2'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
