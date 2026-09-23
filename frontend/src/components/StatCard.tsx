export default function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div
      className="rounded-lg border px-4 py-3"
      style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
    >
      <div className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
      <div
        className="mt-1 text-2xl font-semibold"
        style={{ color: accent ?? "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </div>
    </div>
  );
}
