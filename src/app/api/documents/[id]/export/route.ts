import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase-client'

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const documentId = params.id
  const userId = request.headers.get('user-id')
  const format = request.nextUrl.searchParams.get('format')

  // Validate inputs
  if (!userId) {
    return NextResponse.json(
      { error: 'User ID is required' },
      { status: 400 }
    )
  }

  if (!format || !['pdf', 'docx'].includes(format)) {
    return NextResponse.json(
      { error: 'Valid format (pdf or docx) is required' },
      { status: 400 }
    )
  }

  try {
    // Get document content from request body
    const { content } = await request.json()
    
    if (!content) {
      return NextResponse.json(
        { error: 'Document content is required' },
        { status: 400 }
      )
    }

    // Verify user owns this document
    const { data: document, error: fetchError } = await supabase
      .from('documents')
      .select('id, user_id, title')
      .eq('id', documentId)
      .single()
    
    if (fetchError || !document) {
      return NextResponse.json(
        { error: 'Document not found' },
        { status: 404 }
      )
    }

    if (document.user_id !== userId) {
      return NextResponse.json(
        { error: 'You do not have permission to access this document' },
        { status: 403 }
      )
    }

    // For PDF export
    if (format === 'pdf') {
      // Generate PDF from HTML content
      // This would normally call a HTML-to-PDF service
      // For the MVP, we can use TinyMCE's PDF export plugin
      
      // Since TinyMCE handles PDF export client-side, we just return success
      // The frontend will handle the actual conversion
      return new NextResponse(
        content, // Return the HTML content directly
        {
          status: 200,
          headers: {
            'Content-Type': 'text/html',
            'Content-Disposition': `attachment; filename="${document.title || 'document'}.pdf"`,
          }
        }
      )
    }
    
    // For DOCX export
    if (format === 'docx') {
      // Similar to PDF, we'll rely on TinyMCE for DOCX export in the MVP
      // For a more complete solution, a server-side HTML-to-DOCX library would be used
      
      return new NextResponse(
        content, // Return the HTML content directly
        {
          status: 200,
          headers: {
            'Content-Type': 'text/html',
            'Content-Disposition': `attachment; filename="${document.title || 'document'}.docx"`,
          }
        }
      )
    }

    // This should never happen due to earlier validation
    return NextResponse.json(
      { error: 'Unsupported format' },
      { status: 400 }
    )

  } catch (error) {
    console.error('Error exporting document:', error)
    return NextResponse.json(
      { error: 'Failed to export document' },
      { status: 500 }
    )
  }
} 