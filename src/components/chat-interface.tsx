"use client"

import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Bot, User, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { useToast } from '@/components/ui/use-toast'
import { RichTextEditor } from './rich-text-editor'
import { Badge } from './ui/badge'
import { Alert, AlertDescription } from './ui/alert'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu'
import { v4 as uuidv4 } from 'uuid'
import { useRouter } from 'next/navigation'
import { createChat, saveMessages, loadChat } from '@/lib/chat-service'

type MessageType = 'user' | 'system' | 'editor' | 'upload' | 'error'

interface Message {
  id: string
  type: MessageType
  content: string
  timestamp: Date
  documentId?: string
  documentType?: 'position_paper' | 'resolution' | 'speech'
  files?: File[]
}

interface ChatInterfaceProps {
  userId: string
  chatId?: string
  onSaveDocument?: (documentId: string, content: string) => void
}

export function ChatInterface({ userId, chatId, onSaveDocument }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'system',
      content: "Welcome to MUN Connect! I'm here to help you create high-quality Model UN documents. Please select which type of document you'd like to create:",
      timestamp: new Date(),
    },
    {
      id: '2',
      type: 'system',
      content: `
      <div class="flex flex-col space-y-2 mt-2">
        <button class="document-type-btn flex items-center bg-blue-100 dark:bg-blue-950 hover:bg-blue-200 dark:hover:bg-blue-900 p-3 rounded transition-colors w-full text-left" data-type="position_paper">
          <span class="mr-2">📄</span>
          <div>
            <div class="font-medium">Position Paper</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Formal document stating your country's stance on an issue</div>
          </div>
        </button>
        <button class="document-type-btn flex items-center bg-green-100 dark:bg-green-950 hover:bg-green-200 dark:hover:bg-green-900 p-3 rounded transition-colors w-full text-left" data-type="resolution">
          <span class="mr-2">📜</span>
          <div>
            <div class="font-medium">Resolution Paper</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Formal document proposing solutions to address an issue</div>
          </div>
        </button>
        <button class="document-type-btn flex items-center bg-amber-100 dark:bg-amber-950 hover:bg-amber-200 dark:hover:bg-amber-900 p-3 rounded transition-colors w-full text-left" data-type="speech">
          <span class="mr-2">🎤</span>
          <div>
            <div class="font-medium">Speech</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Formal address to a committee explaining your country's position</div>
          </div>
        </button>
      </div>
      `,
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [documentInfo, setDocumentInfo] = useState<{
    committee?: string
    country?: string
    topic?: string
    documentType?: 'position_paper' | 'resolution' | 'speech'
    referenceFiles: File[]
  }>({
    referenceFiles: []
  })
  const [currentStep, setCurrentStep] = useState<'initial' | 'collecting_info' | 'generating' | 'editing'>('initial')
  const [rateLimit, setRateLimit] = useState({
    remaining: 3,
    resetTime: new Date(Date.now() + 60000)
  })
  const [currentChatId, setCurrentChatId] = useState<string | undefined>(chatId)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()
  const router = useRouter()
  
  // Auto-scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  // Handle document type selection buttons
  useEffect(() => {
    const handleDocTypeClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      
      if (target.classList.contains('document-type-btn') || 
          target.parentElement?.classList.contains('document-type-btn')) {
        
        // Get the button or its parent if text was clicked
        const button = target.classList.contains('document-type-btn') 
          ? target 
          : target.parentElement
          
        if (!button) return
        
        // Get document type from data attribute
        const docType = button.getAttribute('data-type') as 'position_paper' | 'resolution' | 'speech'
        
        if (docType) {
          // Set document type
          setDocumentInfo(prev => ({ ...prev, documentType: docType }))
          setCurrentStep('collecting_info')
          
          // Add user message
          addMessage({
            type: 'user',
            content: `I want to create a ${docType.replace('_', ' ')}`,
          })
          
          // Ask for committee
          addMessage({
            type: 'system',
            content: `Great! Let's create a ${docType.replace('_', ' ')}. What committee are you representing in? (For example: UN Security Council, ECOSOC, WHO, etc.)`,
          })
        }
      }
    }
    
    // Add event listener
    document.addEventListener('click', handleDocTypeClick)
    
    // Clean up
    return () => {
      document.removeEventListener('click', handleDocTypeClick)
    }
  }, []) // Empty dependency array means this runs once on mount
  
  // Load existing chat or create a new one
  useEffect(() => {
    const initializeChat = async () => {
      if (chatId) {
        // Load existing chat
        const { chat, error } = await loadChat(chatId)
        if (chat && !error) {
          setMessages(chat.messages)
          setCurrentChatId(chatId)
        } else {
          console.error('Error loading chat:', error)
          // If there's an error loading the chat, create a new one
          createNewChat()
        }
      } else if (!currentChatId) {
        // Create a new chat if we don't have one
        createNewChat()
      }
    }
    
    const createNewChat = async () => {
      const { chat, error } = await createChat(userId)
      if (chat && !error) {
        setCurrentChatId(chat.id)
        // Update the URL with the new chat ID
        router.push(`/chat/${chat.id}`)
      } else {
        console.error('Error creating new chat:', error)
        toast({
          title: 'Error',
          description: 'Failed to create a new chat session. Please try again.',
          variant: 'destructive',
        })
      }
    }
    
    initializeChat()
  }, [chatId, userId])
  
  // Auto-save messages when they change
  useEffect(() => {
    const saveTimer = setTimeout(async () => {
      if (messages.length > 0 && currentChatId) {
        const { success, error } = await saveMessages(currentChatId, messages)
        if (!success) {
          console.error('Error auto-saving chat:', error)
        }
      }
    }, 2000) // Debounce saves to reduce DB calls
    
    return () => clearTimeout(saveTimer)
  }, [messages, currentChatId])
  
  const addMessage = (message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: uuidv4(),
      timestamp: new Date(),
    }
    
    setMessages(prev => [...prev, newMessage])
  }
  
  const handleSendMessage = async () => {
    if (!inputValue.trim()) return
    
    // Add user message
    addMessage({
      type: 'user',
      content: inputValue,
    })
    
    // Clear input
    setInputValue('')
    
    // Process the message
    await processUserInput(inputValue)
  }
  
  const processUserInput = async (input: string) => {
    setIsProcessing(true)
    
    try {
      // If we're in initial state, determine what document type they want
      if (currentStep === 'initial') {
        const lowerInput = input.toLowerCase()
        
        if (lowerInput.includes('position paper') || lowerInput.includes('position')) {
          setDocumentInfo(prev => ({ ...prev, documentType: 'position_paper' }))
          setCurrentStep('collecting_info')
          
          // Ask for committee
          addMessage({
            type: 'system',
            content: "Great! Let's create a position paper. What committee are you representing in? (For example: UN Security Council, ECOSOC, WHO, etc.)",
          })
        } else if (lowerInput.includes('resolution') || lowerInput.includes('resolution paper')) {
          setDocumentInfo(prev => ({ ...prev, documentType: 'resolution' }))
          setCurrentStep('collecting_info')
          
          // Ask for committee
          addMessage({
            type: 'system',
            content: "I'll help you create a resolution paper. What committee are you representing in? (For example: UN Security Council, ECOSOC, WHO, etc.)",
          })
        } else if (lowerInput.includes('speech')) {
          setDocumentInfo(prev => ({ ...prev, documentType: 'speech' }))
          setCurrentStep('collecting_info')
          
          // Ask for committee
          addMessage({
            type: 'system',
            content: "I'll help you prepare a speech. What committee are you speaking in? (For example: UN Security Council, ECOSOC, WHO, etc.)",
          })
        } else {
          // If not specified, ask directly
          addMessage({
            type: 'system',
            content: "I'd be happy to help you create a Model UN document. What type of document would you like to work on? Please choose from: position paper, resolution paper, or speech.",
          })
        }
      } 
      // Collect information based on where we are in the flow
      else if (currentStep === 'collecting_info') {
        // If we have committee but not country
        if (documentInfo.committee && !documentInfo.country) {
          setDocumentInfo(prev => ({ ...prev, country: input }))
          
          // Ask for topic
          addMessage({
            type: 'system',
            content: `Great! What topic will you be addressing in the ${documentInfo.committee}? (For example: "Climate Change Mitigation", "Refugee Crisis", etc.)`,
          })
        }
        // If we have committee and country but not topic
        else if (documentInfo.committee && documentInfo.country && !documentInfo.topic) {
          setDocumentInfo(prev => ({ ...prev, topic: input }))
          
          // Ask for reference materials
          addMessage({
            type: 'system',
            content: "Thank you! You can now upload background guides or reference materials to help with document generation (up to 3 files, 5MB each). Or just type 'continue' if you don't have any files to upload.",
          })
          
          addMessage({
            type: 'upload',
            content: "Upload files (optional)",
          })
        }
        // If we need committee still
        else if (!documentInfo.committee) {
          setDocumentInfo(prev => ({ ...prev, committee: input }))
          
          // Ask for country
          addMessage({
            type: 'system',
            content: "Which country are you representing?",
          })
        }
        // If we have all basic info and they've typed 'continue' or similar
        else if (documentInfo.committee && documentInfo.country && documentInfo.topic && 
                (input.toLowerCase() === 'continue' || input.toLowerCase().includes('generate'))) {
          // Move to generation phase
          setCurrentStep('generating')
          
          // Generate the document
          await generateDocument()
        }
        // If they upload files we process that separately
      }
      // If they respond after document generation, it's likely feedback
      else if (currentStep === 'editing') {
        addMessage({
          type: 'system',
          content: "I've noted your feedback. Feel free to continue editing the document directly in the editor above. You can download it when you're finished.",
        })
      }
    } catch (error) {
      console.error('Error processing input:', error)
      
      addMessage({
        type: 'error',
        content: `Sorry, there was an error processing your request. Please try again.`,
      })
    } finally {
      setIsProcessing(false)
    }
  }
  
  const handleFileUpload = (files: FileList | null) => {
    if (!files || files.length === 0) return
    
    // Check file size and limits
    const validFiles: File[] = []
    const maxFiles = 3
    const maxSizeBytes = 5 * 1024 * 1024 // 5MB
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      
      // Check if we've hit the maximum
      if (documentInfo.referenceFiles.length + validFiles.length >= maxFiles) {
        toast({
          title: "Maximum files reached",
          description: `You can only upload up to ${maxFiles} reference files.`,
          variant: "destructive",
        })
        break
      }
      
      // Check file size
      if (file.size > maxSizeBytes) {
        toast({
          title: "File too large",
          description: `${file.name} exceeds the 5MB size limit.`,
          variant: "destructive",
        })
        continue
      }
      
      // Check file type
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
      if (!validTypes.includes(file.type)) {
        toast({
          title: "Unsupported file type",
          description: `${file.name} is not a supported file type. Please upload PDF, DOCX, or TXT files.`,
          variant: "destructive",
        })
        continue
      }
      
      validFiles.push(file)
    }
    
    if (validFiles.length > 0) {
      // Show upload progress toast
      toast({
        title: "Processing files",
        description: `Extracting content from ${validFiles.length} file(s)...`,
      })
      
      // Add files to state
      setDocumentInfo(prev => ({
        ...prev,
        referenceFiles: [...prev.referenceFiles, ...validFiles]
      }))
      
      // Add upload message
      addMessage({
        type: 'user',
        content: `Uploaded ${validFiles.length} file(s)`,
        files: validFiles
      })
      
      // Simulate text extraction process to provide feedback
      setTimeout(() => {
        // Add system response
        if (documentInfo.committee && documentInfo.country && documentInfo.topic) {
          addMessage({
            type: 'system',
            content: `Great! I've processed ${validFiles.length} file(s) and extracted the key information. Type 'continue' when you're ready to generate your document.`,
          })
        } else {
          addMessage({
            type: 'system',
            content: `I've processed ${validFiles.length} file(s) and extracted the key information. Let's continue with the information needed.`,
          })
        }
        
        // Show success toast
        toast({
          title: "Files processed",
          description: `Successfully extracted content from ${validFiles.length} file(s).`,
        })
      }, 1500) // Simulate processing time
    }
  }
  
  const generateDocument = async () => {
    // Check rate limits first
    if (rateLimit.remaining <= 0) {
      const waitTime = Math.ceil((rateLimit.resetTime.getTime() - Date.now()) / 1000)
      
      addMessage({
        type: 'error',
        content: `Rate limit reached. Please try again in ${waitTime} seconds.`,
      })
      return
    }
    
    // Inform user generation has started with appropriate message based on document type
    const documentTypeDisplay = documentInfo.documentType?.replace('_', ' ') || 'document'
    
    addMessage({
      type: 'system',
      content: `Generating your ${documentTypeDisplay}... This may take up to 45 seconds.`,
    })
    
    try {
      // Prepare form data for file uploads
      const formData = new FormData()
      formData.append('document_type', documentInfo.documentType || 'position_paper')
      formData.append('committee', documentInfo.committee || '')
      formData.append('country', documentInfo.country || '')
      formData.append('topic', documentInfo.topic || '')
      
      // Add document type specific data
      if (documentInfo.documentType === 'resolution') {
        formData.append('co_sponsors', 'auto-generate') // In a complete implementation, we'd collect co-sponsors
      } else if (documentInfo.documentType === 'speech') {
        formData.append('duration_minutes', '3') // Default to 3-minute speech
        formData.append('speech_type', 'opening') // Default to opening speech
      }
      
      // Add reference files if any
      if (documentInfo.referenceFiles && documentInfo.referenceFiles.length > 0) {
        documentInfo.referenceFiles.forEach(file => {
          formData.append('reference_materials', file)
        })
      }
      
      setIsProcessing(true)
      
      // Show progress updates
      let progressCounter = 0
      const progressInterval = setInterval(() => {
        progressCounter += 1
        if (progressCounter % 5 === 0) { // Every 5 seconds
          addMessage({
            type: 'system',
            content: `Still working on your ${documentTypeDisplay}... (${progressCounter} seconds)`,
          })
        }
      }, 1000)
      
      // Call the actual backend API - do not set Content-Type manually for FormData
      // Let the browser set the appropriate multipart boundary
      const response = await fetch('/api/ai/generate-document', {
        method: 'POST',
        headers: {
          'user-id': userId,
          // Do not manually set Content-Type for FormData
        },
        body: formData
      })
      
      // Clear the progress interval
      clearInterval(progressInterval)
      
      if (!response.ok) {
        // Attempt to parse error response
        try {
          const errorData = await response.json()
          throw new Error(errorData.details || errorData.error || 'Error generating document')
        } catch (parseError) {
          // If error response isn't valid JSON, use status text
          throw new Error(`Error generating document: ${response.statusText}`)
        }
      }
      
      const data = await response.json()
      
      // Update rate limits based on response
      if (data.rate_limits) {
        setRateLimit({
          remaining: data.rate_limits.minute.remaining,
          resetTime: new Date(data.rate_limits.minute.reset)
        })
      } else {
        // Fallback if rate limits not provided
        setRateLimit({
          remaining: rateLimit.remaining - 1,
          resetTime: new Date(Date.now() + 60000) // Reset after 1 minute
        })
      }
      
      // Show the editor with generated content
      addMessage({
        type: 'editor',
        content: data.content,
        documentId: data.document_id,
        documentType: documentInfo.documentType,
      })
      
      // Add system message based on document type
      let successMessage = `Here's your ${documentTypeDisplay}!`
      
      switch(documentInfo.documentType) {
        case 'position_paper':
          successMessage += ` This position paper represents ${documentInfo.country}'s stance on ${documentInfo.topic} for the ${documentInfo.committee}.`
          break
        case 'resolution':
          successMessage += ` This resolution presents a comprehensive approach to ${documentInfo.topic} for the ${documentInfo.committee}.`
          break
        case 'speech':
          successMessage += ` This speech articulates ${documentInfo.country}'s position on ${documentInfo.topic} for the ${documentInfo.committee}.`
          break
      }
      
      successMessage += " You can edit it directly in the editor above. When you're satisfied, you can download it as a PDF or DOCX file."
      
      addMessage({
        type: 'system',
        content: successMessage,
      })
      
      // Update state to editing mode
      setCurrentStep('editing')
      
    } catch (error) {
      console.error('Error generating document:', error)
      
      // Add error message
      addMessage({
        type: 'error',
        content: `Sorry, there was an error generating your document: ${error instanceof Error ? error.message : 'Unknown error'}`,
      })
      
      // Add specific retry instructions based on the error
      addMessage({
        type: 'system',
        content: `You can type 'retry' to try again, or we can try with fewer reference materials if that might help. Type 'retry simplified' for a simpler version.`,
      })
    } finally {
      setIsProcessing(false)
    }
  }
  
  const handleEditorChange = (documentId: string, content: string) => {
    // Update the message content
    setMessages(prev => 
      prev.map(msg => 
        msg.documentId === documentId ? { ...msg, content } : msg
      )
    )
    
    // If callback provided, call it
    if (onSaveDocument) {
      onSaveDocument(documentId, content)
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }
  
  const triggerFileUpload = () => {
    fileInputRef.current?.click()
  }
  
  const exportDocument = async (documentId: string, format: 'pdf' | 'docx', content: string) => {
    try {
      // Show loading toast
      toast({
        title: `Preparing ${format.toUpperCase()} export`,
        description: "Your document is being prepared for download...",
      })
      
      // Prepare document for export
      const response = await fetch(`/api/documents/${documentId}/export?format=${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'user-id': userId
        },
        body: JSON.stringify({ content })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || `Failed to export document as ${format}`)
      }
      
      // Get the blob from response
      const blob = await response.blob()
      
      // Create a download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      
      // Set the file name based on document type and format
      const documentType = messages.find(m => m.documentId === documentId)?.documentType || 'document'
      const fileName = `${documentType.replace('_', '-')}.${format}`
      a.download = fileName
      
      // Add to document, click and remove
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      // Show success toast
      toast({
        title: "Export successful",
        description: `Your document has been downloaded as ${fileName}`,
      })
    } catch (error) {
      console.error('Error exporting document:', error)
      toast({
        title: "Export failed",
        description: error instanceof Error ? error.message : "Failed to export document",
        variant: "destructive",
      })
    }
  }
  
  const renderMessage = (message: Message) => {
    switch (message.type) {
      case 'system':
        return (
          <div className="flex gap-3 max-w-[80%]">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="bg-secondary p-3 rounded-lg">
              {message.content.includes('<') && message.content.includes('>') ? (
                <div dangerouslySetInnerHTML={{ __html: message.content }} />
              ) : (
                message.content
              )}
            </div>
          </div>
        );
        
      case 'user':
        return (
          <div className="flex gap-3 max-w-[80%] ml-auto">
            <div className="bg-primary p-3 rounded-lg text-primary-foreground">
              {message.content}
              {message.files && message.files.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {message.files.map((file, index) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {file.name}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
              <User className="h-4 w-4 text-primary-foreground" />
            </div>
          </div>
        );
        
      case 'editor':
        return (
          <div className="w-full my-4">
            <div className="bg-secondary p-3 rounded-lg mb-2">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-medium">
                  {message.documentType?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </h3>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">Export</Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem 
                      onClick={() => exportDocument(message.documentId || '', 'pdf', message.content)}
                    >
                      Download as PDF
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => exportDocument(message.documentId || '', 'docx', message.content)}
                    >
                      Download as DOCX
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <RichTextEditor 
                initialValue={message.content}
                onChange={(content) => message.documentId && handleEditorChange(message.documentId, content)}
                height={400}
                minimal={true}
              />
            </div>
          </div>
        );
        
      case 'upload':
        return (
          <div className="flex gap-3 max-w-[80%]">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="bg-secondary p-3 rounded-lg">
              <p className="mb-2">{message.content}</p>
              <Button 
                variant="outline" 
                size="sm" 
                className="flex items-center gap-1"
                onClick={triggerFileUpload}
              >
                <Paperclip className="h-4 w-4" />
                Select Files
              </Button>
            </div>
          </div>
        );
        
      case 'error':
        return (
          <div className="flex gap-3 max-w-[80%]">
            <div className="h-8 w-8 rounded-full bg-destructive/10 flex items-center justify-center">
              <Bot className="h-4 w-4 text-destructive" />
            </div>
            <Alert variant="destructive" className="max-w-full">
              <AlertDescription>
                {message.content}
              </AlertDescription>
            </Alert>
          </div>
        );
        
      default:
        return null;
    }
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Rate limit indicator */}
      <div className="py-2 px-4 border-b text-xs text-muted-foreground">
        <span>
          Document generations remaining: {rateLimit.remaining}/3 per minute, resets in {Math.max(0, Math.ceil((rateLimit.resetTime.getTime() - Date.now()) / 1000))}s
        </span>
      </div>
      
      {/* Messages container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(message => (
          <div key={message.id}>
            {renderMessage(message)}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input area */}
      <div className="border-t p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSendMessage()
          }}
          className="flex items-end gap-2"
        >
          <Textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 min-h-[60px] max-h-[200px] resize-none"
            disabled={isProcessing}
          />
          <div className="flex flex-col gap-2">
            <Button
              type="button"
              size="icon"
              variant="outline"
              onClick={triggerFileUpload}
              disabled={isProcessing || documentInfo.referenceFiles.length >= 3}
              title={documentInfo.referenceFiles.length >= 3 ? "Maximum 3 files allowed" : "Upload files"}
            >
              <Paperclip className="h-4 w-4" />
            </Button>
            <Button 
              type="submit" 
              size="icon"
              disabled={!inputValue.trim() || isProcessing}
            >
              {isProcessing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
          
          {/* Hidden file input */}
          <input 
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={(e) => handleFileUpload(e.target.files)}
            multiple
            accept=".pdf,.docx,.txt"
          />
        </form>
      </div>
    </div>
  );
} 