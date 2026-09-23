import { BUCKET_COLOR } from "../lib/api";

export function BucketBadge({ bucket }: { bucket: string }) {
  const color = BUCKET_COLOR[bucket] ?? "var(--text-muted)";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ color, background: "var(--surface-2)" }}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {bucket}
    </span>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-lg border p-4 ${className}`}
      style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
      {children}
    </h2>
  );
}
