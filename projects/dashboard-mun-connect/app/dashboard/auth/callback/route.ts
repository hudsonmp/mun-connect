import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

// Debug flag
const DEBUG_AUTH = true

// Mark as dynamic to ensure we don't cache the auth response
export const dynamic = 'force-dynamic'

/**
 * Handle authentication callback requests for email verification, password reset, etc.
 */
export async function GET(request: NextRequest) {
  // Get the URL and its parameters
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  const errorDescription = requestUrl.searchParams.get('error_description')
  
  if (DEBUG_AUTH) {
    console.log('Auth callback triggered with:')
    console.log('- URL:', request.url)
    console.log('- Code exists:', !!code)
    console.log('- Error:', error || 'none')
  }
  
  // Handle errors from Supabase
  if (error) {
    console.error('Auth error in callback:', error, errorDescription)
    return NextResponse.redirect(
      new URL(`/dashboard/login?error=${error}&error_description=${encodeURIComponent(errorDescription || '')}`, requestUrl.origin)
    )
  }
  
  // If there's no auth code, redirect to login
  if (!code) {
    if (DEBUG_AUTH) console.log('No code parameter found in callback URL')
    return NextResponse.redirect(new URL('/dashboard/login', requestUrl.origin))
  }
  
  try {
    if (DEBUG_AUTH) console.log('Exchanging code for session')
    
    // Create a Supabase client with server cookies
    const cookieStore = cookies()
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore })
    
    // Exchange the code for a session
    const { data, error } = await supabase.auth.exchangeCodeForSession(code)
    
    if (error) {
      console.error('Error exchanging code for session:', error)
      return NextResponse.redirect(
        new URL(`/dashboard/login?error=session_error&error_description=${encodeURIComponent(error.message)}`, requestUrl.origin)
      )
    }
    
    if (DEBUG_AUTH) {
      console.log('Auth successful, user authenticated')
      console.log('Session data:', data.session ? 'Session exists' : 'No session')
      
      if (data.session) {
        console.log('User ID:', data.session.user.id)
        console.log('Email:', data.session.user.email)
      }
    }
    
    // Check if user profile exists, create if it doesn't
    if (data.session) {
      try {
        const { data: profileData, error: profileError } = await supabase
          .from('profiles')
          .select('id')
          .eq('id', data.session.user.id)
          .single()
          
        if (profileError || !profileData) {
          if (DEBUG_AUTH) console.log('Creating profile for user')
          
          // Create a default profile
          const defaultUsername = `user_${Math.random().toString(36).substring(2, 7)}`
          await supabase
            .from('profiles')
            .upsert({
              id: data.session.user.id,
              username: defaultUsername,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            })
        }
      } catch (e) {
        console.error('Error checking/creating profile:', e)
      }
    }
    
    // Redirect to the dashboard
    return NextResponse.redirect(new URL('/dashboard', requestUrl.origin))
  } catch (error) {
    console.error('Exception in auth callback:', error)
    return NextResponse.redirect(
      new URL('/dashboard/login?error=callback_exception', requestUrl.origin)
    )
  }
} 