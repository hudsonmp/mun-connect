"use client"

import React from "react"
import { usePathname } from "next/navigation"
import { DashboardHeader } from "../../components/dashboard/dashboard-header"
import { AuthProvider } from "../../lib/auth-context"
import { Toaster } from "../../components/ui/toaster"
  
// Base path from next.config
const BASE_PATH = '/dashboard'

export default function DashboardRootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const pathname = usePathname()
  
  // Debug path for troubleshooting
  if (typeof window !== 'undefined') {
    console.log('Current pathname in dashboard/layout:', pathname)
  }
  
  // Don't apply protection to login and register pages
  const isAuthRoute = pathname === '/dashboard/login' || 
                     pathname === '/dashboard/register' || 
                     pathname === '/dashboard/profile-setup' ||
                     pathname === '/dashboard/forgot-password' ||
                     pathname === '/dashboard/reset-password'
  
  return (
    <AuthProvider>
      {isAuthRoute ? (
        <>
          <DashboardHeader />
          <main className="min-h-[calc(100vh-64px)]">
            {children}
          </main>
        </>
      ) : (
        <>{children}</>
      )}
      <Toaster />
    </AuthProvider>
  )
}

