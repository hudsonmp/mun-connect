import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export async function GET() {
  try {
    // Log environment variables
    console.log('SUPABASE_URL:', process.env.NEXT_PUBLIC_SUPABASE_URL);
    console.log('Has ANON_KEY:', !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
    
    // Create a direct client for testing
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
    
    const directClient = createClient(
      supabaseUrl,
      supabaseAnonKey,
      {
        auth: {
          persistSession: false
        }
      }
    );
    
    // Test Supabase connection
    const { data, error } = await directClient.auth.getSession();

    return NextResponse.json({
      message: 'Debug route',
      env: {
        supabaseUrl,
        hasAnonKey: !!supabaseAnonKey,
        nodeEnv: process.env.NODE_ENV
      },
      session: data?.session ? { 
        user: {
          id: data.session.user.id,
          email: data.session.user.email
        },
        expires_at: data.session.expires_at
      } : null,
      error: error ? {
        message: error.message,
        name: error.name,
        status: error.status
      } : null
    });
  } catch (error: any) {
    console.error('Debug route error:', error);
    
    return NextResponse.json({
      message: 'Error in debug route',
      error: {
        message: error.message,
        name: error.name,
        stack: error.stack
      }
    }, { status: 500 });
  }
} 