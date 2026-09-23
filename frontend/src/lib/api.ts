
export interface Overview {
  total_alerts: number;
  bucket_counts: { Critical: number; High: number; Medium: number; Low: number };
  correlated_campaigns: number;
  incident_log: { total: number; correlated_campaigns: number; isolated_critical: number };
  knowledge_base: { total_patterns: number; auto_learned: number };
}

export interface AlertSummary {
  alert_id: string;
  timestamp: string;
  source_ip: string;
  destination_ip: string;
  predicted_class: string;
  confidence: number;
  priority_score: number;
  priority_bucket: "Critical" | "High" | "Medium" | "Low";
  is_correlated_campaign: boolean;
  correlation_group_id: string | null;
  matched_known_pattern: string | null;
}

export interface FeatureImpact {
  feature: string;
  shap_value: number;
}

export interface AlertDetail extends AlertSummary {
  row_index: number;
  true_class: string;
  simulated_campaign_id: string | null;
  kill_chain_stages_seen: string | null;
  matched_pattern_similarity: number | null;
  effective_severity_score: number;
  own_severity_label: string;
  top_contributing_features: FeatureImpact[];
}

export interface Analytics {
  alerts_over_time: { timestamp: string; count: number }[];
  attack_type_distribution: { attack_type: string; count: number }[];
  top_sources: { source_ip: string; count: number }[];
  severity_by_attack_type: { attack_type: string; bucket: string; count: number }[];
  pattern_matches: { pattern: string; count: number }[];
}

export interface Incident {
  incident_id: string;
  logged_at: string;
  incident_type: "correlated_campaign" | "isolated_critical";
  alert_ids: string[];
  predicted_classes: string[];
  source_ip: string;
  max_priority_score: number;
  correlation_group_id?: string;
  kill_chain_stages_seen?: string;
  new_pattern_learned?: string | null;
}

export interface KnowledgeBaseEntry {
  name: string;
  description: string;
  typical_severity: string;
  mitre_tactics: string[];
  source?: string;
  learned_at?: string;
}

export interface LiveAnalyzeResult {
  alert_id: string;
  row_index: number;
  timestamp: string;
  source_ip: string;
  destination_ip: string;
  detection: {
    predicted_class: string;
    confidence: number;
    class_probabilities: Record<string, number>;
  };
  correlation: {
    is_correlated_campaign: boolean;
    correlation_group_id: string | null;
    group_size: number;
    kill_chain_stages_seen: string | null;
    matched_known_pattern: string | null;
    matched_pattern_similarity: number | null;
  };
  priority: {
    priority_score: number;
    priority_bucket: "Critical" | "High" | "Medium" | "Low";
    effective_severity_score: number;
    own_severity_label: string;
  };
  explanation: FeatureImpact[];
  escalation: {
    should_escalate: boolean;
    is_novel_pattern: boolean;
    novelty_best_similarity: number;
    novelty_best_match: string | null;
  };
}

const API_BASE = import.meta.env.VITE_API_URL || "";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  overview: () => get<Overview>("/api/overview"),

  alerts: (
    params: {
      bucket?: string[];
      attack_type?: string[];
      campaign_only?: boolean;
      limit?: number;
      offset?: number;
    } = {}
  ) => {
    const qs = new URLSearchParams();
    params.bucket?.forEach((b) => qs.append("bucket", b));
    params.attack_type?.forEach((a) => qs.append("attack_type", a));
    if (params.campaign_only) qs.set("campaign_only", "true");
    qs.set("limit", String(params.limit ?? 50));
    qs.set("offset", String(params.offset ?? 0));
    return get<{ total: number; alerts: AlertSummary[] }>(`/api/alerts?${qs.toString()}`);
  },

  alertDetail: (alertId: string) => get<AlertDetail>(`/api/alerts/${alertId}`),

  attackTypes: () => get<string[]>("/api/alerts/meta/attack-types"),

  analytics: () => get<Analytics>("/api/analytics"),

  incidents: (limit = 100) => get<{ total: number; incidents: Incident[] }>(`/api/incidents?limit=${limit}`),

  knowledgeBase: () => get<KnowledgeBaseEntry[]>("/api/knowledge-base"),

  searchKnowledgeBase: (q: string) =>
    get<{ campaign_name: string; similarity: number; typical_severity: string; mitre_tactics: string[] }[]>(
      `/api/knowledge-base/search?q=${encodeURIComponent(q)}&top_k=5`
    ),

  liveAnalyze: async (body: { row_index?: number; source_ip?: string; commit?: boolean }) => {
    const res = await fetch(apiUrl("/api/live/analyze"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`live/analyze -> ${res.status}`);
    return res.json() as Promise<LiveAnalyzeResult>;
  },
};

export const BUCKET_COLOR: Record<string, string> = {
  Critical: "var(--status-critical)",
  High: "var(--status-serious)",
  Medium: "var(--status-warning)",
  Low: "var(--status-good)",
};

export const SERIES_COLORS = [
  "var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)",
  "var(--series-5)", "var(--series-6)", "var(--series-7)", "var(--series-8)",
];
