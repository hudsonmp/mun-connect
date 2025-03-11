"use client"

import React, { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "../../lib/auth-context"
import { Loader2 } from "lucide-react"

// Debug flag
const DEBUG_AUTH = true

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
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    // Trigger a session refresh to ensure we have the latest auth state
    const initializeAuth = async () => {
      try {
        if (DEBUG_AUTH) {
          console.log('Protected Route - Initializing auth:')
          console.log('- Current path:', pathname)
          console.log('- User:', user?.id || 'none')
          console.log('- Loading:', isLoading)
          console.log('- Profile complete:', isProfileComplete)
          console.log('- Retry count:', retryCount)
        }

        await refreshSession()
        setInitialCheckDone(true)
      } catch (error) {
        console.error('Error refreshing session:', error)
        
        // Retry up to 3 times with exponential backoff
        if (retryCount < 3) {
          const delay = Math.pow(2, retryCount) * 1000
          setTimeout(() => {
            setRetryCount(prev => prev + 1)
          }, delay)
        } else {
          // After 3 retries, mark as done and let the redirect logic handle it
          setInitialCheckDone(true)
        }
      }
    }

    if (!initialCheckDone) {
      initializeAuth()
    }
  }, [refreshSession, retryCount, pathname, user?.id, isLoading, isProfileComplete])

  useEffect(() => {
    if (!isLoading && initialCheckDone) {
      const shouldRedirect = !user || (requireProfileComplete && !isProfileComplete)

      if (DEBUG_AUTH) {
        console.log('Protected Route - Checking redirect:')
        console.log('- Should redirect:', shouldRedirect)
        console.log('- User:', user?.id || 'none')
        console.log('- Profile complete:', isProfileComplete)
        console.log('- Current path:', pathname)
      }

      if (shouldRedirect && !redirecting) {
        setRedirecting(true)

        // Add a small delay to prevent potential race conditions
        setTimeout(() => {
          // Add redirect parameter to return to this page after login
          const currentPath = pathname
          const redirectPath = `${redirectTo}?redirect=${encodeURIComponent(currentPath || '')}`

          if (DEBUG_AUTH) {
            console.log('Protected Route - Redirecting:')
            console.log('- From:', currentPath)
            console.log('- To:', redirectPath)
          }

          // Use window.location for a full page reload to ensure clean state
          window.location.href = redirectPath
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
            Loading MUN Connect...
          </p>
          {retryCount > 0 && (
            <p className="text-sm text-blue-500 mt-2">
              Retrying connection ({retryCount}/3)...
            </p>
          )}
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
            Redirecting to login...
          </p>
        </div>
      </div>
    )
  }

  // Render children directly - no additional checks needed
  return <>{children}</>
} 