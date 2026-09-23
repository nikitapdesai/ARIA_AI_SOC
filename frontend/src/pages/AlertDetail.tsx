import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { BucketBadge, Card, SectionTitle } from "../components/Badge";
import StatCard from "../components/StatCard";
import ShapBarChart from "../components/charts/ShapBarChart";
import { Skeleton, SkeletonChartCard, SkeletonStatCard } from "../components/skeletons/Skeleton";

export default function AlertDetail() {
  const { alertId = "" } = useParams();
  const q = useQuery({ queryKey: ["alert", alertId], queryFn: () => api.alertDetail(alertId) });

  if (q.isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <Skeleton className="h-3 w-32" />
          <Skeleton className="mt-2 h-6 w-40" />
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonStatCard key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <SkeletonChartCard height={220} />
          <SkeletonChartCard />
        </div>
      </div>
    );
  }
  if (q.isError || !q.data) return <div style={{ color: "var(--status-critical)" }}>Alert not found.</div>;

  const a = q.data;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/alerts" className="text-xs hover:underline" style={{ color: "var(--text-muted)" }}>
          ← Back to Alert Queue
        </Link>
        <h1 className="mt-1 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>{a.alert_id}</h1>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Attack Type" value={a.predicted_class} />
        <StatCard label="Confidence" value={`${(a.confidence * 100).toFixed(1)}%`} />
        <StatCard label="Priority Score" value={`${a.priority_score.toFixed(1)} / 100`} />
        <div className="rounded-lg border px-4 py-3" style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}>
          <div className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Priority Bucket
          </div>
          <div className="mt-1.5"><BucketBadge bucket={a.priority_bucket} /></div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Priority Score Breakdown</SectionTitle>
          <dl className="flex flex-col gap-2 text-sm">
            <Row label="Own attack-type severity" value={a.own_severity_label} />
            <Row label="Effective severity score used" value={`${a.effective_severity_score.toFixed(2)} / 1.00`} />
            <Row label="Model confidence" value={`${(a.confidence * 100).toFixed(1)}%`} />
            <Row label="Part of correlated campaign" value={a.is_correlated_campaign ? "Yes" : "No"} />
            {a.kill_chain_stages_seen && <Row label="Kill-chain stages observed" value={a.kill_chain_stages_seen} />}
            {a.matched_known_pattern && (
              <Row
                label="Matched known pattern"
                value={`${a.matched_known_pattern} (similarity ${a.matched_pattern_similarity?.toFixed(2)})`}
              />
            )}
            <Row label="Source → Destination" value={`${a.source_ip} → ${a.destination_ip}`} />
          </dl>
          <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>
            Priority Score = 100 × (0.5 × severity + 0.3 × confidence + 0.2 × frequency). Severity is elevated
            to the matched campaign's real typical severity (looked up from the knowledge base) when higher
            than the attack type's own severity.
          </p>
        </Card>

        <Card>
          <SectionTitle>Why the Model Flagged This (SHAP)</SectionTitle>
          {a.top_contributing_features?.length ? (
            <>
              <ShapBarChart features={a.top_contributing_features} />
              <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                Top 5 network features that most influenced this classification, via SHAP on the Random
                Forest base model. Red increases risk, green decreases it.
              </p>
            </>
          ) : (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>No SHAP explanation available.</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt style={{ color: "var(--text-muted)" }}>{label}</dt>
      <dd className="text-right font-medium" style={{ color: "var(--text-primary)" }}>{value}</dd>
    </div>
  );
}
