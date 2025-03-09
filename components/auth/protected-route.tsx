"use client"

import React, { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

interface ProtectedRouteProps {
  children: React.ReactNode
  requireProfileComplete?: boolean
  redirectTo?: string
}

export function ProtectedRoute({
  children,
  requireProfileComplete = false,
  redirectTo = "/login",
}: ProtectedRouteProps) {
  const { user, isLoading, isProfileComplete, refreshSession } = useAuth()
  const router = useRouter()
  const [redirecting, setRedirecting] = useState(false)

  useEffect(() => {
    // Trigger a session refresh to ensure we have the latest auth state
    refreshSession()
  }, [refreshSession])

  useEffect(() => {
    if (!isLoading) {
      const shouldRedirect = (
        !user || 
        (requireProfileComplete && !isProfileComplete)
      )

      if (shouldRedirect && !redirecting) {
        setRedirecting(true)
        // Add a small delay to prevent potential race conditions
        setTimeout(() => {
          // Add redirect parameter to return to this page after login
          const currentPath = window.location.pathname
          const redirectPath = `${redirectTo}?redirect=${encodeURIComponent(currentPath)}`
          router.push(redirectPath)
        }, 100)
      }
    }
  }, [user, isLoading, isProfileComplete, router, redirectTo, redirecting, requireProfileComplete])

  if (isLoading || redirecting) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
        <div className="flex flex-col items-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-blue-600 font-medium">
            {redirecting ? "Redirecting..." : "Loading..."}
          </p>
        </div>
      </div>
    )
  }

  // If not authenticated or profile not complete (when required)
  if (!user || (requireProfileComplete && !isProfileComplete)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
        <div className="flex flex-col items-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-blue-600 font-medium">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
} 