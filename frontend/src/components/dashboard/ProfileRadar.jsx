import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { buildProfileRadar } from '../../lib/profile';

function RadarTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-lg border border-ink-100 bg-white px-3 py-1.5 text-xs shadow-lift">
      <span className="font-semibold text-ink-900">{point.axis}</span>
      <span className="ml-2 text-ink-500">{point.value} / 100</span>
    </div>
  );
}

// Plots a student's key behaviours on a single shape, every axis oriented so
// that further from the centre means a healthier habit. It is a mirror, not a
// score: the point is to see the overall balance at a glance.
export default function ProfileRadar({ answers }) {
  const data = buildProfileRadar(answers);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} outerRadius="70%">
        <PolarGrid stroke="#e5e7eb" />
        <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: '#65748c' }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar
          name="Your profile"
          dataKey="value"
          stroke="#534ab7"
          strokeWidth={2}
          fill="#534ab7"
          fillOpacity={0.22}
          isAnimationActive
        />
        <Tooltip content={<RadarTooltip />} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
