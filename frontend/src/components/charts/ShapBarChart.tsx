import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FeatureImpact } from "../../lib/api";
import { ChartTooltip } from "./tooltip";

export default function ShapBarChart({ features }: { features: FeatureImpact[] }) {
  const data = [...features]
    .sort((a, b) => a.shap_value - b.shap_value)
    .map((f) => ({ label: f.feature, value: f.shap_value }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="var(--gridline)" />
        <XAxis type="number" tick={{ fill: "var(--text-muted)", fontSize: 12 }} stroke="var(--axis)" />
        <YAxis
          type="category"
          dataKey="label"
          width={170}
          tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
          stroke="var(--axis)"
        />
        <ReferenceLine x={0} stroke="var(--axis)" />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
        <Bar dataKey="value" name="SHAP impact" radius={[4, 4, 4, 4]} barSize={14}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.value >= 0 ? "var(--status-critical)" : "var(--status-good)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
