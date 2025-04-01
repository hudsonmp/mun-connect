import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

// Get environment variables with proper validation
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:5000'
const openaiApiKey = process.env.OPENAI_API_KEY

// Validate critical environment variables
if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase environment variables')
}

if (!backendUrl) {
  console.error('Missing backend URL environment variable')
}

// Create Supabase client with proper fallbacks
const supabase = createClient(supabaseUrl || '', supabaseKey || '')

export async function POST(request: Request) {
  try {
    console.log('Position paper generation API called')
    
    // Extract and validate user ID
    const userId = request.headers.get('user-id')
    if (!userId) {
      console.error('No user ID provided in headers')
      return NextResponse.json({ 
        success: false, 
        error: 'Authentication required',
        details: 'User ID header is missing'
      }, { status: 401 })
    }
    
    // Parse request body with validation
    let body: any = {}
    try {
      body = await request.json()
    } catch (error) {
      console.error('Invalid JSON in request body')
      return NextResponse.json({ 
        success: false, 
        error: 'Invalid request format',
        details: 'Request body must be valid JSON'
      }, { status: 400 })
    }
    
    // Validate required fields
    const requiredFields = ['country', 'committee', 'topic', 'conference']
    const missingFields = requiredFields.filter(field => !body[field])
    
    if (missingFields.length > 0) {
      return NextResponse.json({ 
        success: false, 
        error: 'Missing required fields',
        details: `The following fields are required: ${missingFields.join(', ')}`
      }, { status: 400 })
    }
    
    // Forward the request to the Flask backend
    console.log(`Forwarding request to backend: ${backendUrl}/api/ai/generate-position-paper`)
    const backendResponse = await fetch(`${backendUrl}/api/ai/generate-position-paper`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'user-id': userId,
        'Authorization': request.headers.get('Authorization') || ''
      },
      body: JSON.stringify(body)
    })
    
    // Handle backend response
    if (!backendResponse.ok) {
      let errorData
      try {
        errorData = await backendResponse.json()
      } catch {
        errorData = { error: 'Unknown backend error' }
      }
      
      console.error('Backend error:', errorData)
      return NextResponse.json({ 
        success: false, 
        error: errorData.error || 'Backend processing error',
        details: errorData.details || 'The backend server failed to process the request'
      }, { status: backendResponse.status })
    }
    
    // Parse and validate backend success response
    let responseData
    try {
      responseData = await backendResponse.json()
    } catch (error) {
      console.error('Error parsing backend response:', error)
      return NextResponse.json({ 
        success: false, 
        error: 'Invalid response from backend',
        details: 'The server returned an invalid response format'
      }, { status: 500 })
    }
    
    // Return the backend response
    console.log('Position paper generated successfully')
    return NextResponse.json({
      success: true,
      document: responseData.document,
      content: responseData.content,
      warning: responseData.warning
    }, { status: 201 })
    
  } catch (error: any) {
    console.error('Unexpected error in generate-position-paper API:', error)
    return NextResponse.json({ 
      success: false, 
      error: 'Server error',
      details: error.message || 'An unexpected error occurred'
    }, { status: 500 })
  }
} 