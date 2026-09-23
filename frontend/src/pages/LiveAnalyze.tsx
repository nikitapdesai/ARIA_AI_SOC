import { useState, useRef, useEffect } from "react";
import { api, apiUrl, type LiveAnalyzeResult } from "../lib/api";
import { BucketBadge, Card, SectionTitle } from "../components/Badge";
import ShapBarChart from "../components/charts/ShapBarChart";

export default function LiveAnalyze() {
  const [sourceIp, setSourceIp] = useState("");
  const [commit, setCommit] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LiveAnalyzeResult | null>(null);

  const [streaming, setStreaming] = useState(false);
  const [feed, setFeed] = useState<LiveAnalyzeResult[]>([]);
  const esRef = useRef<EventSource | null>(null);

  async function runAnalysis() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.liveAnalyze({ source_ip: sourceIp || undefined, commit });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function toggleStream() {
    if (streaming) {
      esRef.current?.close();
      esRef.current = null;
      setStreaming(false);
      return;
    }
    setFeed([]);
    const es = new EventSource(apiUrl("/api/live/stream"));
    es.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (data.error) return;
      setFeed((prev) => [data as LiveAnalyzeResult, ...prev].slice(0, 25));
    };
    es.onerror = () => {
      es.close();
      setStreaming(false);
    };
    esRef.current = es;
    setStreaming(true);
  }

  useEffect(() => () => esRef.current?.close(), []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>Live Analyze</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Runs a real network flow through Detection → Correlation → Priority-Explainer → Escalation, live —
          not a replay of pre-computed data.
        </p>
      </div>

      <Card className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
            Source IP (optional — reuse an existing one to test campaign correlation)
          </label>
          <input
            className="rounded-md border px-2 py-1.5 text-sm font-mono"
            style={{ borderColor: "var(--border)", background: "var(--surface-2)", color: "var(--text-primary)" }}
            placeholder="e.g. 10.0.80.58, or leave blank for a fresh source"
            value={sourceIp}
            onChange={(e) => setSourceIp(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-1.5 pb-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
          <input type="checkbox" checked={commit} onChange={(e) => setCommit(e.target.checked)} />
          Persist (log incident / grow knowledge base if it qualifies)
        </label>
        <button
          onClick={runAnalysis}
          disabled={loading}
          className="rounded-md px-4 py-1.5 text-sm font-medium disabled:opacity-50"
          style={{ background: "var(--series-1)", color: "white" }}
        >
          {loading ? "Analyzing…" : "Analyze a New Flow"}
        </button>
      </Card>

      {error && <div className="text-sm" style={{ color: "var(--status-critical)" }}>{error}</div>}

      {result && <ResultTrace result={result} />}

      <Card>
        <div className="flex items-center justify-between">
          <SectionTitle>Live Feed (server-sent, one new flow every ~3s)</SectionTitle>
          <button
            onClick={toggleStream}
            className="rounded-md border px-3 py-1 text-xs font-medium"
            style={{ borderColor: "var(--border)", color: streaming ? "var(--status-critical)" : "var(--text-primary)" }}
          >
            {streaming ? "Stop" : "Start"}
          </button>
        </div>
        <div className="mt-2 flex max-h-80 flex-col gap-1 overflow-y-auto font-mono text-xs">
          {feed.length === 0 && (
            <span style={{ color: "var(--text-muted)" }}>
              {streaming ? "Waiting for the first flow…" : "Press Start to stream live-analyzed flows."}
            </span>
          )}
          {feed.map((r) => (
            <div key={r.alert_id} className="flex items-center gap-2 border-b py-1" style={{ borderColor: "var(--gridline)" }}>
              <BucketBadge bucket={r.priority.priority_bucket} />
              <span style={{ color: "var(--text-secondary)" }}>{r.alert_id}</span>
              <span style={{ color: "var(--text-muted)" }}>src={r.source_ip}</span>
              <span style={{ color: "var(--text-primary)" }}>{r.detection.predicted_class}</span>
              <span style={{ color: "var(--text-muted)" }}>conf={(r.detection.confidence * 100).toFixed(1)}%</span>
              {r.correlation.is_correlated_campaign && (
                <span style={{ color: "var(--status-serious)" }}>
                  campaign{r.correlation.matched_known_pattern ? `: ${r.correlation.matched_known_pattern}` : ""}
                </span>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ResultTrace({ result }: { result: LiveAnalyzeResult }) {
  const topClasses = Object.entries(result.detection.class_probabilities)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
      <Card>
        <SectionTitle>1 · Detection Agent</SectionTitle>
        <div className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{result.detection.predicted_class}</div>
        <div className="text-sm tabular-nums" style={{ color: "var(--text-secondary)" }}>
          {(result.detection.confidence * 100).toFixed(2)}% confidence
        </div>
        <div className="mt-3 flex flex-col gap-1 text-xs">
          {topClasses.map(([cls, p]) => (
            <div key={cls} className="flex justify-between" style={{ color: "var(--text-muted)" }}>
              <span>{cls}</span>
              <span className="tabular-nums">{(p * 100).toFixed(2)}%</span>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle>2 · Correlation Agent</SectionTitle>
        {result.correlation.is_correlated_campaign ? (
          <>
            <div className="text-sm font-medium" style={{ color: "var(--status-serious)" }}>Part of a campaign</div>
            <div className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
              Group {result.correlation.correlation_group_id} · size {result.correlation.group_size}
            </div>
            {result.correlation.kill_chain_stages_seen && (
              <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                Stages: {result.correlation.kill_chain_stages_seen}
              </div>
            )}
            {result.correlation.matched_known_pattern && (
              <div className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
                Matched: <span className="font-medium">{result.correlation.matched_known_pattern}</span>
                {" "}({(result.correlation.matched_pattern_similarity! * 100).toFixed(1)}% similarity)
              </div>
            )}
          </>
        ) : (
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            Isolated — no correlated campaign detected for this source.
          </div>
        )}
      </Card>

      <Card>
        <SectionTitle>3 · Priority-Explainer Agent</SectionTitle>
        <div className="flex items-center gap-2">
          <BucketBadge bucket={result.priority.priority_bucket} />
          <span className="text-sm tabular-nums" style={{ color: "var(--text-secondary)" }}>
            {result.priority.priority_score.toFixed(1)} / 100
          </span>
        </div>
        <div className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          Severity: {result.priority.own_severity_label} (effective {result.priority.effective_severity_score.toFixed(2)})
        </div>
        <div className="mt-3">
          <ShapBarChart features={result.explanation.slice(0, 4)} />
        </div>
      </Card>

      <Card>
        <SectionTitle>4 · Escalation Agent</SectionTitle>
        <div className="text-sm font-medium" style={{ color: result.escalation.should_escalate ? "var(--status-critical)" : "var(--text-muted)" }}>
          {result.escalation.should_escalate ? "Would escalate" : "No escalation"}
        </div>
        <div className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          {result.escalation.is_novel_pattern
            ? "Novel pattern — would be added to the knowledge base"
            : `Matches known pattern "${result.escalation.novelty_best_match}"`}
        </div>
        <div className="mt-1 text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
          Best similarity to KB: {(result.escalation.novelty_best_similarity * 100).toFixed(1)}%
        </div>
      </Card>
    </div>
  );
}
