import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BUCKET_COLOR } from "../../lib/api";
import { ChartTooltip } from "./tooltip";

const ORDER = ["Critical", "High", "Medium", "Low"];

export default function BucketBarChart({ counts }: { counts: Record<string, number> }) {
  const data = ORDER.map((bucket) => ({ bucket, value: counts[bucket] ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke="var(--gridline)" />
        <XAxis dataKey="bucket" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} stroke="var(--axis)" />
        <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} stroke="var(--axis)" />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
        <Bar dataKey="value" name="Alerts" radius={[4, 4, 0, 0]} barSize={48}>
          {data.map((d) => (
            <Cell key={d.bucket} fill={BUCKET_COLOR[d.bucket]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
