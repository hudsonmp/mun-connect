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

// Set callback URL for Supabase auth
if (typeof window !== 'undefined') {
  supabase.auth.setSession({
    access_token: '',
    refresh_token: '',
  })
  supabase.auth.onAuthStateChange((event) => {
    if (event === 'SIGNED_IN') {
      window.location.href = '/dashboard'
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