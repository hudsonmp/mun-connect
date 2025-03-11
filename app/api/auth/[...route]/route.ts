import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000'

async function handleResponse(response: Response) {
  const contentType = response.headers.get('content-type')
  
  if (contentType?.includes('application/json')) {
    try {
      const data = await response.json()
      return NextResponse.json(data, { status: response.status })
    } catch (error) {
      console.error('Error parsing JSON response:', error)
      return NextResponse.json(
        { error: 'Invalid JSON response from server' },
        { status: 500 }
      )
    }
  } else {
    // For non-JSON responses, return the text with an error status
    const text = await response.text()
    return NextResponse.json(
      { error: text || 'Non-JSON response from server' },
      { status: response.status }
    )
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { route: string[] } }
) {
  const route = params.route.join('/')
  const authHeader = request.headers.get('authorization')
  
  try {
    const response = await fetch(`${BACKEND_URL}/auth/${route}`, {
      headers: {
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
    })
    
    return handleResponse(response)
  } catch (error) {
    console.error(`Error in auth/${route}:`, error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { route: string[] } }
) {
  const route = params.route.join('/')
  const authHeader = request.headers.get('authorization')
  
  try {
    const body = await request.json()
    const response = await fetch(`${BACKEND_URL}/auth/${route}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
      body: JSON.stringify(body),
    })
    
    return handleResponse(response)
  } catch (error) {
    console.error(`Error in auth/${route}:`, error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { route: string[] } }
) {
  const route = params.route.join('/')
  const authHeader = request.headers.get('authorization')
  
  try {
    const body = await request.json()
    const response = await fetch(`${BACKEND_URL}/auth/${route}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
      body: JSON.stringify(body),
    })
    
    return handleResponse(response)
  } catch (error) {
    console.error(`Error in auth/${route}:`, error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
} 