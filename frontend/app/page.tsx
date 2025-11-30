import { LogsPanel } from "@/components/logs-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fetchLogs, fetchStats } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [stats, logs] = await Promise.all([
    fetchStats(),
    fetchLogs({ limit: 25 }),
  ]);

  return (
    <main className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-muted-foreground">
          Xray · FastAPI · PostgreSQL · Next.js
        </p>
        <h1 className="text-3xl font-bold">Мониторинг логов</h1>
        <p className="text-muted-foreground max-w-3xl">
          API читает данные напрямую из PostgreSQL, а интерфейс собран на Next.js с компонентами shadcn/ui.
          Используйте фильтры, чтобы быстро находить запросы по email, IP или маршрутизирующим тегам.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Всего событий" value={stats.total.toLocaleString()} />
        <StatCard title="Уникальных пользователей" value={stats.unique_users.toLocaleString()} />
        <StatCard title="Популярные протоколы" value={Object.keys(stats.protocols).slice(0, 3).join(", ") || "—"} />
        <StatCard title="Топ тегов" value={Object.keys(stats.tags).slice(0, 3).join(", ") || "—"} />
      </section>

      <LogsPanel initialItems={logs.items} initialTotal={logs.total} />
    </main>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold flex items-center gap-2">
          {value || "—"}
          <Badge variant="secondary" className="text-xs font-normal">live</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
