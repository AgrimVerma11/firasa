// Custom angular-axis label for the radar charts. Long labels (for example
// "Daily productivity" or "Low screen use") run off the edge of the container on
// narrow screens and get clipped. This wraps each label onto up to two lines and
// anchors it toward the centre based on which side of the chart it sits on, so
// the text stays inside the chart on mobile.
export default function RadarAngleTick(props) {
  const { x, y, cx, cy, payload } = props;
  const label = String(payload?.value ?? '');

  // Greedily wrap into lines of at most ~12 characters.
  const lines = [];
  let current = '';
  for (const word of label.split(' ')) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > 12 && current) {
      lines.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) lines.push(current);

  // Anchor labels on the right toward their start and labels on the left toward
  // their end, so wrapped text grows inward rather than off-screen. Falls back
  // to centre when the polar centre is unknown.
  const hasCentre = typeof cx === 'number' && typeof cy === 'number';
  const anchor = hasCentre && x > cx + 8 ? 'start' : hasCentre && x < cx - 8 ? 'end' : 'middle';
  const dx = anchor === 'start' ? 4 : anchor === 'end' ? -4 : 0;
  const firstDy = -((lines.length - 1) * 6);

  return (
    <text x={x + dx} y={y} textAnchor={anchor} fill="#65748c" fontSize={11}>
      {lines.map((line, index) => (
        <tspan key={line} x={x + dx} dy={index === 0 ? firstDy : 12}>
          {line}
        </tspan>
      ))}
    </text>
  );
}
