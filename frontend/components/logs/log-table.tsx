"use client"

import { useMemo } from "react"
import type { LogRecord } from "@/types/log"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function LogsTable({ items }: { items: LogRecord[] }) {
  const rows = useMemo(() => items, [items])

  return (
    <div className="overflow-hidden rounded-lg border">
      <Table className="min-w-full">
        <TableHeader>
          <TableRow>
            <TableHead>Время</TableHead>
            <TableHead>Источник</TableHead>
            <TableHead>Назначение</TableHead>
            <TableHead>Протокол</TableHead>
            <TableHead>Теги</TableHead>
            <TableHead>Почта</TableHead>
            <TableHead>Действие</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((log) => (
            <TableRow key={log.id}>
              <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                {new Date(log.timestamp).toLocaleString("ru-RU")}
              </TableCell>
              <TableCell className="text-sm">
                <div className="font-medium">{log.source_ip}</div>
                <div className="text-xs text-muted-foreground">порт {log.source_port ?? "-"}</div>
              </TableCell>
              <TableCell className="text-sm">
                <div className="font-medium">{log.destination_host ?? "—"}</div>
                <div className="text-xs text-muted-foreground">порт {log.destination_port ?? "-"}</div>
              </TableCell>
              <TableCell>
                <Badge className="uppercase">{log.protocol}</Badge>
              </TableCell>
              <TableCell className="space-x-2">
                {log.inbound_tag ? <Badge variant="outline">in: {log.inbound_tag}</Badge> : null}
                {log.outbound_tag ? <Badge variant="outline">out: {log.outbound_tag}</Badge> : null}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">{log.email ?? "—"}</TableCell>
              <TableCell>
                <Badge variant={log.action === "block" ? "outline" : "success"}>{log.action ?? "allow"}</Badge>
              </TableCell>
            </TableRow>
          ))}
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                Данных по текущему фильтру нет
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  )
}
