import { NextResponse } from "next/server"

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
    
    const response = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/api/ai/improve-document`, {
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
        { error: errorData.error || "Failed to improve document" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data, { status: 200 })
  } catch (error) {
    console.error("Error improving document with AI:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
} 