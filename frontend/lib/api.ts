const API_BASE = "http://localhost:8000";

export interface LogRecord {
  id: number;
  timestamp: string;
  source_ip: string;
  source_port: number;
  destination_host: string;
  destination_port: number | null;
  protocol: string | null;
  action: string | null;
  inbound_tag: string | null;
  outbound_tag: string | null;
  email: string | null;
}

export interface LogsResponse {
  total: number;
  items: LogRecord[];
}

export interface LogStats {
  total: number;
  unique_users: number;
  protocols: Record<string, number>;
  tags: Record<string, number>;
}

export async function fetchLogs(params: {
  search?: string;
  protocol?: string;
  tag?: string;
  limit?: number;
  offset?: number;
}): Promise<LogsResponse> {
  const url = new URL("/api/logs", API_BASE);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.append(key, String(value));
    }
  });

  const res = await fetch(url.toString(), { next: { revalidate: 0 } });
  if (!res.ok) {
    throw new Error(`Failed to fetch logs: ${res.status}`);
  }
  return res.json();
}

export async function fetchStats(): Promise<LogStats> {
  const res = await fetch(`${API_BASE}/api/logs/stats`, { next: { revalidate: 0 } });
  if (!res.ok) {
    throw new Error("Failed to fetch stats");
  }
  return res.json();
}
