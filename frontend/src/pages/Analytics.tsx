import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, SectionTitle } from "../components/Badge";
import HorizontalBarChart from "../components/charts/HorizontalBarChart";
import TimeSeriesChart from "../components/charts/TimeSeriesChart";
import { BUCKET_COLOR } from "../lib/api";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip } from "../components/charts/tooltip";
import { Skeleton, SkeletonChartCard } from "../components/skeletons/Skeleton";

export default function Analytics() {
  const q = useQuery({ queryKey: ["analytics"], queryFn: api.analytics });

  if (q.isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <Skeleton className="h-6 w-28" />
          <Skeleton className="mt-2 h-3 w-56" />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <SkeletonChartCard />
          <SkeletonChartCard />
        </div>
        <SkeletonChartCard height={360} />
        <SkeletonChartCard height={280} />
      </div>
    );
  }
  if (q.isError || !q.data) return <div style={{ color: "var(--status-critical)" }}>Failed to load analytics.</div>;

  const d = q.data;

  const attackTypes = Array.from(new Set(d.severity_by_attack_type.map((r) => r.attack_type)));
  const severityRows = attackTypes.map((attack_type) => {
    const row: Record<string, string | number> = { attack_type };
    for (const bucket of ["Critical", "High", "Medium", "Low"]) {
      const match = d.severity_by_attack_type.find((r) => r.attack_type === attack_type && r.bucket === bucket);
      row[bucket] = match?.count ?? 0;
    }
    return row;
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>Analytics</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>Trends across the current alert stream</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Alerts Over Time</SectionTitle>
          <TimeSeriesChart data={d.alerts_over_time} />
        </Card>
        <Card>
          <SectionTitle>Top Source IPs</SectionTitle>
          <HorizontalBarChart
            data={d.top_sources.map((s) => ({ label: s.source_ip, value: s.count }))}
            color="var(--series-3)"
          />
        </Card>
      </div>

      <Card>
        <SectionTitle>Severity Breakdown by Attack Type</SectionTitle>
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={severityRows} margin={{ top: 8, right: 16, left: 8, bottom: 70 }}>
            <CartesianGrid vertical={false} stroke="var(--gridline)" />
            <XAxis
              dataKey="attack_type"
              angle={-40}
              textAnchor="end"
              interval={0}
              tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              stroke="var(--axis)"
            />
            <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} stroke="var(--axis)" allowDecimals={false} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
            <Legend verticalAlign="top" height={32} wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }} />
            {["Critical", "High", "Medium", "Low"].map((bucket) => (
              <Bar key={bucket} dataKey={bucket} stackId="sev" name={bucket} fill={BUCKET_COLOR[bucket]} radius={[0, 0, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <SectionTitle>Known Campaign Pattern Matches</SectionTitle>
        {d.pattern_matches.length ? (
          <HorizontalBarChart
            data={d.pattern_matches.map((p) => ({ label: p.pattern, value: p.count }))}
            color="var(--series-7)"
          />
        ) : (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            No correlated campaigns matched a known pattern in this alert stream.
          </p>
        )}
      </Card>
    </div>
  );
}
