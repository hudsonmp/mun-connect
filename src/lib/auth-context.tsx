"use client"

import React, { createContext, useContext, useState, useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { supabase, isSupabaseInitialized } from './supabase-client'

// Define proper types
type User = {
  id: string
  email?: string
  // Add other user properties as needed
}

interface AuthContextProps {
  user: User | null
  isLoading: boolean
  error: string | null
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signUp: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signOut: () => Promise<{ success: boolean; error?: string }>
  clearError: () => void
  isInitialized: boolean
}

const AuthContext = createContext<AuthContextProps | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  const clearError = () => setError(null)

  // Initialize auth state
  useEffect(() => {
    // Check if supabase is properly initialized
    if (!isSupabaseInitialized) {
      console.error("Supabase client not properly initialized. Check environment variables.")
      setError("Authentication service is not available. Please check your configuration.")
      setIsLoading(false)
      return
    }

    let mounted = true
    
    async function initializeAuth() {
      try {
        // Get the current session
        const { data, error: sessionError } = await supabase.auth.getSession()
        
        if (sessionError) throw sessionError
        
        if (mounted) {
          setUser(data.session?.user ?? null)
          setIsLoading(false)
          setIsInitialized(true)
        }
        
        // Set up auth state listener
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
          (_event, session) => {
            if (mounted) {
              setUser(session?.user ?? null)
            }
          }
        )
        
        // Return cleanup function
        return () => {
          mounted = false
          subscription.unsubscribe()
        }
      } catch (err: any) {
        console.error("Auth initialization error:", err)
        if (mounted) {
          setError(err.message || "Failed to initialize authentication")
          setUser(null)
          setIsLoading(false)
        }
      }
    }
    
    const cleanup = initializeAuth()
    
    return () => {
      cleanup.then(cleanupFn => cleanupFn && cleanupFn())
    }
  }, [])

  // Handle redirects based on auth state
  useEffect(() => {
    if (isLoading) return

    const isAuthRoute = pathname?.startsWith("/auth/")
    const isPublicRoute = pathname === "/"
    
    if (!user && !isAuthRoute && !isPublicRoute) {
      router.push("/auth/login")
    } else if (user && isAuthRoute) {
      router.push("/")
    }
  }, [user, isLoading, pathname, router])

  // Sign in with better error handling
  const signIn = async (email: string, password: string) => {
    try {
      setError(null)
      
      // Verify supabase is initialized
      if (!isSupabaseInitialized) {
        throw new Error("Authentication service is not available. Please check your configuration.")
      }
      
      // Verify supabase client exists
      if (!supabase || !supabase.auth) {
        throw new Error("Authentication client is not properly initialized")
      }

      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) throw error

      setUser(data.user)
      return { success: true }
    } catch (err: any) {
      console.error("Sign in error:", err)
      const errorMessage = err.message || "Failed to sign in"
      setError(errorMessage)
      return { success: false, error: errorMessage }
    }
  }

  // Sign up with better error handling
  const signUp = async (email: string, password: string) => {
    try {
      setError(null)
      
      // Verify supabase is initialized
      if (!isSupabaseInitialized) {
        throw new Error("Authentication service is not available. Please check your configuration.")
      }
      
      // Verify supabase client exists
      if (!supabase || !supabase.auth) {
        throw new Error("Authentication client is not properly initialized")
      }

      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      })

      if (error) throw error

      return { success: true }
    } catch (err: any) {
      console.error("Sign up error:", err)
      const errorMessage = err.message || "Failed to sign up"
      setError(errorMessage)
      return { success: false, error: errorMessage }
    }
  }

  // Sign out with better error handling
  const signOut = async () => {
    try {
      setError(null)
      
      // Verify supabase is initialized
      if (!isSupabaseInitialized) {
        throw new Error("Authentication service is not available. Please check your configuration.")
      }
      
      // Verify supabase client exists
      if (!supabase || !supabase.auth) {
        throw new Error("Authentication client is not properly initialized")
      }

      const { error } = await supabase.auth.signOut()
      if (error) throw error

      setUser(null)
      return { success: true }
    } catch (err: any) {
      console.error("Sign out error:", err)
      const errorMessage = err.message || "Failed to sign out"
      setError(errorMessage)
      return { success: false, error: errorMessage }
    }
  }

  const value = {
    user,
    isLoading,
    error,
    signIn,
    signUp,
    signOut,
    clearError,
    isInitialized,
  }

  return (
    <AuthContext.Provider value={value}>
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