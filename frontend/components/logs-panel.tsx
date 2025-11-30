"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { fetchLogs, type LogRecord } from "@/lib/api";

interface LogsPanelProps {
  initialItems: LogRecord[];
  initialTotal: number;
}

export function LogsPanel({ initialItems, initialTotal }: LogsPanelProps) {
  const [logs, setLogs] = useState<LogRecord[]>(initialItems);
  const [total, setTotal] = useState<number>(initialTotal);
  const [search, setSearch] = useState("");
  const [protocol, setProtocol] = useState("");
  const [tag, setTag] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetchLogs({ search, protocol, tag, limit: 50 });
      setLogs(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtersApplied = useMemo(() => search || protocol || tag, [search, protocol, tag]);

  return (
    <Card>
      <CardHeader className="space-y-3">
        <CardTitle className="flex items-center justify-between">
          <span>Последние события</span>
          <Badge variant="secondary">{total} записей</Badge>
        </CardTitle>
        <div className="grid gap-3 md:grid-cols-4">
          <Input
            placeholder="Поиск по email, IP, домену"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Input
            placeholder="Протокол (tcp/udp)"
            value={protocol}
            onChange={(e) => setProtocol(e.target.value)}
          />
          <Input
            placeholder="Тег маршрута"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <Button onClick={load} disabled={loading} className="flex-1">
              {loading ? "Загрузка..." : filtersApplied ? "Обновить" : "Показать"}
            </Button>
            {filtersApplied && (
              <Button
                variant="ghost"
                onClick={() => {
                  setSearch("");
                  setProtocol("");
                  setTag("");
                  load();
                }}
              >
                Сбросить
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Время</TableHead>
              <TableHead>Пользователь</TableHead>
              <TableHead>Источник</TableHead>
              <TableHead>Назначение</TableHead>
              <TableHead>Протокол</TableHead>
              <TableHead>Теги</TableHead>
              <TableHead>Действие</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="whitespace-nowrap">{new Date(row.timestamp).toLocaleString("ru-RU")}</TableCell>
                <TableCell>
                  {row.user_id ? (
                    <Link
                      href={`/users/${row.user_id}`}
                      className="text-primary hover:underline"
                    >
                      {row.email || `user #${row.user_id}`}
                    </Link>
                  ) : (
                    row.email || "—"
                  )}
                </TableCell>
                <TableCell>
                  <div className="text-sm font-medium">{row.source_ip}</div>
                  <div className="text-xs text-muted-foreground">порт {row.source_port}</div>
                </TableCell>
                <TableCell>
                  <div className="text-sm font-medium">{row.destination_host}</div>
                  <div className="text-xs text-muted-foreground">порт {row.destination_port ?? "?"}</div>
                </TableCell>
                <TableCell className="uppercase">{row.protocol ?? "n/a"}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {row.inbound_tag && <Badge variant="outline">in: {row.inbound_tag}</Badge>}
                    {row.outbound_tag && <Badge variant="outline">out: {row.outbound_tag}</Badge>}
                  </div>
                </TableCell>
                <TableCell>{row.action || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
