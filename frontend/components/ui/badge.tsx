import * as React from "react"
import { cn } from "@/lib/utils"

type BadgeProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: "default" | "outline" | "success"
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants: Record<NonNullable<BadgeProps["variant"]>, string> = {
    default: "bg-secondary text-secondary-foreground",
    outline: "border border-input text-foreground",
    success: "bg-green-100 text-green-700 border border-green-200",
  }
  return <div className={cn("inline-flex items-center rounded-full px-3 py-1 text-xs", variants[variant], className)} {...props} />
}
