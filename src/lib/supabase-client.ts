import { createClient } from '@supabase/supabase-js'

// Get environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

// Validate environment variables
if (!supabaseUrl) {
  console.error('CRITICAL ERROR: Missing NEXT_PUBLIC_SUPABASE_URL environment variable')
  // In development, provide a helpful message
  if (process.env.NODE_ENV !== 'production') {
    console.error('Make sure you have a .env.local file with NEXT_PUBLIC_SUPABASE_URL defined')
  }
}

if (!supabaseKey) {
  console.error('CRITICAL ERROR: Missing NEXT_PUBLIC_SUPABASE_ANON_KEY environment variable')
  // In development, provide a helpful message
  if (process.env.NODE_ENV !== 'production') {
    console.error('Make sure you have a .env.local file with NEXT_PUBLIC_SUPABASE_ANON_KEY defined')
  }
}

// Create a single supabase client to be shared across the application
export const supabase = createClient(supabaseUrl || '', supabaseKey || '', {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    storageKey: 'mun-connect-auth-storage',
    detectSessionInUrl: true,
    flowType: 'pkce',
  }
})

// Export initialization status for checking in other components
export const isSupabaseInitialized = !!(supabaseUrl && supabaseKey)

// Add a default export as well for better compatibility
export default supabase 