import { NextResponse } from "next/server"
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase environment variables')
}

const supabase = createClient(supabaseUrl, supabaseKey)

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const userId = searchParams.get('userId')

    if (!userId) {
      return NextResponse.json({ error: 'User ID is required' }, { status: 400 })
    }

    const { data, error } = await supabase
      .from('documents')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching documents:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    return NextResponse.json(data || [])
  } catch (err: any) {
    console.error('Error in documents API:', err)
    return NextResponse.json({ error: err.message }, { status: 500 })
  }
}

export async function POST(request: Request) {
  const userId = request.headers.get("user-id")

  if (!userId) {
    return NextResponse.json(
      { error: "User ID is required" },
      { status: 400 }
    )
  }

  try {
    const body = await request.json()
    
    const response = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/api/documents`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "user-id": userId
      },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(
        { error: errorData.error || "Failed to create document" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error("Error creating document:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
} 