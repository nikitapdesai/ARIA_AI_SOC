import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip } from "./tooltip";

export default function TimeSeriesChart({ data }: { data: { timestamp: string; count: number }[] }) {
  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={formatted} margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke="var(--gridline)" />
        <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 11 }} stroke="var(--axis)" />
        <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} stroke="var(--axis)" allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} />
        <Line
          type="monotone"
          dataKey="count"
          name="Alerts"
          stroke="var(--series-1)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
