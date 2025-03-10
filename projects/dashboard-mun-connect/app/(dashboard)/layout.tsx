"use client"

import React from "react"
import { AuthProvider } from "../../lib/auth-context"
import { Toaster } from "../../components/ui/toaster"

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <AuthProvider>
      {children}
      <Toaster />
    </AuthProvider>
  )
} 