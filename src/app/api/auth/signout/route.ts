import { NextResponse } from "next/server"

export async function POST() {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/api/auth/signout`, {
      method: "POST",
    })

    if (!response.ok) {
      const data = await response.json()
      return NextResponse.json(
        { error: data.error || "Failed to sign out" },
        { status: response.status }
      )
    }

    return NextResponse.json(
      { message: "Successfully signed out" },
      { status: 200 }
    )
  } catch (error) {
    console.error("Signout error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
} 