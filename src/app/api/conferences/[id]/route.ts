import { NextResponse } from "next/server"
import { createClient } from '@supabase/supabase-js'

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const supabase = createClient(supabaseUrl, supabaseKey)

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const userId = request.headers.get("user-id")
  const { id } = params

  if (!userId) {
    return NextResponse.json(
      { error: "User ID is required" },
      { status: 400 }
    )
  }

  try {
    const { data, error } = await supabase
      .from('conferences')
      .select('*')
      .eq('id', id)
      .eq('user_id', userId)
      .single()

    if (error) throw error
    if (!data) {
      return NextResponse.json(
        { error: "Conference not found" },
        { status: 404 }
      )
    }

    return NextResponse.json(data, { status: 200 })
  } catch (error: any) {
    console.error("Error fetching conference:", error)
    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: Request,
  { params }: { params: { id: string } }
) {
  const userId = request.headers.get("user-id")
  const { id } = params

  if (!userId) {
    return NextResponse.json(
      { error: "User ID is required" },
      { status: 400 }
    )
  }

  try {
    const body = await request.json()
    const updateData = {
      ...body,
      updated_at: new Date().toISOString()
    }

    const { data, error } = await supabase
      .from('conferences')
      .update(updateData)
      .eq('id', id)
      .eq('user_id', userId)
      .select()
      .single()

    if (error) throw error
    if (!data) {
      return NextResponse.json(
        { error: "Conference not found" },
        { status: 404 }
      )
    }

    return NextResponse.json(data, { status: 200 })
  } catch (error: any) {
    console.error("Error updating conference:", error)
    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { id: string } }
) {
  const userId = request.headers.get("user-id")
  const { id } = params

  if (!userId) {
    return NextResponse.json(
      { error: "User ID is required" },
      { status: 400 }
    )
  }

  try {
    const { error } = await supabase
      .from('conferences')
      .delete()
      .eq('id', id)
      .eq('user_id', userId)

    if (error) throw error

    return NextResponse.json({ success: true }, { status: 200 })
  } catch (error: any) {
    console.error("Error deleting conference:", error)
    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    )
  }
} 