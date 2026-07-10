import { FEATURE_LABELS } from '../config/schema';

// Risk levels come back from the API as "Low Risk" / "Moderate Risk" /
// "High Risk". This centralises the colour and copy that go with each so the
// badge, the score meter, and the charts all stay consistent.
const RISK_META = {
  'Low Risk': {
    key: 'low',
    short: 'Low',
    color: '#1d9e75',
    ring: 'ring-risk-low/30',
    text: 'text-risk-low',
    bg: 'bg-risk-low/10',
    dot: 'bg-risk-low',
  },
  'Moderate Risk': {
    key: 'moderate',
    short: 'Moderate',
    color: '#ef9f27',
    ring: 'ring-risk-moderate/30',
    text: 'text-risk-moderate',
    bg: 'bg-risk-moderate/10',
    dot: 'bg-risk-moderate',
  },
  'High Risk': {
    key: 'high',
    short: 'High',
    color: '#d85a30',
    ring: 'ring-risk-high/30',
    text: 'text-risk-high',
    bg: 'bg-risk-high/10',
    dot: 'bg-risk-high',
  },
};

const FALLBACK_RISK = {
  key: 'unknown',
  short: 'Unknown',
  color: '#65748c',
  ring: 'ring-ink-200',
  text: 'text-ink-500',
  bg: 'bg-ink-100',
  dot: 'bg-ink-400',
};

export function riskMeta(level) {
  return RISK_META[level] || FALLBACK_RISK;
}

// Turn a raw feature name into something readable. Prefer the curated labels;
// fall back to a tidy title-case of the underscored name.
export function featureLabel(name) {
  if (FEATURE_LABELS[name]) return FEATURE_LABELS[name];
  if (!name) return '';
  return name
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

// Positive phrasing for a feature when it is a strength (a protective habit), so
// a low-stress student reads "Manages stress", not "Stress level".
const STRENGTH_LABELS = {
  stress_level: 'Manages stress',
  screen_time_non_study: 'Low screen use',
  study_consistency: 'Consistent',
  tasks_on_time: 'Punctual',
  assignments_on_time: 'Submits on time',
  procrastination_level: 'Low procrastination',
  sleep_hours: 'Well rested',
  attendance_percentage: 'Strong attendance',
  focus_duration: 'Good focus',
  career_goal_clarity: 'Clear goals',
  daily_productivity: 'Productive',
  energy_level: 'High energy',
  routine_rating: 'Structured routine',
  revision_frequency: 'Revises regularly',
  study_hours_daily: 'Puts in the hours',
};

export function strengthLabel(name) {
  return STRENGTH_LABELS[name] || featureLabel(name);
}

const IMPACT_META = {
  high: { label: 'High impact', dot: 'bg-risk-high' },
  medium: { label: 'Medium impact', dot: 'bg-risk-moderate' },
  low: { label: 'Lower impact', dot: 'bg-risk-low' },
};

export function impactMeta(level) {
  return IMPACT_META[level] || { label: 'Impact', dot: 'bg-ink-400' };
}

export function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}

// Probabilities arrive as 0..1 floats; show them as whole percentages.
export function toPercent(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0';
  return Math.round(clamp(value, 0, 1) * 100).toString();
}

export function signed(value, digits = 1) {
  const rounded = Number(value.toFixed(digits));
  if (rounded > 0) return `+${rounded}`;
  return rounded.toString();
}
