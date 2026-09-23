import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { BucketBadge, Card } from "../components/Badge";
import { SkeletonTableCard } from "../components/skeletons/Skeleton";

const BUCKETS = ["Critical", "High", "Medium", "Low"];
const PAGE_SIZE = 50;

export default function AlertQueue() {
  const [bucket, setBucket] = useState<string[]>([...BUCKETS]);
  const [attackType, setAttackType] = useState<string[]>([]);
  const [campaignOnly, setCampaignOnly] = useState(false);
  const [page, setPage] = useState(0);

  useEffect(() => setPage(0), [bucket, attackType, campaignOnly]);

  const attackTypesQ = useQuery({ queryKey: ["attack-types"], queryFn: api.attackTypes });
  const alertsQ = useQuery({
    queryKey: ["alerts", bucket, attackType, campaignOnly, page],
    queryFn: () =>
      api.alerts({
        bucket,
        attack_type: attackType,
        campaign_only: campaignOnly,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  function toggleBucket(b: string) {
    setBucket((prev) => (prev.includes(b) ? prev.filter((x) => x !== b) : [...prev, b]));
  }

  const total = alertsQ.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rangeStart = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const rangeEnd = Math.min(total, page * PAGE_SIZE + PAGE_SIZE);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>Alert Queue</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Sorted by priority score, descending
        </p>
      </div>

      <Card className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5">
          {BUCKETS.map((b) => (
            <button
              key={b}
              onClick={() => toggleBucket(b)}
              className="rounded-full px-3 py-1 text-xs font-medium border"
              style={{
                borderColor: "var(--border)",
                background: bucket.includes(b) ? "var(--surface-2)" : "transparent",
                color: bucket.includes(b) ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              {b}
            </button>
          ))}
        </div>
        <select
          multiple
          className="rounded-md border px-2 py-1 text-xs max-w-56"
          style={{ borderColor: "var(--border)", background: "var(--surface-1)", color: "var(--text-secondary)" }}
          value={attackType}
          onChange={(e) => {
            const opts = Array.from(e.target.selectedOptions).map((o) => o.value);
            setAttackType(opts);
          }}
        >
          {(attackTypesQ.data ?? []).map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        {attackType.length > 0 && (
          <button className="text-xs underline" style={{ color: "var(--text-muted)" }} onClick={() => setAttackType([])}>
            clear attack type filter
          </button>
        )}
        <label className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
          <input type="checkbox" checked={campaignOnly} onChange={(e) => setCampaignOnly(e.target.checked)} />
          Correlated campaigns only
        </label>
      </Card>

      {alertsQ.isLoading ? (
        <SkeletonTableCard rows={10} />
      ) : (
      <Card className="p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs uppercase" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              <th className="px-3 py-2 font-medium">Alert</th>
              <th className="px-3 py-2 font-medium">Time</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Attack Type</th>
              <th className="px-3 py-2 font-medium">Confidence</th>
              <th className="px-3 py-2 font-medium">Priority</th>
              <th className="px-3 py-2 font-medium">Campaign</th>
            </tr>
          </thead>
          <tbody>
            {(alertsQ.data?.alerts ?? []).map((a) => (
              <tr
                key={a.alert_id}
                className="border-b last:border-0"
                style={{ borderColor: "var(--gridline)" }}
              >
                <td className="px-3 py-2">
                  <Link to={`/alerts/${a.alert_id}`} className="font-medium hover:underline" style={{ color: "var(--series-1)" }}>
                    {a.alert_id}
                  </Link>
                </td>
                <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                  {new Date(a.timestamp).toLocaleString()}
                </td>
                <td className="px-3 py-2 font-mono text-xs" style={{ color: "var(--text-secondary)" }}>{a.source_ip}</td>
                <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>{a.predicted_class}</td>
                <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  {(a.confidence * 100).toFixed(1)}%
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <BucketBadge bucket={a.priority_bucket} />
                    <span className="tabular-nums text-xs" style={{ color: "var(--text-muted)" }}>
                      {a.priority_score.toFixed(1)}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2 text-xs" style={{ color: "var(--text-secondary)" }}>
                  {a.matched_known_pattern ?? (a.is_correlated_campaign ? "Campaign (no KB match)" : "—")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div
          className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2"
          style={{ borderColor: "var(--border)" }}
        >
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            Showing {rangeStart}-{rangeEnd} of {total} alerts
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-md border px-3 py-1 text-xs font-medium disabled:opacity-40"
              style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
            >
              ← Previous
            </button>
            <span className="text-xs tabular-nums" style={{ color: "var(--text-secondary)" }}>
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded-md border px-3 py-1 text-xs font-medium disabled:opacity-40"
              style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
            >
              Next →
            </button>
          </div>
        </div>
      </Card>
      )}
    </div>
  );
}
