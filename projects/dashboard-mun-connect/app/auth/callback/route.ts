import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  // Get the URL and its parameters
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = requestUrl.searchParams.get('next') || '/dashboard'
  
  console.log('Auth callback triggered, code exists:', !!code)
  console.log('Redirect destination:', next)
  
  if (code) {
    // Create a Supabase client
    const cookieStore = cookies()
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore })
    
    try {
      // Exchange the code for a session
      const { data, error } = await supabase.auth.exchangeCodeForSession(code)
      
      if (error) {
        console.error('Error exchanging code for session:', error)
        return NextResponse.redirect(new URL('/dashboard/login?error=auth_exchange_failed', requestUrl.origin))
      }

      console.log('Session successfully obtained:', !!data.session)
      
      // Clear any URL fragments that might have been added
      if (requestUrl.hash) {
        requestUrl.hash = ''
      }
      
      // Redirect to the dashboard or specified page with cache control
      const response = NextResponse.redirect(new URL(next, requestUrl.origin))
      response.headers.set('Cache-Control', 'no-store, max-age=0')
      return response
    } catch (err) {
      console.error('Exception in auth callback:', err)
      return NextResponse.redirect(new URL('/dashboard/login?error=auth_exception', requestUrl.origin))
    }
  }
  
  // If there's no code, redirect to the login page
  console.log('No code provided, redirecting to login')
  return NextResponse.redirect(new URL('/dashboard/login', requestUrl.origin))
} 