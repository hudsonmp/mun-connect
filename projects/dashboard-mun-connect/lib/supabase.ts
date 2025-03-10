"use client"

import { createClient } from '@supabase/supabase-js'
import type { Database } from './database.types'

// Check if environment variables are defined
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const redirectUrl = process.env.NEXT_PUBLIC_REDIRECT_URL || 'https://mun-connect-dashboard.vercel.app/dashboard'

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables. Please check your .env file.')
}

// Create a more robust Supabase client configuration
export const supabase = createClient<Database>(
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

// Enhanced session initialization for browser environment
if (typeof window !== 'undefined') {
  const initializeSession = async () => {
    try {
      // Try to get an active session
      const { data, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Error initializing session:', error)
        return
      }
      
      if (data?.session) {
        console.log('Session initialized successfully')
        
        // Explicitly set the session in case there are any issues with automatic handling
        await supabase.auth.setSession({
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
        })
        
        // Store auth state in localStorage as a backup mechanism
        localStorage.setItem('authState', JSON.stringify({
          isAuthenticated: true,
          userId: data.session.user.id,
          lastUpdated: new Date().toISOString()
        }))
      } else {
        console.log('No active session found')
        localStorage.removeItem('authState')
      }
    } catch (err) {
      console.error('Exception initializing session:', err)
    }
  }
  
  // Run the initialization
  initializeSession()
  
  // Set default redirect URL for email confirmations
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('supabaseRedirectUrl', redirectUrl)
  }
  
  // Listen for auth state changes to ensure consistency
  supabase.auth.onAuthStateChange((event, session) => {
    console.log('Auth state changed:', event)
    
    if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
      // Update the auth state in localStorage
      localStorage.setItem('authState', JSON.stringify({
        isAuthenticated: true,
        userId: session?.user.id,
        lastUpdated: new Date().toISOString()
      }))
    } else if (event === 'SIGNED_OUT') {
      // Clear the auth state
      localStorage.removeItem('authState')
    }
  })
  
  // Set up error handling for storage issues
  window.addEventListener('storage', (event) => {
    if (event.key === 'supabase-auth') {
      // Refresh the page to ensure auth state is consistent
      window.location.reload()
    }
  })
}

// Export the database type
export type { Database } 