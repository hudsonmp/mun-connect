"use client"

import { Loader2 } from "lucide-react"
import { cn } from "../../lib/utils"

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg"
  className?: string
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-8 w-8",
  lg: "h-12 w-12",
}

export function LoadingSpinner({ size = "md", className }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center">
      <Loader2 
        className={cn(
          "animate-spin text-blue-600",
          sizeClasses[size],
          className
        )} 
      />
      {size === "lg" && (
        <p className="text-blue-600 font-medium mt-4">
          Loading MUN Connect...
        </p>
      )}
    </div>
  )
} 