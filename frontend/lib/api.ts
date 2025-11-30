const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_BASE = "http://localhost:8000";

export interface LogRecord {
  id: number;
  timestamp: string;
  user_id: number | null;
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

export interface SessionSummary {
  user_id: number;
  email: string | null;
  session_group_id: number;
  started_at: string;
  ended_at: string;
  events: number;
}

export interface SessionEvent {
  id: number;
  email: string | null;
  event_time: string;
  source_ip: string;
  source_port: number;
  protocol: string | null;
  destination: string | null;
  destination_port: number | null;
  inbound_tag: string | null;
  outbound_tag: string | null;
  action: string | null;
  session_group_id: number;
}

export interface SiteVisit {
  site: string;
  first_visit: string;
  last_visit: string;
  hits_count: number;
}

export interface UserProfileResponse {
  user_id: number;
  email: string | null;
  sessions: SessionSummary[];
  top_sites: SiteVisit[];
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

export async function fetchUserProfile(userId: string | number): Promise<UserProfileResponse> {
  const res = await fetch(`${API_BASE}/api/users/${userId}/profile`, { next: { revalidate: 0 } });
  if (!res.ok) {
    throw new Error("Failed to fetch user profile");
  }
  return res.json();
}

export async function fetchSessionEvents(
  userId: string | number,
  sessionGroupId: string | number,
): Promise<SessionEvent[]> {
  const res = await fetch(
    `${API_BASE}/api/users/${userId}/sessions/${sessionGroupId}`,
    { next: { revalidate: 0 } },
  );
  if (!res.ok) {
    throw new Error("Failed to fetch session events");
  }
  return res.json();
}
