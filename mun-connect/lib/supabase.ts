import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Create Supabase client with proper redirect configuration
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    flowType: 'pkce',
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
})

// Initialize session if in browser environment
if (typeof window !== 'undefined') {
  // This ensures the session is properly initialized
  supabase.auth.getSession().then(({ data }) => {
    if (data && data.session) {
      // Session exists, but let the auth context handle redirects
      console.log('Session initialized')
    }
  })
}

export type Database = {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          username: string
          full_name: string | null
          bio: string | null
          avatar_url: string | null
          country: string | null
          interests: string[] | null
          conference_experience: string[] | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          username: string
          full_name?: string | null
          bio?: string | null
          avatar_url?: string | null
          country?: string | null
          interests?: string[] | null
          conference_experience?: string[] | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          username?: string
          full_name?: string | null
          bio?: string | null
          avatar_url?: string | null
          country?: string | null
          interests?: string[] | null
          conference_experience?: string[] | null
          created_at?: string
          updated_at?: string
        }
      }
    }
  }
} 