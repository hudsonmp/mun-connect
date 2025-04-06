import { NextResponse } from "next/server"

export async function PUT(request: Request) {
  const userId = request.headers.get("user-id")

  if (!userId) {
    return NextResponse.json(
      { error: "User ID is required" },
      { status: 400 }
    )
  }

  try {
    const body = await request.json()
    
    if (!body.awards_count && body.awards_count !== 0) {
      return NextResponse.json(
        { error: "Awards count is required" },
        { status: 400 }
      )
    }
    
    const response = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/api/user-stats/awards`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "user-id": userId
      },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(
        { error: errorData.error || "Failed to update awards count" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data, { status: 200 })
  } catch (error) {
    console.error("Error updating awards count:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
} 