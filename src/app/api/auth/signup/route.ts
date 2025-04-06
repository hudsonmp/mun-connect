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

export async function POST(request: Request) {
  try {
    // Parse and validate request body
    const body = await request.json().catch(() => ({}))
    const { email, password } = body

    if (!email || !password) {
      return NextResponse.json(
        { success: false, error: "Email and password are required" },
        { status: 400 }
      )
    }

    // Basic password validation
    if (password.length < 6) {
      return NextResponse.json(
        { success: false, error: "Password must be at least 6 characters" },
        { status: 400 }
      )
    }

    // Sign up with Supabase
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    })

    if (error) {
      console.error('Signup error:', error.message)
      return NextResponse.json(
        { success: false, error: error.message },
        { status: error.status || 400 }
      )
    }

    // Create a profile for the new user
    if (data?.user?.id) {
      const { error: profileError } = await supabase
        .from('profiles')
        .insert({
          id: data.user.id,
          username: email.split('@')[0],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })

      if (profileError) {
        console.error('Profile creation error:', profileError.message)
        // We don't fail the signup if profile creation fails
      }
    }

    return NextResponse.json(
      { 
        success: true, 
        message: "Account created successfully",
        user: data.user
      }, 
      { status: 201 }
    )
  } catch (err: any) {
    console.error("Unexpected error in signup API:", err)
    return NextResponse.json(
      { success: false, error: "An unexpected error occurred" },
      { status: 500 }
    )
  }
} 