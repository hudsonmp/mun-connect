"use client"

import React, { createContext, useContext, useState, useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { supabase } from './supabase-client' // Use the shared client

// Initialize Supabase client
// const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
// const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
// const supabase = createClient(supabaseUrl, supabaseAnonKey)

interface AuthContextProps {
  user: any | null
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextProps | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  // Get the current session
  const getSession = async () => {
    try {
      const { data: { session }, error } = await supabase.auth.getSession()
      if (error) throw error
      setUser(session?.user ?? null)
    } catch (error) {
      console.error("Error getting session:", error)
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  // Check authentication on initial load
  useEffect(() => {
    getSession()

    // Set up auth state listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      setIsLoading(false)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  // Handle redirects based on auth state
  useEffect(() => {
    if (!isLoading) {
      const isAuthRoute = pathname?.startsWith("/auth/")
      const isPublicRoute = pathname === "/"
      
      if (!user && !isAuthRoute && !isPublicRoute) {
        router.push("/auth/login")
      } else if (user && isAuthRoute) {
        router.push("/")
      }
    }
  }, [user, isLoading, pathname, router])

  // Sign in
  const signIn = async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) throw error

      setUser(data.user)
      router.push("/")
    } catch (error: any) {
      console.error("Sign in error:", error)
      throw error
    }
  }

  // Sign up
  const signUp = async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      })

      if (error) throw error

      // Redirect to login page after successful registration
      router.push("/auth/login")
    } catch (error: any) {
      console.error("Sign up error:", error)
      throw error
    }
  }

  // Sign out
  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) throw error

      setUser(null)
      router.push("/auth/login")
    } catch (error: any) {
      console.error("Sign out error:", error)
      throw error
    }
  }

  // If loading, return null or a loading spinner
  if (isLoading) {
    return null // Or return a loading spinner component
  }

  return (
    <AuthContext.Provider 
      value={{
        user,
        isLoading,
        signIn,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
} 