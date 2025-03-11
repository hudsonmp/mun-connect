"use client"

import React from "react"
import { usePathname } from "next/navigation"
import { DashboardSidebar } from "../../components/dashboard/dashboard-sidebar"
import { DashboardHeader } from "../../components/dashboard/dashboard-header"
import { ProtectedRoute } from "../../components/auth/protected-route"
import { Toaster } from "../../components/ui/toaster"

// Debug flag
const DEBUG_AUTH = true

// Helper to check if a path is an auth route
const isAuthPath = (path: string) => {
  const authPaths = ['/login', '/register', '/auth/callback', '/profile-setup']
  return authPaths.some(authPath => path.endsWith(authPath))
}

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const pathname = usePathname()
  
  if (DEBUG_AUTH) {
    console.log('Dashboard Layout rendering for path:', pathname)
    console.log('Is auth route:', isAuthPath(pathname))
  }
  
  // Don't apply dashboard layout to auth routes
  if (isAuthPath(pathname)) {
    return <>{children}</>
  }
  
  // Apply protected route wrapper and dashboard layout to non-auth routes
  return (
    <ProtectedRoute requireProfileComplete={true}>
      <div className="min-h-screen flex flex-col">
        <DashboardHeader />
        <div className="flex-1 flex">
          <DashboardSidebar />
          <main className="flex-1 transition-all duration-300 ease-in-out ml-16 dashboard-main p-6 bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
            {children}
          </main>
        </div>
      </div>
    </ProtectedRoute>
  )
} 