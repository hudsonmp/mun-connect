"use client"

import { ReactNode, useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "../../lib/auth-context"
import { LoadingSpinner } from "../ui/loading-spinner"

interface ProtectedRouteProps {
  children: ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!isLoading && !user) {
      const returnUrl = encodeURIComponent(pathname)
      router.push(`/dashboard/login?redirect=${returnUrl}`)
      return
    }

    // If user exists but doesn't have a username, redirect to profile setup
    // except if they're already on the profile setup page
    if (!isLoading && user && !user.username && pathname !== '/dashboard/profile-setup') {
      router.push('/dashboard/profile-setup')
      return
    }
  }, [user, isLoading, router, pathname])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  return <>{children}</>
} 