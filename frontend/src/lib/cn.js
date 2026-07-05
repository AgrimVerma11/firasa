// Tiny classname joiner: keeps the truthy strings, drops falsey ones. Enough for
// conditional Tailwind classes without pulling in a dependency.
export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}
