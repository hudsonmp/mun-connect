import { NextResponse } from 'next/server'
import OpenAI from 'openai'
import { createClient } from '@supabase/supabase-js'

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase environment variables')
}

const supabase = createClient(supabaseUrl, supabaseKey)

// Initialize OpenAI client
const openaiApiKey = process.env.OPENAI_API_KEY
if (!openaiApiKey) {
  console.error('Missing OpenAI API key')
}

const openai = new OpenAI({
  apiKey: openaiApiKey
})

export async function POST(request: Request) {
  try {
    console.log("Position paper generation API called")
    
    // Extract user ID from headers and validate
    const userId = request.headers.get('user-id')
    if (!userId) {
      console.error("No user ID provided in headers")
      return NextResponse.json({ error: 'User ID is required' }, { status: 400 })
    }
    
    // Log auth header for debugging
    const authHeader = request.headers.get('authorization')
    console.log("Auth header present:", !!authHeader)
    
    // Verify user exists by checking the profiles table
    try {
      console.log("Checking for user profile with ID:", userId)
      const { data: profileData, error: profileError } = await supabase
        .from('profiles')
        .select('id')
        .eq('id', userId)
        .single()
        
      if (profileError) {
        console.error("Profile query error:", profileError)
        
        // If profile doesn't exist, create it
        console.log("Attempting to create profile for user:", userId)
        const { error: createError } = await supabase
          .from('profiles')
          .insert({
            id: userId,
            username: `user_${Date.now()}`,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })
        
        if (createError) {
          console.error("Error creating profile:", createError)
          return NextResponse.json({ error: 'Failed to create user profile' }, { status: 500 })
        }
        
        console.log("Profile created successfully for user:", userId)
      } else {
        console.log("User profile verified:", profileData.id)
      }
    } catch (authError) {
      console.error("Error checking/creating user profile:", authError)
      return NextResponse.json({ error: 'Authentication error' }, { status: 401 })
    }
    
    // Parse request body
    let body;
    try {
      body = await request.json()
      console.log("Request body received and parsed")
    } catch (error) {
      console.error("Error parsing request body:", error)
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
    }
    
    // Extract data for prompt with validation
    const conference = body.conference || ''
    const committee = body.committee || ''
    const committee_type = body.committee_type || 'General Assembly'
    const topic = body.topic || ''
    const country = body.country || ''
    const template = body.template || 'Standard Position Paper'
    const backgroundText = body.background_text || ''
    const backgroundGuideUrls = body.background_guide_urls || []
    const relevantSourceUrls = body.relevant_source_urls || []
    const positionPaperGuidelines = body.position_paper_guidelines || ''
    const formattingTipsPage = body.formatting_tips_page || ''
    const customRequirements = body.custom_requirements || ''
    
    // Validate required fields
    if (!conference || !committee || !topic || !country) {
      console.error("Missing required fields")
      return NextResponse.json({ 
        error: 'Missing required fields', 
        details: { conference, committee, topic, country } 
      }, { status: 400 })
    }
    
    // Construct the prompt
    const prompt = `
      You are an expert in Model United Nations and international relations. Write a comprehensive position paper for ${country} in the ${committee} committee (type: ${committee_type}) at ${conference} on the topic of ${topic}.

      Format this position paper following the ${template} format, with clear sections including:
      1. Introduction with country background
      2. Country's position on the topic
      3. Past international actions
      4. Proposed solutions
      5. Conclusion

      Make sure the paper is written in a formal, diplomatic style appropriate for a Model UN conference.
      
      Additional background information:
      ${backgroundText}

      Background guides:
      ${backgroundGuideUrls.join('\n')}
      
      Relevant sources:
      ${relevantSourceUrls.join('\n')}
      
      Position paper guidelines:
      ${positionPaperGuidelines}
      
      Formatting tips (page reference):
      ${formattingTipsPage}
      
      Custom formatting requirements:
      ${customRequirements}
    `
    
    console.log("Making OpenAI API call...")
    
    // Make the OpenAI API call with error handling
    let completion;
    try {
      completion = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: "You are an expert assistant that helps students write high-quality position papers for Model United Nations conferences." },
          { role: "user", content: prompt }
        ],
        temperature: 0.7,
        max_tokens: 2500
      })
    } catch (error: any) {
      console.error("OpenAI API error:", error)
      return NextResponse.json({ 
        error: 'Error generating position paper with OpenAI',
        details: error.message 
      }, { status: 500 })
    }
    
    // Extract the generated text
    const generatedText = completion.choices[0].message.content || ''
    if (!generatedText) {
      console.error("Empty response from OpenAI")
      return NextResponse.json({ error: 'Empty response from AI model' }, { status: 500 })
    }
    
    console.log("Position paper generated successfully")
    
    // Save the document in the database
    try {
      const { data, error } = await supabase
        .from('documents')
        .insert({
          user_id: userId,
          title: `${country} - ${topic}`,
          type: 'Position Paper',
          committee: committee,
          conference: conference,
          content: generatedText,
          progress: 100,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .select()
        .single()
        
      if (error) {
        console.error('Error saving document:', error)
      } else {
        console.log('Document saved successfully:', data?.id)
        
        // Update user stats
        try {
          const { data: statsData, error: statsError } = await supabase
            .from('user_stats')
            .select('*')
            .eq('user_id', userId)
            .single()
            
          if (!statsError && statsData) {
            const { error: updateError } = await supabase
              .from('user_stats')
              .update({
                documents_count: (statsData.documents_count || 0) + 1,
                updated_at: new Date().toISOString()
              })
              .eq('user_id', userId)
              
            if (updateError) {
              console.error('Error updating user stats:', updateError)
            } else {
              console.log('User stats updated successfully')
            }
          }
        } catch (statsUpdateError) {
          console.error('Exception updating user stats:', statsUpdateError)
        }
      }
      
      // Return the document ID and content
      return NextResponse.json({
        document: data,
        content: generatedText
      }, { status: 201 })
    } catch (dbError) {
      console.error('Database operation error:', dbError)
      // Still return the generated content even if DB operations fail
      return NextResponse.json({
        content: generatedText,
        warning: 'Generated content was not saved to database'
      }, { status: 200 })
    }
  } catch (error: any) {
    console.error('Unexpected error in generate-position-paper API:', error)
    return NextResponse.json(
      { error: error.message || 'An unexpected error occurred' },
      { status: 500 }
    )
  }
} 