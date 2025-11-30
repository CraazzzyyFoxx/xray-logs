export type LogRecord = {
  id: number
  timestamp: string
  source_ip: string
  source_port?: number | null
  destination_host?: string | null
  destination_port?: number | null
  protocol: string
  action?: string | null
  inbound_tag?: string | null
  outbound_tag?: string | null
  email?: string | null
}

export type PaginatedLogs = {
  total: number
  items: LogRecord[]
}

export type LogStats = {
  total: number
  protocol_counts: Record<string, number>
  tag_counts: Record<string, number>
  unique_users: number
  available_protocols: string[]
  available_tags: string[]
}
