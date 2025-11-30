"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchSessionEvents, type SessionEvent, type SessionSummary } from "@/lib/api";

interface Props {
  userId: number;
  sessions: SessionSummary[];
}

export function UserSessions({ userId, sessions }: Props) {
  const [selected, setSelected] = useState<SessionSummary | null>(sessions[0] ?? null);
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = async (sessionGroupId: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSessionEvents(userId, sessionGroupId);
      setEvents(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить события");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selected) {
      loadEvents(selected.session_group_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.session_group_id]);

  const durationMinutes = useMemo(() => {
    if (!selected) return null;
    const start = new Date(selected.started_at).getTime();
    const end = new Date(selected.ended_at).getTime();
    return Math.max(0, Math.round((end - start) / 60000));
  }, [selected]);

  return (
    <Card>
      <CardHeader className="space-y-2">
        <CardTitle className="flex items-center justify-between">
          <span>Сессии</span>
          {selected && <Badge variant="secondary">#{selected.session_group_id}</Badge>}
        </CardTitle>
        <div className="flex flex-wrap gap-2">
          {sessions.map((s) => (
            <Badge
              key={s.session_group_id}
              variant={selected?.session_group_id === s.session_group_id ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => setSelected(s)}
            >
              {new Date(s.started_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
              <span className="mx-1">→</span>
              {new Date(s.ended_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
              <span className="ml-2 text-xs opacity-80">{s.events} событий</span>
            </Badge>
          ))}
          {sessions.length === 0 && <span className="text-muted-foreground text-sm">Нет сессий за 3 дня</span>}
        </div>
        {selected && (
          <p className="text-sm text-muted-foreground">
            {new Date(selected.started_at).toLocaleString("ru-RU")} · длительность ~{durationMinutes ?? "?"} мин · {selected.events} событий
          </p>
        )}
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {loading && <div className="text-sm text-muted-foreground">Загрузка событий...</div>}
        {error && <div className="text-sm text-destructive">{error}</div>}
        {!loading && !error && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Время</TableHead>
                <TableHead>Источник</TableHead>
                <TableHead>Назначение</TableHead>
                <TableHead>Протокол</TableHead>
                <TableHead>Теги</TableHead>
                <TableHead>Действие</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="whitespace-nowrap">{new Date(event.event_time).toLocaleString("ru-RU")}</TableCell>
                  <TableCell>
                    <div className="text-sm font-medium">{event.source_ip}</div>
                    <div className="text-xs text-muted-foreground">порт {event.source_port}</div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm font-medium">{event.destination}</div>
                    <div className="text-xs text-muted-foreground">порт {event.destination_port ?? "?"}</div>
                  </TableCell>
                  <TableCell className="uppercase">{event.protocol ?? "n/a"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {event.inbound_tag && <Badge variant="outline">in: {event.inbound_tag}</Badge>}
                      {event.outbound_tag && <Badge variant="outline">out: {event.outbound_tag}</Badge>}
                    </div>
                  </TableCell>
                  <TableCell>{event.action || "—"}</TableCell>
                </TableRow>
              ))}
              {events.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    Нет событий для выбранной сессии
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
