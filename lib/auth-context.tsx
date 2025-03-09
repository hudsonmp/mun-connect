"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { supabase } from './supabase'
import { Session, User } from '@supabase/supabase-js'
import { useRouter, usePathname } from 'next/navigation'

type AuthContextType = {
  user: User | null
  session: Session | null
  isLoading: boolean
  signUp: (email: string, password: string) => Promise<{ error: any; data: any }>
  signIn: (email: string, password: string) => Promise<{ error: any; data: any }>
  signOut: () => Promise<void>
  isProfileComplete: boolean
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isProfileComplete, setIsProfileComplete] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  // Helper function to check if a path is an auth path
  const isAuthPath = (path: string) => {
    return path.includes('/login') || path.includes('/register') || path.includes('/profile-setup')
  }

  // Function to refresh the session
  const refreshSession = async () => {
    try {
      const { data, error } = await supabase.auth.refreshSession()
      if (error) {
        console.error('Error refreshing session:', error)
        // If refresh fails, redirect to login
        if (!isAuthPath(pathname || '')) {
          router.push('/login')
        }
      } else if (data.session) {
        setSession(data.session)
        setUser(data.session.user)
      }
    } catch (error) {
      console.error('Error in refreshSession:', error)
    }
  }

  useEffect(() => {
    const getSession = async () => {
      try {
        setIsLoading(true)
        const { data: { session } } = await supabase.auth.getSession()
        
        setSession(session)
        setUser(session?.user ?? null)
        
        if (session?.user) {
          // Check if profile is complete
          const { data, error } = await supabase
            .from('profiles')
            .select('username')
            .eq('id', session.user.id)
            .single()
          
          if (error) {
            console.error('Error fetching profile:', error)
          }
          
          setIsProfileComplete(!!data?.username)
          
          // Set up a timer to refresh the session before it expires
          if (session.expires_at) {
            const expiresAt = new Date(session.expires_at * 1000)
            const timeUntilExpiry = expiresAt.getTime() - Date.now()
            const refreshTime = Math.max(timeUntilExpiry - 60000, 0) // Refresh 1 minute before expiry
            
            const refreshTimer = setTimeout(() => {
              refreshSession()
            }, refreshTime)
            
            return () => clearTimeout(refreshTimer)
          }
        }
      } catch (error) {
        console.error('Error in getSession:', error)
      } finally {
        setIsLoading(false)
      }
    }

    getSession()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session)
        setUser(session?.user ?? null)
        
        // Handle auth state changes
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
          // Get profile information
          if (session?.user) {
            try {
              const { data, error } = await supabase
                .from('profiles')
                .select('username')
                .eq('id', session.user.id)
                .single()
              
              if (error) {
                console.error('Error fetching profile on auth change:', error)
              }
              
              setIsProfileComplete(!!data?.username)
            } catch (error) {
              console.error('Error in auth change profile fetch:', error)
            }
          }
        } else if (event === 'SIGNED_OUT') {
          // Redirect to home page on sign out if not already on an auth page
          if (!isAuthPath(pathname || '')) {
            router.push('/')
          }
        }
        
        setIsLoading(false)
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [router, pathname])

  const signUp = async (email: string, password: string) => {
    try {
      const response = await supabase.auth.signUp({
        email,
        password,
      })
      return response
    } catch (error) {
      console.error('Error in signUp:', error)
      return { error, data: null }
    }
  }

  const signIn = async (email: string, password: string) => {
    try {
      const response = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      return response
    } catch (error) {
      console.error('Error in signIn:', error)
      return { error, data: null }
    }
  }

  const signOut = async () => {
    try {
      await supabase.auth.signOut()
      router.push('/')
    } catch (error) {
      console.error('Error in signOut:', error)
    }
  }

  const value = {
    user,
    session,
    isLoading,
    signUp,
    signIn,
    signOut,
    isProfileComplete,
    refreshSession
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
} 