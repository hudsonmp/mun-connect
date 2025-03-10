"use client"

import { createClient } from '@supabase/supabase-js'
import type { Database } from './database.types'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Debug flag for auth issues
const DEBUG_AUTH = true

// Get environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const redirectUrl = process.env.NEXT_PUBLIC_REDIRECT_URL || 'https://mun-connect-dashboard.vercel.app/auth/callback'

// Validate environment variables
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables.')
  if (DEBUG_AUTH) {
    console.log('NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl || 'undefined')
    console.log('NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey ? '[REDACTED]' : 'undefined')
    console.log('Environment:', process.env.NODE_ENV)
  }
}

// Create Supabase client with consistent auth settings for admin client
const authConfig = {
  auth: {
    flowType: 'pkce' as const,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    storage: typeof window !== 'undefined' ? window.localStorage : undefined,
    storageKey: 'supabase-auth',
  }
}

// Create Supabase admin client
export const supabaseAdmin = createClient<Database>(
  supabaseUrl || '',
  supabaseAnonKey || '',
  authConfig
)

// Create Supabase client with the newer approach 
export const supabase = typeof window !== 'undefined' 
  ? createClientComponentClient<Database>({
      supabaseUrl: supabaseUrl,
      supabaseKey: supabaseAnonKey,
      cookieOptions: {
        name: 'supabase-auth',
        path: '/',
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production'
      }
    })
  : supabaseAdmin // Fallback for server contexts

// Initialize session and set up error recovery
if (typeof window !== 'undefined') {
  console.log('Initializing Supabase client...')
  
  // Set up session initialization and error handling
  const initializeSession = async () => {
    try {
      if (DEBUG_AUTH) console.log('Initializing Supabase client and session')
      
      // First check if we have a stored auth state that claims we're authenticated
      const storedAuthState = localStorage.getItem('authState');
      let localAuthClaim = false;
      let localUserId = null;
      
      if (storedAuthState) {
        try {
          const authState = JSON.parse(storedAuthState);
          localUserId = authState.userId;
          const lastUpdated = new Date(authState.lastUpdated);
          const now = new Date();
          const hoursSinceUpdate = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60);
          
          // If auth state is recent and claims authentication
          if (hoursSinceUpdate < 24 && authState.isAuthenticated && authState.userId) {
            localAuthClaim = true;
            if (DEBUG_AUTH) console.log('Found recent local auth state claiming authentication for user:', authState.userId);
            
            // Update some metadata in the stored auth state
            const updatedAuthState = {
              ...authState,
              lastUpdated: new Date().toISOString(),
              currentUrl: window.location.href,
              userAgent: navigator.userAgent,
              hasSupabaseAuth: false // Will update this later if we find a session
            };
            localStorage.setItem('authState', JSON.stringify(updatedAuthState));
          }
        } catch (e) {
          console.error('Error parsing auth state:', e);
          // Clear corrupted auth state
          localStorage.removeItem('authState');
        }
      }
      
      // Try to get current session
      const { data, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Error initializing session:', error)
        
        // If we have a local auth claim but Supabase session failed, try to restore it
        if (localAuthClaim && localUserId) {
          if (DEBUG_AUTH) console.log('Attempting to recover session based on local auth claim');
          try {
            const refreshResult = await supabase.auth.refreshSession();
            if (refreshResult.data?.session) {
              if (DEBUG_AUTH) console.log('Successfully refreshed session from local auth claim');
              // Update auth state to indicate we have a Supabase session
              const currentAuthState = JSON.parse(localStorage.getItem('authState') || '{}');
              localStorage.setItem('authState', JSON.stringify({
                ...currentAuthState,
                hasSupabaseAuth: true,
                lastUpdated: new Date().toISOString()
              }));
            }
          } catch (refreshError) {
            console.error('Failed to refresh session:', refreshError);
          }
        }
        
        return
      }
      
      if (data?.session) {
        if (DEBUG_AUTH) {
          console.log('Session initialized successfully')
          const expiresAt = data.session.expires_at 
            ? new Date(data.session.expires_at * 1000) 
            : 'No expiry'
          console.log(`Session expires at: ${expiresAt}`)
          console.log(`User ID: ${data.session.user.id}`)
        }
        
        // Ensure the session is properly set in Supabase
        try {
          await supabase.auth.setSession({
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
          })
          if (DEBUG_AUTH) console.log('Session explicitly set')
          
          // Ensure localStorage is synced with this valid session
          localStorage.setItem('authState', JSON.stringify({
            isAuthenticated: true,
            userId: data.session.user.id,
            hasSupabaseAuth: true,
            lastUpdated: new Date().toISOString(),
            currentUrl: window.location.href,
            userAgent: navigator.userAgent
          }))
        } catch (err) {
          console.error('Error setting session:', err)
        }
      } else {
        if (DEBUG_AUTH) console.log('No active session found during initialization')
        
        // If Supabase has no session but we have a local auth claim, 
        // try one more time to refresh the session
        if (localAuthClaim && localUserId) {
          if (DEBUG_AUTH) console.log('Auth state mismatch: Local claims auth but Supabase has no session. Attempting final refresh.');
          try {
            const refreshResult = await supabase.auth.refreshSession();
            if (refreshResult.data?.session) {
              if (DEBUG_AUTH) console.log('Successfully refreshed session in final attempt');
              
              // Update auth state to indicate we have a Supabase session
              localStorage.setItem('authState', JSON.stringify({
                isAuthenticated: true,
                userId: refreshResult.data.session.user.id,
                hasSupabaseAuth: true,
                lastUpdated: new Date().toISOString(),
                currentUrl: window.location.href,
                userAgent: navigator.userAgent
              }));
              
              return;
            } else {
              // If refresh failed, clear the auth state
              if (DEBUG_AUTH) console.log('Failed to refresh session in final attempt, clearing local storage');
              localStorage.removeItem('authState');
              localStorage.removeItem('supabase-auth');
              
              // Force reload to ensure clean state
              if (!window.location.pathname.includes('/login')) {
                if (DEBUG_AUTH) console.log('Redirecting to login after auth failure');
                window.location.href = '/dashboard/login';
              }
            }
          } catch (refreshError) {
            console.error('Failed in final refresh attempt:', refreshError);
            localStorage.removeItem('authState');
            localStorage.removeItem('supabase-auth');
          }
        }
      }
    } catch (err) {
      console.error('Exception initializing session:', err)
    }
  }
  
  // Run the initialization
  initializeSession()
  
  // Store the redirect URL for reference in other components
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('supabaseRedirectUrl', redirectUrl)
    if (DEBUG_AUTH) console.log('Redirect URL stored:', redirectUrl)
  }
  
  // Listen for auth state changes
  supabase.auth.onAuthStateChange((event, session) => {
    if (DEBUG_AUTH) console.log('Auth state changed in Supabase client:', event)
    
    if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
      if (DEBUG_AUTH) console.log('User signed in or token refreshed')
      
      // Update backup auth state
      if (session) {
        localStorage.setItem('authState', JSON.stringify({
          isAuthenticated: true,
          userId: session.user.id,
          hasSupabaseAuth: true,
          lastUpdated: new Date().toISOString(),
          currentUrl: window.location.href,
          userAgent: navigator.userAgent
        }))
      }
    } else if (event === 'SIGNED_OUT') {
      if (DEBUG_AUTH) console.log('User signed out')
      localStorage.removeItem('authState')
      localStorage.removeItem('supabase-auth')
    }
  })
  
  // Set up error handling for storage events
  window.addEventListener('storage', (event) => {
    if (event.key === 'supabase-auth' && event.newValue !== event.oldValue) {
      if (DEBUG_AUTH) console.log('Storage event: auth state changed externally')
      
      // Refresh the page to sync auth state
      window.location.reload()
    }
  })
  
  // Add a recovery mechanism for stuck auth initialization
  setTimeout(() => {
    const authStateRaw = localStorage.getItem('authState');
    if (authStateRaw) {
      try {
        const authState = JSON.parse(authStateRaw);
        if (authState.isAuthenticated && !authState.hasSupabaseAuth) {
          if (DEBUG_AUTH) console.log('Detected stuck auth initialization after timeout');
          // Try to refresh the session
          supabase.auth.refreshSession().then(({ data, error }) => {
            if (error) {
              if (DEBUG_AUTH) console.log('Failed to refresh session after timeout:', error);
              if (!window.location.pathname.includes('/login')) {
                window.location.href = '/dashboard/login';
              }
            } else if (data.session) {
              if (DEBUG_AUTH) console.log('Successfully refreshed session after timeout');
              localStorage.setItem('authState', JSON.stringify({
                ...authState,
                hasSupabaseAuth: true,
                lastUpdated: new Date().toISOString()
              }));
              // Reload the page to ensure all components reflect the correct auth state
              window.location.reload();
            }
          });
        }
      } catch (e) {
        console.error('Error parsing auth state during recovery:', e);
      }
    }
  }, 5000); // Check after 5 seconds
}

// Export the database type
export type { Database } 