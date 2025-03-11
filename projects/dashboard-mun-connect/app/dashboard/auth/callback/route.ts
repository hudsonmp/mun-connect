import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

// Debug flag
const DEBUG_AUTH = true

// Base path from next.config
const BASE_PATH = '/dashboard'

// Mark as dynamic to ensure we don't cache the auth response
export const dynamic = 'force-dynamic'

// Helper to create proper paths accounting for the basePath
const getPath = (path: string) => {
  // If the path already starts with the base path, don't duplicate it
  if (path.startsWith(BASE_PATH)) {
    return path
  }
  // If it's just a slash, return the base path
  if (path === '/') {
    return BASE_PATH
  }
  // Otherwise, combine them properly
  return `${BASE_PATH}${path.startsWith('/') ? path : '/' + path}`
}

/**
 * Handle authentication callback requests for email verification, password reset, etc.
 */
export async function GET(request: NextRequest) {
  // Get the URL and its parameters
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  const errorDescription = requestUrl.searchParams.get('error_description')
  const next = requestUrl.searchParams.get('next') || '/'
  
  // Create properly formatted redirect paths
  const formattedNext = getPath(next)
  
  if (DEBUG_AUTH) {
    console.log('🔐 Auth callback triggered with:')
    console.log('- URL:', request.url)
    console.log('- Code exists:', !!code)
    console.log('- Error:', error || 'none')
    console.log('- Original redirect destination:', next)
    console.log('- Formatted redirect destination:', formattedNext)
    console.log('- Headers:', Object.fromEntries([...request.headers.entries()]))
  }
  
  // Handle errors from Supabase
  if (error) {
    console.error('Auth error in callback:', error, errorDescription)
    return NextResponse.redirect(
      new URL(`${BASE_PATH}/login?error=${error}&error_description=${encodeURIComponent(errorDescription || '')}`, requestUrl.origin)
    )
  }
  
  // If there's no auth code, redirect to login
  if (!code) {
    if (DEBUG_AUTH) console.log('No code parameter found in callback URL')
    return NextResponse.redirect(new URL(`${BASE_PATH}/login`, requestUrl.origin))
  }
  
  try {
    if (DEBUG_AUTH) console.log('Exchanging code for session')
    
    // Create a Supabase client with server cookies
    const cookieStore = await cookies()
    
    // Create the Supabase client
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL || '',
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
      {
        cookies: {
          get(name) {
            return cookieStore.get(name)?.value
          },
          set(name, value, options) {
            try {
              cookieStore.set(name, value, options as any)
            } catch (error) {
              console.error(`Error setting cookie ${name}:`, error)
            }
          },
          remove(name, options) {
            try {
              cookieStore.set(name, '', { ...options as any, maxAge: 0 })
            } catch (error) {
              console.error(`Error removing cookie ${name}:`, error)
            }
          },
        },
      }
    )
    
    // Exchange the code for a session
    const { data, error } = await supabase.auth.exchangeCodeForSession(code)
    
    if (error) {
      console.error('Error exchanging code for session:', error)
      return NextResponse.redirect(
        new URL(`${BASE_PATH}/login?error=session_error&error_description=${encodeURIComponent(error.message)}`, requestUrl.origin)
      )
    }
    
    if (DEBUG_AUTH) {
      console.log('🎉 Auth successful, user authenticated')
      console.log('Session data:', data.session ? 'Session exists' : 'No session')
      
      if (data.session) {
        console.log('User ID:', data.session.user.id)
        console.log('Email:', data.session.user.email)
        console.log('Session expires:', data.session.expires_at 
          ? new Date(data.session.expires_at * 1000).toLocaleString() 
          : 'No expiry set')
      }
    }
    
    // Check if user profile exists, create if it doesn't
    if (data.session) {
      try {
        const { data: profileData, error: profileError } = await supabase
          .from('profiles')
          .select('id, username')
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
            
          // Redirect to profile setup if profile was just created
          const setupUrl = new URL(`${BASE_PATH}/profile-setup`, requestUrl.origin)
          
          if (DEBUG_AUTH) console.log('Redirecting new user to profile setup:', setupUrl.toString())
          
          const response = NextResponse.redirect(setupUrl)
          response.headers.set('Cache-Control', 'no-store, max-age=0')
          return response
        }
        
        // If profile exists but no username, redirect to profile setup
        if (!profileData.username) {
          const setupUrl = new URL(`${BASE_PATH}/profile-setup`, requestUrl.origin)
          
          if (DEBUG_AUTH) console.log('Redirecting to profile setup (no username):', setupUrl.toString())
          
          const response = NextResponse.redirect(setupUrl)
          response.headers.set('Cache-Control', 'no-store, max-age=0')
          return response
        }
      } catch (e) {
        console.error('Error checking/creating profile:', e)
      }
    }
    
    // Set a cookie to indicate successful auth
    const dashboardUrl = new URL(formattedNext, requestUrl.origin)
    
    // Add a debug parameter to help track where the user came from
    dashboardUrl.searchParams.set('auth_source', 'callback')
    
    if (DEBUG_AUTH) console.log('Redirecting to:', dashboardUrl.toString())
    
    const response = NextResponse.redirect(dashboardUrl)
    
    // Set cache headers to prevent caching
    response.headers.set('Cache-Control', 'no-store, max-age=0')
    response.headers.set('Pragma', 'no-cache')
    response.headers.set('Expires', '0')
    
    return response
  } catch (error) {
    console.error('Exception in auth callback:', error)
    return NextResponse.redirect(
      new URL(`${BASE_PATH}/login?error=callback_exception`, requestUrl.origin)
    )
  }
} 