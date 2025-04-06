import { NextResponse } from "next/server"
import { createClient } from '@supabase/supabase-js'
import { cookies } from 'next/headers'

// Initialize Supabase client with URL and anon key
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export async function GET(request: Request) {
  try {
    // Create a Supabase client for the request
    const cookieStore = cookies()
    const supabase = createClient(supabaseUrl, supabaseKey, {
      global: {
        headers: {
          Cookie: cookieStore.toString(),
        },
      },
    })

    // Get user from session
    const { data: { session } } = await supabase.auth.getSession()
    const userId = session?.user?.id

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { data, error } = await supabase
      .from('conferences')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching conferences:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    return NextResponse.json(data || [])
  } catch (err: any) {
    console.error('Error in conferences API:', err)
    return NextResponse.json({ error: err.message }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    // Create a Supabase client for the request
    const cookieStore = cookies()
    const supabase = createClient(supabaseUrl, supabaseKey, {
      global: {
        headers: {
          Cookie: cookieStore.toString(),
        },
      },
    })

    // Get user from session
    const { data: { session } } = await supabase.auth.getSession()
    const userId = session?.user?.id

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    
    // Ensure we use the authenticated user's ID
    const conferenceData = {
      ...body,
      user_id: userId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    
    const { data, error } = await supabase
      .from('conferences')
      .insert(conferenceData)
      .select()
      .single()

    if (error) {
      console.error("Error creating conference:", error)
      throw error
    }

    return NextResponse.json(data, { status: 201 })
  } catch (error: any) {
    console.error("Error creating conference:", error)
    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    )
  }
} 