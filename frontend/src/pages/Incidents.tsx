import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card } from "../components/Badge";
import { Skeleton, SkeletonListCard } from "../components/skeletons/Skeleton";

export default function Incidents() {
  const q = useQuery({ queryKey: ["incidents"], queryFn: () => api.incidents(150) });

  if (q.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <Skeleton className="h-6 w-28" />
          <Skeleton className="mt-2 h-3 w-64" />
        </div>
        <SkeletonListCard rows={6} />
      </div>
    );
  }
  if (q.isError || !q.data) return <div style={{ color: "var(--status-critical)" }}>Failed to load incidents.</div>;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>Incidents</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {q.data.total} total incidents logged by the Escalation Agent
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {q.data.incidents.map((inc) => (
          <Card key={inc.incident_id} className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="font-medium" style={{ color: "var(--text-primary)" }}>{inc.incident_id}</span>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium"
                style={{
                  background: "var(--surface-2)",
                  color: inc.incident_type === "correlated_campaign" ? "var(--series-7)" : "var(--status-critical)",
                }}
              >
                {inc.incident_type === "correlated_campaign" ? "Correlated Campaign" : "Isolated Critical"}
              </span>
            </div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
              {new Date(inc.logged_at).toLocaleString()} · source {inc.source_ip} · max priority{" "}
              {inc.max_priority_score.toFixed(1)}
            </div>
            <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
              {inc.alert_ids.length} alert(s): {inc.predicted_classes.join(", ")}
            </div>
            {inc.new_pattern_learned && (
              <div className="text-xs" style={{ color: "var(--series-3)" }}>
                → New knowledge base pattern learned: {inc.new_pattern_learned}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
