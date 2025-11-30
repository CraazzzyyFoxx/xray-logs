import { notFound } from "next/navigation";

import { UserSessions } from "@/components/user-sessions";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fetchUserProfile } from "@/lib/api";

export default async function UserProfilePage({ params }: { params: { id: string } }) {
  const profile = await fetchUserProfile(params.id).catch(() => null);

  if (!profile) {
    notFound();
  }

  const latest = profile.sessions[0];

  return (
    <main className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-muted-foreground">Профиль пользователя</p>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold">{profile.email || `user #${profile.user_id}`}</h1>
          <Badge variant="secondary">ID: {profile.user_id}</Badge>
          <Badge variant="outline">Последние 3 дня</Badge>
        </div>
        <p className="text-muted-foreground max-w-3xl">
          Сессии формируются при разрыве активности более 10 минут. Выберите сессию, чтобы посмотреть события.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <StatCard title="Сессий" value={profile.sessions.length} />
        <StatCard title="Популярных сайтов" value={profile.top_sites.length} />
        <StatCard title="Последняя активность" value={latest ? new Date(latest.ended_at).toLocaleString("ru-RU") : "—"} />
      </section>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <UserSessions userId={profile.user_id} sessions={profile.sessions} />
        </div>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Часто посещаемые адреса</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Адрес</TableHead>
                  <TableHead>Последняя сессия</TableHead>
                  <TableHead className="text-right">Запросов</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {profile.top_sites.map((site) => (
                  <TableRow key={site.site}>
                    <TableCell className="font-medium">{site.site}</TableCell>
                    <TableCell>{new Date(site.last_visit).toLocaleString("ru-RU")}</TableCell>
                    <TableCell className="text-right">{site.hits_count}</TableCell>
                  </TableRow>
                ))}
                {profile.top_sites.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground">
                      Нет данных о посещениях
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

function StatCard({ title, value }: { title: string; value: string | number }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">{value || "—"}</div>
      </CardContent>
    </Card>
  );
}
