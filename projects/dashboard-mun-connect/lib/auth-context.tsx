"use client"

import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback, useRef } from 'react'
import { supabase } from './supabase'
import { Session } from '@supabase/supabase-js'
import { useRouter, usePathname } from 'next/navigation'
import { User } from './types'

// Debug flag to help debug auth issues
const DEBUG_AUTH = true

// Add a browser console debugger function
const debugAuthState = () => {
  if (typeof window === 'undefined' || !DEBUG_AUTH) return;
  
  console.group('%c🔐 Auth State Debugger', 'color: #10B981; font-weight: bold; font-size: 14px;');
  
  // Check for cookies 
  console.log('%cCookies:', 'font-weight: bold;');
  console.table(document.cookie.split(';').reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split('=');
    if (key) acc[key] = value || 'empty';
    return acc;
  }, {} as Record<string, string>));
  
  // Check localStorage
  console.log('%cLocal Storage:', 'font-weight: bold;');
  const localStorageItems = {
    'authState': localStorage.getItem('authState'),
    'access_token': localStorage.getItem('access_token'),
    'refresh_token': localStorage.getItem('refresh_token'),
  };
  console.table(localStorageItems);
  
  console.groupEnd();
};

// Call debug function on load
if (typeof window !== 'undefined' && DEBUG_AUTH) {
  setTimeout(debugAuthState, 1000);
}

type AuthContextType = {
  user: User | null
  session: Session | null
  isLoading: boolean
  signUp: (email: string, password: string, username: string) => Promise<{ error: any; data: any }>
  signIn: (email: string, password: string) => Promise<{ error: any; data: any }>
  signOut: () => Promise<void>
  isProfileComplete: boolean
  refreshSession: () => Promise<void>
  updateProfile: (profileData: any) => Promise<{ error: any; data: any }>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Helper function to handle API responses
async function handleApiResponse(response: Response) {
  const data = await response.json()
  
  if (!response.ok) {
    // If the response contains an error message, use it
    if (data?.error) {
      throw new Error(typeof data.error === 'string' ? data.error : JSON.stringify(data.error))
    }
    // Otherwise, throw a generic error with the status
    throw new Error(`Request failed with status ${response.status}`)
  }
  
  return data
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isProfileComplete, setIsProfileComplete] = useState(false)
  const router = useRouter()
  const pathname = usePathname()
  
  // Refs for timers to allow cleanup
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Helper function to check if a path is an auth path
  const isAuthPath = useCallback((path: string) => {
    const authPaths = ['/login', '/register', '/profile-setup']
    return authPaths.some(authPath => 
      path === authPath || 
      path === `/dashboard${authPath}` || 
      path === `/dashboard/dashboard${authPath}`
    )
  }, [])

  // Enhanced session refresh with better error handling
  const refreshSession = useCallback(async () => {
    try {
      if (DEBUG_AUTH) console.log('Refreshing session...')
      
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        setSession(null)
        setUser(null)
        setIsLoading(false)
        
        if (!isAuthPath(pathname || '')) {
          router.push('/dashboard/login')
        }
        return
      }
      
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${refreshToken}`,
        },
      })
      
      const data = await handleApiResponse(response)
      localStorage.setItem('access_token', data.access_token)
      
      // Get user data with new token
      const userResponse = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${data.access_token}`,
        },
      })
      
      const userData = await handleApiResponse(userResponse)
      setUser(userData)
      setSession({ access_token: data.access_token, refresh_token: refreshToken } as Session)
      setIsProfileComplete(!!userData.username)
      
      if (isAuthPath(pathname || '')) {
        router.push('/dashboard/dashboard')
      }
    } catch (error) {
      console.error('Error in refreshSession:', error)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setSession(null)
      setUser(null)
      
      if (!isAuthPath(pathname || '')) {
        router.push('/dashboard/login')
      }
    } finally {
      setIsLoading(false)
    }
  }, [pathname, router, isAuthPath])

  // Initialize auth state
  useEffect(() => {
    refreshSession()
    
    // Set up refresh timer
    const REFRESH_INTERVAL = 14 * 60 * 1000 // 14 minutes
    refreshTimerRef.current = setInterval(refreshSession, REFRESH_INTERVAL)
    
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current)
    }
  }, [refreshSession])

  // Enhanced signup with proper profile creation
  const signUp = async (email: string, password: string, username: string) => {
    try {
      if (DEBUG_AUTH) console.log('Signing up user:', email)
      
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          username,
        }),
      })
      
      const data = await handleApiResponse(response)
      
      // Store tokens
      localStorage.setItem('access_token', data.tokens.access_token)
      localStorage.setItem('refresh_token', data.tokens.refresh_token)
      
      setUser(data.user)
      setSession({
        access_token: data.tokens.access_token,
        refresh_token: data.tokens.refresh_token,
      } as Session)
      setIsProfileComplete(true)
      
      router.push('/dashboard/dashboard')
      return { error: null, data }
    } catch (error) {
      console.error('Exception in signUp:', error)
      return { error: error instanceof Error ? error.message : 'An error occurred during signup', data: null }
    }
  }

  // Enhanced sign in with better error handling
  const signIn = async (email: string, password: string) => {
    try {
      if (DEBUG_AUTH) console.log('Signing in user:', email)
      
      // Use Supabase's built-in signIn instead of custom API
      const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      
      if (authError) {
        console.error('Auth error:', authError)
        return { error: authError, data: null }
      }
      
      if (!authData.session) {
        console.error('No session returned from signIn')
        return { error: new Error('No session returned from signIn'), data: null }
      }
      
      // Set the session in Supabase client
      await supabase.auth.setSession({
        access_token: authData.session.access_token,
        refresh_token: authData.session.refresh_token,
      })
      
      setUser(authData.user)
      setSession(authData.session)
      
      // Store minimal auth state in localStorage
      localStorage.setItem('authState', JSON.stringify({
        isAuthenticated: true,
        userId: authData.user.id,
        hasSupabaseAuth: true,
        lastUpdated: new Date().toISOString()
      }))
      
      // Check if profile is complete
      const { data: profile } = await supabase
        .from('profiles')
        .select('username')
        .eq('id', authData.user.id)
        .single()
      
      setIsProfileComplete(!!profile?.username)
      
      // Handle redirect
      const params = new URLSearchParams(window.location.search)
      const redirectPath = params.get('redirect') || '/dashboard'
      
      if (!profile?.username) {
        router.push('/dashboard/profile-setup')
      } else {
        router.push(redirectPath)
      }
      
      return { error: null, data: authData }
    } catch (error) {
      console.error('Exception in signIn:', error)
      return { error: error instanceof Error ? error.message : 'An error occurred during sign in', data: null }
    }
  }

  // Enhanced sign out that properly cleans up state
  const signOut = async () => {
    try {
      if (DEBUG_AUTH) console.log('Signing out user')
      
      // Clear all auth state
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setSession(null)
      setUser(null)
      setIsProfileComplete(false)
      
      // Navigate to login page
      router.push('/dashboard/login')
      
      if (DEBUG_AUTH) console.log('Sign out complete')
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  // Function to update user profile with better error handling
  const updateProfile = async (profileData: any) => {
    try {
      const accessToken = localStorage.getItem('access_token')
      if (!accessToken) {
        return { error: 'No user logged in', data: null }
      }

      const response = await fetch('/api/auth/me', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify(profileData),
      })

      const data = await handleApiResponse(response)

      // Update the profile completion status
      if (data?.username) {
        setIsProfileComplete(true)
      }

      return { error: null, data }
    } catch (error) {
      console.error('Error updating profile:', error)
      return { error: error instanceof Error ? error.message : 'An error occurred while updating profile', data: null }
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