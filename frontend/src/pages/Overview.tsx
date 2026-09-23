import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import StatCard from "../components/StatCard";
import { Card, SectionTitle } from "../components/Badge";
import BucketBarChart from "../components/charts/BucketBarChart";
import HorizontalBarChart from "../components/charts/HorizontalBarChart";
import PageSkeleton from "../components/skeletons/PageSkeleton";

export default function Overview() {
  const overviewQ = useQuery({ queryKey: ["overview"], queryFn: api.overview });
  const analyticsQ = useQuery({ queryKey: ["analytics"], queryFn: api.analytics });

  if (overviewQ.isLoading) return <PageSkeleton />;
  if (overviewQ.isError || !overviewQ.data) return <div style={{ color: "var(--status-critical)" }}>Failed to load overview.</div>;

  const o = overviewQ.data;
  const attackData = (analyticsQ.data?.attack_type_distribution ?? [])
    .map((d) => ({ label: d.attack_type, value: d.count }))
    .slice(0, 10);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>Overview</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          AI-assisted SOC alert prioritization — live system status
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Total Alerts" value={o.total_alerts} />
        <StatCard label="Critical" value={o.bucket_counts.Critical} accent="var(--status-critical)" />
        <StatCard label="High" value={o.bucket_counts.High} accent="var(--status-serious)" />
        <StatCard label="Medium" value={o.bucket_counts.Medium} accent="var(--status-warning)" />
        <StatCard label="Campaigns" value={o.correlated_campaigns} />
        <StatCard label="Incidents Logged" value={o.incident_log.total} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Priority Distribution</SectionTitle>
          <BucketBarChart counts={o.bucket_counts} />
        </Card>
        <Card>
          <SectionTitle>Attack Type Distribution</SectionTitle>
          <HorizontalBarChart data={attackData} color="var(--series-1)" />
        </Card>
      </div>

      <Card>
        <SectionTitle>Knowledge Base &amp; Escalation</SectionTitle>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {o.incident_log.total} total incidents logged ({o.incident_log.correlated_campaigns} correlated
          campaigns, {o.incident_log.isolated_critical} isolated critical). Knowledge base holds{" "}
          {o.knowledge_base.total_patterns} patterns, {o.knowledge_base.auto_learned} auto-learned by the
          Escalation Agent's novelty-detection loop.
        </p>
      </Card>
    </div>
  );
}
