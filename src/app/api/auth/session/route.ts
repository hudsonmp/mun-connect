import { NextResponse } from "next/server"

export async function GET() {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/api/auth/session`, {
      method: "GET",
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || "Session not found" },
        { status: response.status }
      )
    }

    return NextResponse.json(data, { status: 200 })
  } catch (error) {
    console.error("Session error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
} 