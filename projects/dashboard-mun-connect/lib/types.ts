import { User as SupabaseUser } from '@supabase/supabase-js'

export interface User extends SupabaseUser {
  username?: string
  full_name?: string
  avatar_url?: string
} 