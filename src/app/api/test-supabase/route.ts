import { NextResponse } from "next/server"
import { createClient } from '@supabase/supabase-js'

export async function GET() {
  try {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    return NextResponse.json({
      url: supabaseUrl,
      hasKey: !!supabaseAnonKey,
    })
  } catch (error) {
    console.error("Test error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
} 