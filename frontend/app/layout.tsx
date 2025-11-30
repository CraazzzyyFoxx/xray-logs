import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Xray Logs Dashboard",
  description: "Live analytics for Xray logs",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-background text-foreground">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <header className="mb-8 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">FastAPI + Next.js + shadcn/ui</p>
              <h1 className="text-3xl font-bold">Xray Logs Analytics</h1>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-muted px-4 py-2 text-sm text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-green-500" /> PostgreSQL
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  )
}
