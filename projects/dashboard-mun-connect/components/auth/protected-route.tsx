"use client"

import React, { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "../../lib/auth-context"
import { Loader2 } from "lucide-react"

interface ProtectedRouteProps {
  children: React.ReactNode
  requireProfileComplete?: boolean
  redirectTo?: string
}

export function ProtectedRoute({
  children,
  requireProfileComplete = false,
  redirectTo = "/dashboard/login",
}: ProtectedRouteProps) {
  const { user, isLoading, isProfileComplete, refreshSession } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [redirecting, setRedirecting] = useState(false)
  const [initialCheckDone, setInitialCheckDone] = useState(false)

  useEffect(() => {
    // Trigger a session refresh to ensure we have the latest auth state
    refreshSession().then(() => {
      setInitialCheckDone(true)
    })
  }, [refreshSession])

  useEffect(() => {
    if (!isLoading && initialCheckDone) {
      const shouldRedirect = (
        !user || 
        (requireProfileComplete && !isProfileComplete)
      )

      if (shouldRedirect && !redirecting) {
        setRedirecting(true)
        // Add a small delay to prevent potential race conditions
        setTimeout(() => {
          // Add redirect parameter to return to this page after login
          const currentPath = pathname
          const redirectPath = `${redirectTo}?redirect=${encodeURIComponent(currentPath || '')}`
          router.push(redirectPath)
        }, 100)
      }
    }
  }, [user, isLoading, isProfileComplete, router, redirectTo, redirecting, requireProfileComplete, pathname, initialCheckDone])

  // Show loading state while initial auth check is in progress
  if (isLoading || !initialCheckDone) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
        <div className="flex flex-col items-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-blue-600 font-medium">
            Loading...
          </p>
        </div>
      </div>
    )
  }

  // Show redirecting state if we're in the process of redirecting
  if (redirecting) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
        <div className="flex flex-col items-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-blue-600 font-medium">
            Redirecting...
          </p>
        </div>
      </div>
    )
  }

  // Render children directly - no additional checks needed
  return <>{children}</>
} 