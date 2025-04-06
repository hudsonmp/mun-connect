import { NextResponse } from "next/server"
import { createClient } from '@supabase/supabase-js'

// Get environment variables with proper validation
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

// Validate environment variables
if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase environment variables')
}

// Create Supabase client with proper fallbacks
const supabase = createClient(supabaseUrl || '', supabaseKey || '')

export async function POST() {
  try {
    // Sign out with Supabase directly
    const { error } = await supabase.auth.signOut()

    if (error) {
      console.error('Signout error:', error.message)
      return NextResponse.json(
        { success: false, error: error.message },
        { status: error.status || 400 }
      )
    }

    return NextResponse.json(
      { success: true, message: "Successfully signed out" },
      { status: 200 }
    )
  } catch (err: any) {
    console.error("Unexpected error in signout API:", err)
    return NextResponse.json(
      { success: false, error: "An unexpected error occurred" },
      { status: 500 }
    )
  }
} 