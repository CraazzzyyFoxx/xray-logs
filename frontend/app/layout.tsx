import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Xray Logs Dashboard",
  description: "Analytics for Xray logs powered by FastAPI and PostgreSQL",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased bg-muted/30">
        <div className="mx-auto max-w-6xl p-6 space-y-6">{children}</div>
      </body>
    </html>
  );
}
