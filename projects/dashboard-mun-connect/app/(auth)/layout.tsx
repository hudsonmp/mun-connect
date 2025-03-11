"use client"

import React, { useEffect } from "react"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "../../lib/auth-context"

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (!isLoading && user) {
      // If we're already on a profile setup page and profile is not complete, don't redirect
      if (pathname === '/dashboard/profile-setup' && !user.username) {
        return
      }
      router.push('/dashboard/dashboard')
    }
  }, [user, isLoading, router, pathname])

  return (
    <div className="min-h-screen bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950">
      <div className="container mx-auto px-4 py-6">
        <header className="flex justify-center mb-8">
          <Link href="/" className="flex items-center space-x-2">
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-2xl font-bold text-transparent">
              MUN Connect
            </span>
          </Link>
        </header>
        <main>{children}</main>
      </div>
    </div>
  )
} 