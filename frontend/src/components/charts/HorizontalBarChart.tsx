import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip } from "./tooltip";

interface Datum {
  label: string;
  value: number;
  color?: string;
}

export default function HorizontalBarChart({
  data,
  color = "var(--series-1)",
  height = 320,
}: {
  data: Datum[];
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="var(--gridline)" />
        <XAxis type="number" tick={{ fill: "var(--text-muted)", fontSize: 12 }} stroke="var(--axis)" />
        <YAxis
          type="category"
          dataKey="label"
          width={150}
          tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
          stroke="var(--axis)"
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-2)" }} />
        <Bar dataKey="value" name="Count" radius={[0, 4, 4, 0]} barSize={14}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color ?? color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
