"use client"

import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback, useRef } from 'react'
import { supabase } from './supabase'
import { Session, User } from '@supabase/supabase-js'
import { useRouter, usePathname } from 'next/navigation'

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
    'supabase-auth': localStorage.getItem('supabase-auth'),
    'supabaseRedirectUrl': localStorage.getItem('supabaseRedirectUrl'),
    'redirect_count': localStorage.getItem('redirect_count'),
  };
  console.table(localStorageItems);
  
  // Check for service worker
  console.log('%cService Worker Status:', 'font-weight: bold;');
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => {
      console.log(`Service Workers: ${registrations.length} registered`);
      registrations.forEach(reg => console.log(reg.scope));
    });
  } else {
    console.log('Service Workers not supported');
  }
  
  // Summarize auth state
  console.log('%cAuth Summary:', 'font-weight: bold;');
  try {
    const authState = localStorage.getItem('authState') ? JSON.parse(localStorage.getItem('authState')!) : null;
    const supabaseAuth = localStorage.getItem('supabase-auth') ? JSON.parse(localStorage.getItem('supabase-auth')!) : null;
    
    console.log({
      isAuthenticated: authState?.isAuthenticated || false,
      userId: authState?.userId || 'none',
      lastUpdated: authState?.lastUpdated ? new Date(authState.lastUpdated).toLocaleString() : 'never',
      hasSupabaseAuth: !!supabaseAuth,
      currentUrl: window.location.href,
      userAgent: navigator.userAgent,
    });
  } catch (e) {
    console.error('Error parsing auth state:', e);
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
  
  // Refs for timers to allow cleanup
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Helper function to get proper path with or without basePath
  const getPath = useCallback((path: string) => {
    // Since basePath is '/dashboard', we need to remove it from paths that already include it
    if (path.startsWith('/dashboard')) {
      // For paths like '/dashboard/login', we want to return just '/login'
      return path.substring('/dashboard'.length) || '/'
    }
    // For paths without the prefix, return as-is
    return path
  }, [])

  // Helper function to check if a path is an auth path
  const isAuthPath = useCallback((path: string) => {
    return path.includes('/login') || path.includes('/register') || path.includes('/profile-setup')
  }, [])

  // Enhanced session refresh with better error handling and persistence
  const refreshSession = useCallback(async () => {
    try {
      if (DEBUG_AUTH) console.log('Refreshing session...')
      
      // Debug current auth state
      debugAuthState();
      
      // Try to get current session first before refreshing
      const { data: currentSession } = await supabase.auth.getSession()
      
      if (currentSession?.session) {
        if (DEBUG_AUTH) console.log('Found existing session before refresh')
        setSession(currentSession.session)
        setUser(currentSession.session.user)
        
        // Update localStorage to ensure it's in sync with Supabase session
        localStorage.setItem('authState', JSON.stringify({
          isAuthenticated: true,
          userId: currentSession.session.user.id,
          hasSupabaseAuth: true,
          lastUpdated: new Date().toISOString(),
          currentUrl: window.location.href,
          userAgent: navigator.userAgent
        }))
      }
      
      // Now attempt to refresh the session
      const { data, error } = await supabase.auth.refreshSession()
      
      if (error) {
        console.error('Error refreshing session:', error)
        
        // If we already set a session above, we can return early
        if (currentSession?.session) {
          if (DEBUG_AUTH) console.log('Using existing session despite refresh failure')
          return
        }
        
        // Try one more time to get existing session before giving up
        const { data: sessionData } = await supabase.auth.getSession()
        if (sessionData?.session) {
          if (DEBUG_AUTH) console.log('Found existing session after refresh failure')
          setSession(sessionData.session)
          setUser(sessionData.session.user)
          
          // Update localStorage
          localStorage.setItem('authState', JSON.stringify({
            isAuthenticated: true,
            userId: sessionData.session.user.id,
            hasSupabaseAuth: true,
            lastUpdated: new Date().toISOString(),
            currentUrl: window.location.href,
            userAgent: navigator.userAgent
          }))
          return
        }
        
        // Check localStorage backup
        const storedAuthState = localStorage.getItem('authState')
        if (storedAuthState) {
          try {
            const authState = JSON.parse(storedAuthState)
            const lastUpdated = new Date(authState.lastUpdated)
            const now = new Date()
            const hoursSinceUpdate = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60)
            
            if (hoursSinceUpdate < 24 && authState.isAuthenticated) {
              if (DEBUG_AUTH) console.log('Using localStorage backup auth state')
              
              // Try one more time to explicitly set the session from stored tokens
              const supabaseAuthStr = localStorage.getItem('supabase-auth')
              if (supabaseAuthStr) {
                try {
                  const supabaseAuth = JSON.parse(supabaseAuthStr)
                  if (supabaseAuth.access_token && supabaseAuth.refresh_token) {
                    if (DEBUG_AUTH) console.log('Attempting to restore session from stored tokens')
                    const { data: sessionData, error: sessionError } = await supabase.auth.setSession({
                      access_token: supabaseAuth.access_token,
                      refresh_token: supabaseAuth.refresh_token
                    })
                    
                    if (sessionError) {
                      console.error('Failed to restore session from tokens:', sessionError)
                    } else if (sessionData?.session) {
                      if (DEBUG_AUTH) console.log('Successfully restored session from tokens')
                      setSession(sessionData.session)
                      setUser(sessionData.session.user)
                      return
                    }
                  }
                } catch (e) {
                  console.error('Error parsing supabase-auth:', e)
                }
              }
              
              // Don't redirect here, we'll try to recover the session via other means
              return
            }
          } catch (e) {
            console.error('Error parsing backup auth state:', e)
          }
        }
        
        // Debug auth state again
        debugAuthState();
        
        // If we still don't have a session and we're not on an auth path, redirect to login
        if (!isAuthPath(pathname || '')) {
          if (DEBUG_AUTH) console.log('No session found, redirecting to login')
          router.push(getPath('/dashboard/login'))
        }
      } else if (data.session) {
        if (DEBUG_AUTH) console.log('Session refreshed successfully')
        setSession(data.session)
        setUser(data.session.user)
        
        // Store in localStorage as backup
        localStorage.setItem('authState', JSON.stringify({
          isAuthenticated: true,
          userId: data.session.user.id,
          hasSupabaseAuth: true,
          lastUpdated: new Date().toISOString(),
          currentUrl: window.location.href,
          userAgent: navigator.userAgent
        }))
        
        // Explicitly set the session in Supabase client too
        await supabase.auth.setSession({
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
        })
        
        // Debug successful refresh
        debugAuthState();
      } else {
        if (DEBUG_AUTH) console.log('No session after refresh')
        
        // Check localStorage backup before clearing everything
        const storedAuthState = localStorage.getItem('authState')
        if (storedAuthState) {
          try {
            const authState = JSON.parse(storedAuthState)
            const lastUpdated = new Date(authState.lastUpdated)
            const now = new Date()
            const hoursSinceUpdate = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60)
            
            if (hoursSinceUpdate < 24 && authState.isAuthenticated) {
              if (DEBUG_AUTH) console.log('Recent auth state in localStorage, not clearing session')
              
              // Try one more time to recover the session 
              try {
                if (DEBUG_AUTH) console.log('Final attempt to refresh session')
                const { data: refreshData } = await supabase.auth.refreshSession()
                if (refreshData?.session) {
                  if (DEBUG_AUTH) console.log('Successfully refreshed session in final attempt')
                  setSession(refreshData.session)
                  setUser(refreshData.session.user)
                  return
                }
              } catch (e) {
                console.error('Error in final refresh attempt:', e)
              }
              
              return
            }
          } catch (e) {
            console.error('Error parsing stored auth state:', e)
          }
        }
        
        if (DEBUG_AUTH) console.log('Clearing session state')
        setSession(null)
        setUser(null)
        localStorage.removeItem('authState')
        
        // Force a full browser reload to reset all auth state
        if (!isAuthPath(pathname || '')) {
          if (DEBUG_AUTH) console.log('Forcing reload to login page')
          window.location.href = getPath('/dashboard/login')
        }
      }
    } catch (error) {
      console.error('Exception in refreshSession:', error)
    }
  }, [router, pathname, isAuthPath, getPath])

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
        
        // Check if we already have a stored auth state
        const storedAuthState = localStorage.getItem('authState')
        let localAuthClaim = false
        
        if (storedAuthState) {
          try {
            const authState = JSON.parse(storedAuthState)
            const lastUpdated = new Date(authState.lastUpdated)
            const now = new Date()
            const hoursSinceUpdate = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60)
            
            if (hoursSinceUpdate < 24 && authState.isAuthenticated) {
              localAuthClaim = true
              if (DEBUG_AUTH) console.log('Found local auth claim for user:', authState.userId)
              
              // Update localStorage with current metadata
              localStorage.setItem('authState', JSON.stringify({
                ...authState,
                currentUrl: window.location.href,
                userAgent: navigator.userAgent,
                lastUpdated: new Date().toISOString()
              }))
            }
          } catch (e) {
            console.error('Error parsing stored auth state:', e)
            localStorage.removeItem('authState')
          }
        }
        
        // Try to get session from Supabase
        const { data: { session }, error: sessionError } = await supabase.auth.getSession()
        
        if (sessionError) {
          console.error('Error getting session:', sessionError)
          
          // If we have a local auth claim, try to restore the session
          if (localAuthClaim) {
            if (DEBUG_AUTH) console.log('Attempting to restore session from local auth claim')
            
            // Try to refresh the session
            const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
            
            if (refreshError) {
              console.error('Failed to refresh session:', refreshError)
              
              // Try to recover from localStorage tokens if available
              const supabaseAuthStr = localStorage.getItem('supabase-auth')
              if (supabaseAuthStr) {
                try {
                  const supabaseAuth = JSON.parse(supabaseAuthStr)
                  if (supabaseAuth.access_token && supabaseAuth.refresh_token) {
                    if (DEBUG_AUTH) console.log('Trying to set session from stored tokens')
                    
                    const { data: tokenData, error: tokenError } = await supabase.auth.setSession({
                      access_token: supabaseAuth.access_token,
                      refresh_token: supabaseAuth.refresh_token
                    })
                    
                    if (tokenError) {
                      console.error('Failed to set session from tokens:', tokenError)
                    } else if (tokenData.session) {
                      if (DEBUG_AUTH) console.log('Successfully restored session from tokens')
                      setSession(tokenData.session)
                      setUser(tokenData.session.user)
                      
                      // Check profile and initialize refresh timer
                      await checkProfileAndSetupTimer(tokenData.session)
                      return
                    }
                  }
                } catch (e) {
                  console.error('Error parsing stored tokens:', e)
                }
              }
            } else if (refreshData.session) {
              if (DEBUG_AUTH) console.log('Successfully refreshed session')
              setSession(refreshData.session)
              setUser(refreshData.session.user)
              
              // Check profile and initialize refresh timer
              await checkProfileAndSetupTimer(refreshData.session)
              return
            }
          }
        } else if (session) {
          if (DEBUG_AUTH) console.log('Session found during initialization')
          setSession(session)
          setUser(session.user)
          
          // Update localStorage to stay in sync
          localStorage.setItem('authState', JSON.stringify({
            isAuthenticated: true,
            userId: session.user.id,
            hasSupabaseAuth: true,
            lastUpdated: new Date().toISOString(),
            currentUrl: window.location.href,
            userAgent: navigator.userAgent
          }))
          
          // Check profile and initialize refresh timer
          await checkProfileAndSetupTimer(session)
          return
        }
        
        // If we get here, we couldn't recover a session
        if (DEBUG_AUTH) console.log('Failed to find or restore a valid session')
        
        // Clear auth state if we're not on an auth path to force login
        if (!isAuthPath(pathname || '')) {
          localStorage.removeItem('authState')
          localStorage.removeItem('supabase-auth')
        }
        
        setIsLoading(false)
      } catch (error) {
        console.error('Exception in initializeAuth:', error)
        setIsLoading(false)
      }
    }
    
    // Helper to check profile and set up refresh timer
    const checkProfileAndSetupTimer = async (session: Session) => {
      try {
        // Check if profile is complete
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
        
        refreshTimerRef.current = setTimeout(() => {
          if (DEBUG_AUTH) console.log('Auto-refreshing session')
          refreshSession()
        }, refreshTime)
      } else {
        // No expiry time available, schedule regular refresh
        if (DEBUG_AUTH) console.log('No session expiry info, scheduling refresh in 30 minutes')
        refreshTimerRef.current = setTimeout(refreshSession, 30 * 60 * 1000)
      }
      
      // Also set up a periodic heartbeat to check the session
      heartbeatTimerRef.current = setInterval(() => {
        if (DEBUG_AUTH) console.log('Auth heartbeat check')
        supabase.auth.getSession().then(({ data }) => {
          if (!data.session && session) {
            if (DEBUG_AUTH) console.log('Heartbeat detected missing session, refreshing')
            refreshSession()
          }
        })
      }, 5 * 60 * 1000) // Check every 5 minutes
      
      setIsLoading(false)
    }
    
    // Start the auth initialization
    initializeAuth()
    
    // Clean up timers
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current)
    }
  }, [pathname, refreshSession, isAuthPath, getPath])

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

        // Explicitly set the session in Supabase client too
        try {
          await supabase.auth.setSession({
            access_token: response.data.session.access_token,
            refresh_token: response.data.session.refresh_token,
          })
          if (DEBUG_AUTH) console.log('Session explicitly set after sign in')
        } catch (e) {
          console.error('Error setting session after sign in:', e)
        }
        
        // Check if profile is complete
        try {
          const { data: profile } = await supabase
            .from('profiles')
            .select('username')
            .eq('id', response.data.session.user.id)
            .single()
            
          setIsProfileComplete(!!profile?.username)
          
          // Handle redirect after successful login
          const params = new URLSearchParams(window.location.search)
          const redirectPath = params.get('redirect')
          
          if (redirectPath) {
            if (DEBUG_AUTH) console.log('Redirecting to:', redirectPath)
            router.push(getPath(redirectPath))
          } else if (!profile?.username) {
            if (DEBUG_AUTH) console.log('Profile not complete, redirecting to profile setup')
            router.push(getPath('/dashboard/profile-setup'))
          } else {
            if (DEBUG_AUTH) console.log('Redirecting to dashboard')
            router.push(getPath('/dashboard'))
          }
        } catch (error) {
          console.error('Error checking profile on sign in:', error)
          router.push(getPath('/dashboard'))
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
      localStorage.removeItem('supabase-auth')
      
      // Navigate to login page
      router.push(getPath('/dashboard/login'))
      
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