"use client"

import { ReactNode } from "react"
import { AuthProvider } from "../../lib/auth-context"
import { Toaster } from "../ui/toaster"

interface ClientLayoutProps {
  children: ReactNode
}

export function ClientLayout({ children }: ClientLayoutProps) {
  return (
    <AuthProvider>
      {children}
      <Toaster />
    </AuthProvider>
  )
} 