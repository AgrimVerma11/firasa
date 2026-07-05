import { FIELD_BY_NAME, RADAR_AXES } from '../config/schema';

// Convert one answer into a 0..100 "healthier is higher" score for the radar.
// Ordinal answers use their position in the ordering; numeric scales are
// rescaled from their min/max; inverted axes (stress, screen time) are flipped
// so that a larger value always reads as a better habit on the chart.
function axisValue(axis, answers) {
  const raw = answers[axis.key];
  if (raw === undefined || raw === null || raw === '') return null;

  const field = FIELD_BY_NAME[axis.key];
  if (!field) return null;

  let fraction;
  if (axis.kind === 'ordinal') {
    const index = field.options.indexOf(raw);
    if (index < 0) return null;
    const span = field.options.length - 1 || 1;
    fraction = index / span;
  } else {
    const min = field.min ?? 1;
    const max = field.max ?? 5;
    const span = max - min || 1;
    fraction = (Number(raw) - min) / span;
  }

  if (axis.invert) fraction = 1 - fraction;
  return Math.round(fraction * 100);
}

// Build the radar series from a student's answers. Axes we cannot compute (an
// unanswered optional field) are dropped rather than shown as zero.
export function buildProfileRadar(answers) {
  return RADAR_AXES.map((axis) => ({
    axis: axis.label,
    value: axisValue(axis, answers),
  })).filter((point) => point.value !== null);
}
