export default function ProgressRing({ fraction, size, stroke = 25 }: { fraction: number; size: number; stroke?: number }) {
  const radius = (size - stroke) / 2;
  const length = Math.PI * 2 * radius;
  return <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
    <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#d7e8d4" strokeWidth={stroke} />
    <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#55765e" strokeWidth={stroke} strokeLinecap="round" strokeDasharray={`${length * fraction} ${length}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
  </svg>;
}
