import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import { Card, SectionTitle } from "../components/Badge";
import { SkeletonListCard } from "../components/skeletons/Skeleton";

export default function KnowledgeBase() {
  const kbQ = useQuery({ queryKey: ["kb"], queryFn: api.knowledgeBase });
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<Awaited<ReturnType<typeof api.searchKnowledgeBase>> | null>(null);

  async function runSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      setResults(await api.searchKnowledgeBase(query));
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>Knowledge Base</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Seed patterns plus campaigns auto-learned by the Escalation Agent's novelty-detection loop
        </p>
      </div>

      <Card>
        <SectionTitle>Semantic Search</SectionTitle>
        <form onSubmit={runSearch} className="flex gap-2">
          <input
            className="flex-1 rounded-md border px-2 py-1.5 text-sm"
            style={{ borderColor: "var(--border)", background: "var(--surface-2)", color: "var(--text-primary)" }}
            placeholder="Describe an attack sequence, e.g. 'port scan followed by brute force'"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="submit"
            disabled={searching}
            className="rounded-md px-4 py-1.5 text-sm font-medium disabled:opacity-50"
            style={{ background: "var(--series-1)", color: "white" }}
          >
            {searching ? "Searching…" : "Search"}
          </button>
        </form>
        {results && (
          <div className="mt-3 flex flex-col gap-2">
            {results.map((r) => (
              <div key={r.campaign_name} className="flex items-center justify-between text-sm">
                <span style={{ color: "var(--text-primary)" }}>{r.campaign_name}</span>
                <span className="tabular-nums text-xs" style={{ color: "var(--text-muted)" }}>
                  {(r.similarity * 100).toFixed(1)}% similar · {r.typical_severity}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {kbQ.isLoading ? (
        <SkeletonListCard rows={5} />
      ) : (
      <div className="flex flex-col gap-2">
        {(kbQ.data ?? []).map((entry, i) => {
          const isLearned = entry.source === "escalation_agent_auto_learned";
          return (
            <Card key={`${entry.name}-${i}`} className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="font-medium" style={{ color: "var(--text-primary)" }}>{entry.name}</span>
                {isLearned && (
                  <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: "var(--surface-2)", color: "var(--series-3)" }}>
                    AUTO-LEARNED
                  </span>
                )}
                <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>{entry.typical_severity}</span>
              </div>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{entry.description}</p>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                MITRE tactics: {entry.mitre_tactics?.join(", ") || "—"}
                {isLearned && entry.learned_at && <> · learned {new Date(entry.learned_at).toLocaleString()}</>}
              </div>
            </Card>
          );
        })}
      </div>
      )}
    </div>
  );
}
