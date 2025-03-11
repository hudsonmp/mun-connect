"use client"

import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback, useRef } from 'react'
import { supabase, getSupabase } from './supabase'
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
  try {
    const localStorageItems = {
      'authState': localStorage.getItem('authState'),
      'access_token': localStorage.getItem('access_token'),
      'refresh_token': localStorage.getItem('refresh_token'),
    };
    console.table(localStorageItems);
  } catch (error) {
    console.error('Error accessing localStorage:', error);
  }
  
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
  
  // Get the Supabase client
  const supabaseClient = typeof window !== 'undefined' ? getSupabase() : null;
  
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
      
      let refreshToken;
      try {
        refreshToken = localStorage.getItem('refresh_token');
      } catch (error) {
        console.error('Error accessing refresh token from localStorage:', error);
        refreshToken = null;
      }
      
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
      try {
        localStorage.setItem('access_token', data.access_token)
      } catch (error) {
        console.error('Error storing access token in localStorage:', error);
      }
      
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
      try {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      } catch (storageError) {
        console.error('Error clearing tokens from localStorage:', storageError);
      }
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
    // Check if we have a Supabase client
    if (!supabaseClient) {
      console.error('Supabase client not available');
      setIsLoading(false);
      return;
    }
    
    // Check for existing session
    const initializeAuth = async () => {
      try {
        const { data, error } = await supabaseClient.auth.getSession();
        if (error) {
          console.error('Error getting session:', error);
          setIsLoading(false);
          return;
        }
        
        if (data?.session) {
          setSession(data.session);
          setUser(data.session.user as User);
          
          // Check if profile is complete
          const { data: profile } = await supabaseClient
            .from('profiles')
            .select('username')
            .eq('id', data.session.user.id)
            .single();
            
          setIsProfileComplete(!!profile?.username);
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    initializeAuth();
    
    // Set up refresh timer
    const REFRESH_INTERVAL = 14 * 60 * 1000 // 14 minutes
    refreshTimerRef.current = setInterval(refreshSession, REFRESH_INTERVAL)
    
    // Set up auth state change listener
    let authListener: any;
    if (supabaseClient) {
      authListener = supabaseClient.auth.onAuthStateChange((event, session) => {
        if (DEBUG_AUTH) console.log('Auth state changed:', event);
        
        if (session) {
          setSession(session);
          setUser(session.user as User);
        } else if (event === 'SIGNED_OUT') {
          setSession(null);
          setUser(null);
        }
      });
    }
    
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
      if (authListener) authListener.subscription.unsubscribe();
    }
  }, [refreshSession, supabaseClient])

  // Enhanced signup with proper profile creation
  const signUp = async (email: string, password: string, username: string) => {
    try {
      if (DEBUG_AUTH) console.log('Signing up user:', email)
      
      if (!supabaseClient) {
        return { error: 'Supabase client not initialized', data: null };
      }
      
      // Sign up with Supabase
      const { data: authData, error: authError } = await supabaseClient.auth.signUp({
        email,
        password,
      });
      
      if (authError) {
        return { error: authError, data: null };
      }
      
      if (!authData.user) {
        return { error: 'No user returned from signUp', data: null };
      }
      
      // Create the profile
      const { error: profileError } = await supabaseClient
        .from('profiles')
        .upsert({
          id: authData.user.id,
          username,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        
      if (profileError) {
        return { error: profileError, data: null };
      }
      
      setUser(authData.user as User);
      setSession(authData.session);
      setIsProfileComplete(true);
      
      router.push('/dashboard/dashboard');
      return { error: null, data: authData };
      
    } catch (error) {
      console.error('Exception in signUp:', error)
      return { error: error instanceof Error ? error.message : 'An error occurred during signup', data: null }
    }
  }

  // Enhanced sign in with better error handling
  const signIn = async (email: string, password: string) => {
    try {
      if (DEBUG_AUTH) console.log('Signing in user:', email)
      
      if (!supabaseClient) {
        return { error: 'Supabase client not initialized', data: null };
      }
      
      // Use Supabase's built-in signIn
      const { data: authData, error: authError } = await supabaseClient.auth.signInWithPassword({
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
      
      setUser(authData.user as User)
      setSession(authData.session)
      
      // Check if profile is complete
      const { data: profile } = await supabaseClient
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
      
      if (supabaseClient) {
        await supabaseClient.auth.signOut();
      }
      
      // Clear all auth state
      try {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      } catch (error) {
        console.error('Error clearing tokens from localStorage:', error);
      }
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
      if (!user) {
        return { error: 'No user logged in', data: null };
      }
      
      if (!supabaseClient) {
        return { error: 'Supabase client not initialized', data: null };
      }
      
      // Update profile using Supabase
      const { data, error } = await supabaseClient
        .from('profiles')
        .upsert({
          id: user.id,
          ...profileData,
          updated_at: new Date().toISOString(),
        })
        .select()
        .single();
        
      if (error) {
        return { error, data: null };
      }

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