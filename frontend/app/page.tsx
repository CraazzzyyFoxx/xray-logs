"use client"

import { useEffect, useMemo, useState } from "react"
import { LogsTable } from "@/components/logs/log-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { fetchLogs, fetchStats } from "@/lib/api"
import type { LogRecord, LogStats } from "@/types/log"
import { RefreshCw, Search } from "lucide-react"

const PAGE_LIMIT = 25

export default function HomePage() {
  const [logs, setLogs] = useState<LogRecord[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<LogStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({ search: "", protocol: "", tag: "" })
  const [page, setPage] = useState(0)

  const pageCount = useMemo(() => Math.ceil(total / PAGE_LIMIT), [total])

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((err) => console.error(err))
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchLogs({
      search: filters.search || undefined,
      protocol: filters.protocol || undefined,
      tag: filters.tag || undefined,
      limit: PAGE_LIMIT,
      offset: page * PAGE_LIMIT,
    })
      .then((res) => {
        setLogs(res.items)
        setTotal(res.total)
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }, [filters, page])

  const resetFilters = () => {
    setFilters({ search: "", protocol: "", tag: "" })
    setPage(0)
  }

  const protocolOptions = stats?.available_protocols ?? []
  const tagOptions = stats?.available_tags ?? []

  return (
    <main className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Всего логов</CardDescription>
            <CardTitle className="text-3xl">{stats?.total ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Уникальные пользователи</CardDescription>
            <CardTitle className="text-3xl">{stats?.unique_users ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Протоколы</CardDescription>
            <CardContent className="flex flex-wrap gap-2 p-0 pt-2">
              {protocolOptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">Нет данных</p>
              ) : (
                protocolOptions.map((proto) => (
                  <Badge key={proto} variant="outline" className="uppercase">
                    {proto}
                  </Badge>
                ))
              )}
            </CardContent>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Теги</CardDescription>
            <CardContent className="flex flex-wrap gap-2 p-0 pt-2">
              {tagOptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">Нет данных</p>
              ) : (
                tagOptions.map((tag) => (
                  <Badge key={tag} variant="outline">
                    {tag}
                  </Badge>
                ))
              )}
            </CardContent>
          </CardHeader>
        </Card>
      </section>

      <Card>
        <CardHeader className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-full md:w-1/3">
              <label className="text-xs uppercase text-muted-foreground">Поиск</label>
              <div className="relative mt-1">
                <Search className="absolute left-2 top-2 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-8"
                  placeholder="Домен, email или IP"
                  value={filters.search}
                  onChange={(e) => {
                    setFilters((prev) => ({ ...prev, search: e.target.value }))
                    setPage(0)
                  }}
                />
              </div>
            </div>
            <div className="w-full md:w-1/4">
              <label className="text-xs uppercase text-muted-foreground">Протокол</label>
              <Select
                value={filters.protocol}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, protocol: e.target.value }))
                  setPage(0)
                }}
              >
                <option value="">Все</option>
                {protocolOptions.map((proto) => (
                  <option key={proto} value={proto}>
                    {proto.toUpperCase()}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-full md:w-1/4">
              <label className="text-xs uppercase text-muted-foreground">Тег</label>
              <Select
                value={filters.tag}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, tag: e.target.value }))
                  setPage(0)
                }}
              >
                <option value="">Любой</option>
                {tagOptions.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
              </Select>
            </div>
            <Button variant="outline" onClick={resetFilters} className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4" /> Сбросить
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? <p className="text-sm text-muted-foreground">Загрузка...</p> : null}
          <LogsTable items={logs} />
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div>
              Показано {logs.length} из {total}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => setPage((p) => Math.max(p - 1, 0))}
                disabled={page === 0}
              >
                Предыдущая
              </Button>
              <div>
                Страница {page + 1} / {Math.max(pageCount, 1)}
              </div>
              <Button
                variant="outline"
                onClick={() => setPage((p) => (p + 1 < pageCount ? p + 1 : p))}
                disabled={page + 1 >= pageCount}
              >
                Следующая
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
