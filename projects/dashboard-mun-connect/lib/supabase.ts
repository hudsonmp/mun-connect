"use client"

import { createClient } from '@supabase/supabase-js'
import type { Database } from './database.types'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Debug flag for auth issues
const DEBUG_AUTH = true

// Get environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const redirectUrl = process.env.NEXT_PUBLIC_REDIRECT_URL || 'https://mun-connect-dashboard.vercel.app/dashboard/auth/callback'

// Validate environment variables
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables. Check your .env file.')
  if (DEBUG_AUTH) {
    console.log('NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl)
    console.log('NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey ? '[REDACTED]' : 'undefined')
  }
}

// Create Supabase client (legacy way)
export const supabaseAdmin = createClient<Database>(
  supabaseUrl || '',
  supabaseAnonKey || '',
  {
    auth: {
      flowType: 'pkce',
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
      storage: typeof window !== 'undefined' ? window.localStorage : undefined,
      storageKey: 'supabase-auth',
    },
  }
)

// Create Supabase client with the newer approach
export const supabase = typeof window !== 'undefined' 
  ? createClientComponentClient<Database>({
      supabaseUrl: supabaseUrl,
      supabaseKey: supabaseAnonKey,
    })
  : supabaseAdmin // Fallback for server contexts

// Initialize session and set up error recovery
if (typeof window !== 'undefined') {
  // Set up session initialization and error handling
  const initializeSession = async () => {
    try {
      if (DEBUG_AUTH) console.log('Initializing Supabase client and session')
      
      // Try to get current session
      const { data, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Error initializing session:', error)
        return
      }
      
      if (data?.session) {
        if (DEBUG_AUTH) {
          console.log('Session initialized successfully')
          const expiresAt = data.session.expires_at 
            ? new Date(data.session.expires_at * 1000) 
            : 'No expiry'
          console.log(`Session expires at: ${expiresAt}`)
        }
        
        // Ensure the session is properly set in Supabase
        try {
          await supabase.auth.setSession({
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
          })
          if (DEBUG_AUTH) console.log('Session explicitly set')
        } catch (err) {
          console.error('Error setting session:', err)
        }
        
        // Store auth state in localStorage as a backup mechanism
        localStorage.setItem('authState', JSON.stringify({
          isAuthenticated: true,
          userId: data.session.user.id,
          lastUpdated: new Date().toISOString()
        }))
      } else {
        if (DEBUG_AUTH) console.log('No active session found during initialization')
        localStorage.removeItem('authState')
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
          lastUpdated: new Date().toISOString()
        }))
      }
    } else if (event === 'SIGNED_OUT') {
      if (DEBUG_AUTH) console.log('User signed out')
      localStorage.removeItem('authState')
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
}

// Export the database type
export type { Database } 