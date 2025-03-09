"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { DashboardSidebar } from "@/components/dashboard/dashboard-sidebar"
import { DashboardHeader } from "@/components/dashboard/dashboard-header"
import { Loader2 } from "lucide-react"

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const { user, isLoading, isProfileComplete } = useAuth()
  const router = useRouter()
  const [redirecting, setRedirecting] = useState(false)

  // Redirect to login if not authenticated or to profile setup if profile is not complete
  useEffect(() => {
    if (!isLoading) {
      if (!user && !redirecting) {
        setRedirecting(true)
        // Add a small delay to prevent potential race conditions
        setTimeout(() => {
          router.push('/login?redirect=/dashboard')
        }, 100)
      } else if (user && !isProfileComplete && !redirecting) {
        setRedirecting(true)
        setTimeout(() => {
          router.push('/profile-setup')
        }, 100)
      }
    }
  }, [user, isLoading, isProfileComplete, router, redirecting])

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

  // If not authenticated after loading, don't render anything (will redirect)
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
        <div className="flex flex-col items-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-blue-600 font-medium">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardHeader />
      <div className="flex-1 flex">
        <DashboardSidebar />
        <main className="flex-1 transition-all duration-300 ease-in-out ml-16 dashboard-main p-6 bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-white dark:from-blue-950/20 dark:via-indigo-950/10 dark:to-background">
          {children}
        </main>
      </div>
    </div>
  )
}

