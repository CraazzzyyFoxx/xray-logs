import type { LogRecord, LogStats, PaginatedLogs } from "@/types/log"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function buildQuery(params: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === "") return
    searchParams.set(key, String(value))
  })
  return searchParams.toString()
}

export async function fetchLogs({
  search,
  protocol,
  tag,
  limit,
  offset,
}: {
  search?: string
  protocol?: string
  tag?: string
  limit?: number
  offset?: number
}): Promise<PaginatedLogs> {
  const query = buildQuery({ search, protocol, tag, limit, offset })
  const res = await fetch(`${API_URL}/api/logs${query ? `?${query}` : ""}`)
  if (!res.ok) {
    throw new Error(`Failed to load logs: ${res.statusText}`)
  }
  return (await res.json()) as PaginatedLogs
}

export async function fetchStats(): Promise<LogStats> {
  const res = await fetch(`${API_URL}/api/logs/stats`)
  if (!res.ok) {
    throw new Error(`Failed to load stats: ${res.statusText}`)
  }
  return (await res.json()) as LogStats
}
