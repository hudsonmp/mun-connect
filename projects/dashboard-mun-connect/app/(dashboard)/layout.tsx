"use client"

import React from "react"
import { usePathname } from "next/navigation"
import { DashboardSidebar } from "../../components/dashboard/dashboard-sidebar"
import { DashboardHeader } from "../../components/dashboard/dashboard-header"
import { ProtectedRoute } from "../../components/auth/protected-route"
import { Toaster } from "../../components/ui/toaster"

// Base path from next.config
const BASE_PATH = '/dashboard'

export default function DashboardGroupLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const pathname = usePathname()
  
  // Debug path for troubleshooting
  if (typeof window !== 'undefined') {
    console.log('Current pathname in (dashboard) layout:', pathname)
  }
  
  return (
    <ProtectedRoute>
      <div className="min-h-screen flex flex-col">
        <DashboardHeader />
        <div className="flex-1 flex">
          <DashboardSidebar />
          <main className="flex-1 transition-all duration-300 ease-in-out ml-16 dashboard-main p-6 bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
            {children}
          </main>
        </div>
      </div>
      <Toaster />
    </ProtectedRoute>
  )
} 