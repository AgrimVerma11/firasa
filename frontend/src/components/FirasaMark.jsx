// The Firasa mark.
//
// Four elements, each carrying meaning (documented in docs/BRAND.md):
//   the aperture    an open circle with a gap of about forty degrees at the
//                   upper right, so the mark reads as an eye and a lens and
//                   never as a closed verdict.
//   the horizon     the still surface that reflects, running past the circle
//                   on both sides.
//   the reflection  what sits beneath the surface, kept faint on purpose.
//   the sign        one filled dot, the single thing a reading surfaces.
//
// The strokes use currentColor so the mark takes on the surrounding text
// colour. The dot keeps the brand colour by default so it stays the point of
// focus; pass accent="currentColor" for a single-colour mark. strokeScale
// thickens the lines and the dot for small contexts (the header lockup), where
// the default hairline weight would otherwise disappear.
export default function FirasaMark({
  size = 32,
  className = '',
  accent = '#534AB7',
  strokeScale = 1,
  title,
}) {
  const labelled = Boolean(title);
  const circleWidth = 2 * strokeScale;
  const horizonWidth = 1.75 * strokeScale;
  const reflectionWidth = 1.5 * strokeScale;
  const dotRadius = 3 + (strokeScale - 1) * 1.5;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role={labelled ? 'img' : undefined}
      aria-label={labelled ? title : undefined}
      aria-hidden={labelled ? undefined : true}
    >
      {labelled ? <title>{title}</title> : null}
      <path
        d="M80.81 33.63A34 34 0 1 1 64.37 17.19"
        stroke="currentColor"
        strokeWidth={circleWidth}
        strokeLinecap="round"
      />
      <line
        x1="15"
        y1="62"
        x2="85"
        y2="62"
        stroke="currentColor"
        strokeWidth={horizonWidth}
        strokeLinecap="round"
      />
      <path
        d="M35 64Q50 74 65 64"
        stroke="currentColor"
        strokeWidth={reflectionWidth}
        strokeLinecap="round"
        opacity="0.22"
      />
      <circle cx="50" cy="60" r={dotRadius} fill={accent} />
    </svg>
  );
}
