export function Skeleton({
  className = "",
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={`animate-pulse rounded-md ${className}`}
      style={{ background: "var(--surface-2)", ...style }}
    />
  );
}

export function SkeletonStatCard() {
  return (
    <div
      className="rounded-lg border px-4 py-3"
      style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
    >
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-2 h-7 w-14" />
    </div>
  );
}

export function SkeletonChartCard({ height = 280 }: { height?: number }) {
  return (
    <div
      className="rounded-lg border p-4"
      style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
    >
      <Skeleton className="mb-4 h-3 w-40" />
      <Skeleton style={{ height }} className="w-full" />
    </div>
  );
}

export function SkeletonTableCard({ rows = 8 }: { rows?: number }) {
  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
    >
      <div className="border-b p-3" style={{ borderColor: "var(--border)" }}>
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="flex flex-col gap-3 p-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-5 w-full" />
        ))}
      </div>
    </div>
  );
}

export function SkeletonListCard({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border p-4"
          style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
        >
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="mt-2 h-3 w-2/3" />
          <Skeleton className="mt-2 h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}
