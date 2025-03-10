"use client"

import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react'
import { supabase } from './supabase'
import { Session, User } from '@supabase/supabase-js'
import { useRouter, usePathname } from 'next/navigation'

// Debug flag to help debug auth issues
const DEBUG_AUTH = true

type AuthContextType = {
  user: User | null
  session: Session | null
  isLoading: boolean
  signUp: (email: string, password: string) => Promise<{ error: any; data: any }>
  signIn: (email: string, password: string) => Promise<{ error: any; data: any }>
  signOut: () => Promise<void>
  isProfileComplete: boolean
  refreshSession: () => Promise<void>
  updateProfile: (profileData: any) => Promise<{ error: any; data: any }>
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
  const isAuthPath = useCallback((path: string) => {
    return path.includes('/login') || path.includes('/register') || path.includes('/profile-setup')
  }, [])

  // Enhanced session refresh with better error handling and persistence
  const refreshSession = useCallback(async () => {
    try {
      if (DEBUG_AUTH) console.log('Refreshing session...')
      const { data, error } = await supabase.auth.refreshSession()
      
      if (error) {
        console.error('Error refreshing session:', error)
        
        // Try to get existing session before giving up
        const { data: sessionData } = await supabase.auth.getSession()
        if (sessionData?.session) {
          if (DEBUG_AUTH) console.log('Found existing session after refresh failure')
          setSession(sessionData.session)
          setUser(sessionData.session.user)
          return
        }
        
        // If we still don't have a session and we're not on an auth path, redirect to login
        if (!isAuthPath(pathname || '')) {
          if (DEBUG_AUTH) console.log('No session found, redirecting to login')
          router.push('/dashboard/login')
        }
      } else if (data.session) {
        if (DEBUG_AUTH) console.log('Session refreshed successfully')
        setSession(data.session)
        setUser(data.session.user)
        
        // Store in localStorage as backup
        localStorage.setItem('authState', JSON.stringify({
          isAuthenticated: true,
          userId: data.session.user.id,
          lastUpdated: new Date().toISOString()
        }))
      } else {
        if (DEBUG_AUTH) console.log('No session after refresh')
        setSession(null)
        setUser(null)
        localStorage.removeItem('authState')
      }
    } catch (error) {
      console.error('Exception in refreshSession:', error)
    }
  }, [router, pathname, isAuthPath])

  // Function to update user profile with error handling
  const updateProfile = async (profileData: any) => {
    try {
      if (!user) {
        return { error: { message: 'No user logged in' }, data: null }
      }

      const { error, data } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          ...profileData,
          updated_at: new Date().toISOString(),
        })
        .select()

      if (error) {
        console.error('Error updating profile:', error)
        return { error, data: null }
      }

      // Update the profile completion status
      if (data && data[0]?.username) {
        setIsProfileComplete(true)
      }

      return { error: null, data }
    } catch (error) {
      console.error('Error updating profile:', error)
      return { error, data: null }
    }
  }

  // Initialize session and set up event listeners
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setIsLoading(true)
        if (DEBUG_AUTH) console.log('Initializing auth...')
        
        // Try to get session from Supabase
        const { data: { session } } = await supabase.auth.getSession()
        
        if (session) {
          if (DEBUG_AUTH) console.log('Session found during initialization')
          setSession(session)
          setUser(session.user)
          
          // Check if profile is complete
          try {
            const { data, error } = await supabase
              .from('profiles')
              .select('username')
              .eq('id', session.user.id)
              .single()
            
            if (error) {
              console.error('Error fetching profile during init:', error)
              
              // Create default profile if it doesn't exist
              if (error.code === 'PGRST116') {
                const defaultUsername = `user_${Math.random().toString(36).substring(2, 10)}`
                if (DEBUG_AUTH) console.log('Creating default profile with username:', defaultUsername)
                
                const { error: createError } = await supabase
                  .from('profiles')
                  .upsert({
                    id: session.user.id,
                    username: defaultUsername,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                  })
                
                if (createError) {
                  console.error('Error creating profile:', createError)
                } else {
                  setIsProfileComplete(false)
                }
              }
            } else {
              setIsProfileComplete(!!data?.username)
              if (DEBUG_AUTH) console.log('Profile complete:', !!data?.username)
            }
          } catch (error) {
            console.error('Exception fetching profile:', error)
          }
          
          // Set up session refresh timer
          if (session.expires_at) {
            const expiresAt = new Date(session.expires_at * 1000)
            const timeUntilExpiry = expiresAt.getTime() - Date.now()
            // Refresh 5 minutes before expiry or immediately if close to expiry
            const refreshTime = Math.max(timeUntilExpiry - 300000, 0) 
            
            if (DEBUG_AUTH) console.log(`Session expires in ${timeUntilExpiry/1000/60} minutes, scheduling refresh in ${refreshTime/1000/60} minutes`)
            
            const refreshTimer = setTimeout(() => {
              if (DEBUG_AUTH) console.log('Refresh timer triggered')
              refreshSession()
            }, refreshTime)
            
            return () => clearTimeout(refreshTimer)
          }
        } else {
          if (DEBUG_AUTH) console.log('No session found during initialization')
          
          // Try to recover from localStorage backup
          const storedAuthState = localStorage.getItem('authState')
          if (storedAuthState) {
            try {
              const authState = JSON.parse(storedAuthState)
              const lastUpdated = new Date(authState.lastUpdated)
              const now = new Date()
              const hoursSinceUpdate = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60)
              
              if (hoursSinceUpdate < 24 && authState.isAuthenticated) {
                if (DEBUG_AUTH) console.log('Found recent auth state, attempting to restore session')
                // We'll call refresh to try to recover the session
                await refreshSession()
              } else {
                localStorage.removeItem('authState')
              }
            } catch (e) {
              console.error('Error parsing auth state:', e)
              localStorage.removeItem('authState')
            }
          }
        }
      } catch (error) {
        console.error('Exception in auth initialization:', error)
      } finally {
        setIsLoading(false)
      }
    }

    initializeAuth()

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (DEBUG_AUTH) console.log('Auth state changed:', event)
        
        setSession(session)
        setUser(session?.user ?? null)
        
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
          if (session) {
            // Check profile status
            try {
              const { data, error } = await supabase
                .from('profiles')
                .select('username')
                .eq('id', session.user.id)
                .single()
              
              if (error) {
                console.error('Error fetching profile on auth change:', error)
                
                if (error.code === 'PGRST116') {
                  // Create default profile
                  const defaultUsername = `user_${Math.random().toString(36).substring(2, 10)}`
                  if (DEBUG_AUTH) console.log('Creating default profile on auth change with username:', defaultUsername)
                  
                  const { error: createError } = await supabase
                    .from('profiles')
                    .upsert({
                      id: session.user.id,
                      username: defaultUsername,
                      created_at: new Date().toISOString(),
                      updated_at: new Date().toISOString(),
                    })
                  
                  if (createError) {
                    console.error('Error creating profile on auth change:', createError)
                  } else {
                    setIsProfileComplete(false)
                  }
                }
              } else {
                setIsProfileComplete(!!data?.username)
              }
            } catch (error) {
              console.error('Exception in auth change profile fetch:', error)
            }
            
            // Update local storage backup
            localStorage.setItem('authState', JSON.stringify({
              isAuthenticated: true,
              userId: session.user.id,
              lastUpdated: new Date().toISOString()
            }))
          }
        } else if (event === 'SIGNED_OUT') {
          if (DEBUG_AUTH) console.log('User signed out')
          localStorage.removeItem('authState')
          
          // Redirect to home page on sign out if not already on an auth page
          if (!isAuthPath(pathname || '')) {
            router.push('/dashboard/login')
          }
        }
        
        setIsLoading(false)
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [router, pathname, refreshSession, isAuthPath])

  // Enhanced signup with proper profile creation
  const signUp = async (email: string, password: string) => {
    try {
      if (DEBUG_AUTH) console.log('Signing up user:', email)
      
      // Get redirect URL from localStorage or use default
      let redirectUrl = '/dashboard/auth/callback'
      if (typeof window !== 'undefined' && window.localStorage) {
        redirectUrl = window.localStorage.getItem('supabaseRedirectUrl') || redirectUrl
      }
      
      const response = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: redirectUrl,
        }
      })
      
      if (DEBUG_AUTH) {
        if (response.error) {
          console.error('Sign up error:', response.error)
        } else {
          console.log('Sign up successful, confirmation email sent')
        }
      }
      
      // Create a basic profile entry if signup is successful
      if (response.data?.user && !response.error) {
        const defaultUsername = `user_${Math.random().toString(36).substring(2, 10)}`
        if (DEBUG_AUTH) console.log('Creating profile for new user with username:', defaultUsername)
        
        // Create a default profile with a generated username
        await supabase
          .from('profiles')
          .upsert({
            id: response.data.user.id,
            username: defaultUsername,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          })
      }
      
      return response
    } catch (error) {
      console.error('Exception in signUp:', error)
      return { error, data: null }
    }
  }

  // Enhanced sign in with better error handling and session persistence
  const signIn = async (email: string, password: string) => {
    try {
      if (DEBUG_AUTH) console.log('Signing in user:', email)
      
      const response = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      
      if (DEBUG_AUTH) {
        if (response.error) {
          console.error('Sign in error:', response.error)
        } else {
          console.log('Sign in successful')
        }
      }
      
      // Store successful sign-in info and update context
      if (response.data?.session) {
        if (DEBUG_AUTH) console.log('Setting session after sign in')
        
        // Explicitly set the auth context state
        setSession(response.data.session)
        setUser(response.data.session.user)
        
        // Store in localStorage as backup
        localStorage.setItem('authState', JSON.stringify({
          isAuthenticated: true,
          userId: response.data.session.user.id,
          lastUpdated: new Date().toISOString()
        }))
        
        // Check if profile is complete
        try {
          const { data: profile } = await supabase
            .from('profiles')
            .select('username')
            .eq('id', response.data.session.user.id)
            .single()
            
          setIsProfileComplete(!!profile?.username)
        } catch (error) {
          console.error('Error checking profile on sign in:', error)
        }
      }
      
      return response
    } catch (error) {
      console.error('Exception in signIn:', error)
      return { error, data: null }
    }
  }

  // Enhanced sign out that properly cleans up state
  const signOut = async () => {
    try {
      if (DEBUG_AUTH) console.log('Signing out user')
      
      // Sign out from Supabase
      await supabase.auth.signOut()
      
      // Clear all auth state
      setSession(null)
      setUser(null)
      setIsProfileComplete(false)
      localStorage.removeItem('authState')
      
      // Navigate to login page
      router.push('/dashboard/login')
      
      if (DEBUG_AUTH) console.log('Sign out complete')
    } catch (error) {
      console.error('Error signing out:', error)
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
    refreshSession,
    updateProfile,
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