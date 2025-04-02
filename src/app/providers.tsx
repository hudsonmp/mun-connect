"use client"

import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/toaster"
import { AuthProvider } from '@/lib/auth-context'
import { UserProfileProvider } from '@/lib/user-profile-context'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <UserProfileProvider>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
          <Toaster />
        </ThemeProvider>
      </UserProfileProvider>
    </AuthProvider>
  )
} 