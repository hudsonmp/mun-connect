"use client"

import { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from './supabase'
import { Session, User } from '@supabase/supabase-js'
import { useRouter } from 'next/navigation'

type AuthContextType = {
  user: User | null
  session: Session | null
  isLoading: boolean
  signUp: (email: string, password: string) => Promise<{ error: any; data: any }>
  signIn: (email: string, password: string) => Promise<{ error: any; data: any }>
  signOut: () => Promise<void>
  isProfileComplete: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isProfileComplete, setIsProfileComplete] = useState(false)
  const router = useRouter()

  useEffect(() => {
    const getSession = async () => {
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
        
        setIsProfileComplete(!!data?.username)
        
        // If we're on the landing page and user is authenticated, redirect to dashboard
        if (typeof window !== 'undefined' && window.location.pathname === '/') {
          router.push('/dashboard')
        }
      }
      
      setIsLoading(false)
    }

    getSession()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setSession(session)
        setUser(session?.user ?? null)
        setIsLoading(false)
        
        // Handle auth state changes
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
          // Get profile information
          if (session?.user) {
            supabase
              .from('profiles')
              .select('username')
              .eq('id', session.user.id)
              .single()
              .then(({ data }) => {
                setIsProfileComplete(!!data?.username)
                
                // If user just signed in and is on landing page, redirect to dashboard
                if (typeof window !== 'undefined' && window.location.pathname === '/') {
                  router.push('/dashboard')
                }
              })
          }
        } else if (event === 'SIGNED_OUT') {
          // If user signed out, redirect to landing page
          if (typeof window !== 'undefined' && window.location.pathname.includes('/dashboard')) {
            router.push('/')
          }
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [router])

  const signUp = async (email: string, password: string) => {
    const response = await supabase.auth.signUp({
      email,
      password,
    })
    return response
  }

  const signIn = async (email: string, password: string) => {
    const response = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    return response
  }

  const signOut = async () => {
    await supabase.auth.signOut()
    router.push('/')
  }

  const value = {
    user,
    session,
    isLoading,
    signUp,
    signIn,
    signOut,
    isProfileComplete
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