import { NextResponse } from 'next/server'
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
        { success: false, error: 'Email and password are required' },
        { status: 400 }
      )
    }

    // Sign in with Supabase
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      console.error('Signin error:', error.message)
      return NextResponse.json(
        { success: false, error: error.message },
        { status: error.status || 401 }
      )
    }

    // Only fetch profile if sign-in was successful
    let profile = null
    if (data?.user?.id) {
      const { data: profileData, error: profileError } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', data.user.id)
        .single()

      if (profileError) {
        console.error('Profile fetch error:', profileError.message)
      } else {
        profile = profileData
      }
    }

    // Return success response
    return NextResponse.json({
      success: true,
      session: data.session,
      user: data.user,
      profile
    }, { status: 200 })
    
  } catch (err: any) {
    console.error('Unexpected error in signin API:', err)
    return NextResponse.json(
      { success: false, error: 'An unexpected error occurred' },
      { status: 500 }
    )
  }
} 