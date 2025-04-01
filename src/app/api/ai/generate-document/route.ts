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
    // Check if the request is a FormData
    const contentType = request.headers.get("Content-Type") || ""
    
    // Set up the backend URL with error handling
    const backendUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    
    if (!backendUrl) {
      console.error("Missing NEXT_PUBLIC_SUPABASE_URL environment variable")
      return NextResponse.json(
        { error: "Server configuration error" }, 
        { status: 500 }
      )
    }
    
    let requestBody: FormData | string
    // Use Record<string, string> to create a dynamically keyed object for headers
    let headers: Record<string, string> = {
      "user-id": userId
    }
    
    if (contentType.includes("multipart/form-data")) {
      // Handle FormData by cloning and forwarding
      requestBody = await request.formData()
      
      // No need to set Content-Type for FormData as it will be set automatically with boundary
    } else {
      // Handle JSON request
      requestBody = JSON.stringify(await request.json())
      headers["Content-Type"] = "application/json"
    }
    
    const response = await fetch(`${backendUrl}/api/ai/generate-document`, {
      method: "POST",
      headers,
      body: requestBody
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(
        { error: errorData.error || "Failed to generate document" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data, { status: 200 })
  } catch (error) {
    console.error("Error generating document with AI:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
} 