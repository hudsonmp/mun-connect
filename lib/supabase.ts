import { createClient } from '@supabase/supabase-js'
import type { Database } from './database.types'

// Check if environment variables are defined
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables. Please check your .env file.')
}

// Create Supabase client with proper redirect configuration
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

// Initialize session if in browser environment
if (typeof window !== 'undefined') {
  // This ensures the session is properly initialized
  supabase.auth.getSession().then(({ data, error }) => {
    if (error) {
      console.error('Error initializing session:', error)
    } else if (data && data.session) {
      // Session exists, but let the auth context handle redirects
      console.log('Session initialized')
    }
  }).catch(err => {
    console.error('Exception initializing session:', err)
  })

  // Set up error handling for network/storage issues
  window.addEventListener('storage', (event) => {
    if (event.key === 'supabase-auth') {
      // Refresh the page to ensure auth state is consistent
      window.location.reload()
    }
  })
}

// Export the database type
export type { Database } 