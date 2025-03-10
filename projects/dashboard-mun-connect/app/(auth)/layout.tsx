"use client"

import React, { useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useAuth, AuthProvider } from "../../lib/auth-context"

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider>
      <AuthLayoutContent>
        {children}
      </AuthLayoutContent>
    </AuthProvider>
  )
}

function AuthLayoutContent({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (!isLoading && user) {
      router.push('/dashboard')
    }
  }, [user, isLoading, router])

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