import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  // Get the URL and its parameters
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = requestUrl.searchParams.get('next') || '/dashboard'
  
  if (code) {
    try {
      // Create a Supabase client
      const cookieStore = cookies()
      const supabase = createRouteHandlerClient({ cookies: () => cookieStore })
      
      // Exchange the code for a session
      const { data, error } = await supabase.auth.exchangeCodeForSession(code)
      
      if (error) {
        console.error('Error exchanging code for session:', error)
        return NextResponse.redirect(new URL('/dashboard/login?error=auth_error', requestUrl.origin))
      }
      
      // Clear any URL fragments
      if (requestUrl.hash) {
        requestUrl.hash = ''
      }
      
      console.log('Auth successful, redirecting to dashboard')
      
      // Redirect to the dashboard
      return NextResponse.redirect(new URL('/dashboard', requestUrl.origin))
    } catch (error) {
      console.error('Exception in auth callback:', error)
      return NextResponse.redirect(new URL('/dashboard/login?error=auth_exception', requestUrl.origin))
    }
  }
  
  // If there's no code, redirect to login
  return NextResponse.redirect(new URL('/dashboard/login', requestUrl.origin))
} 