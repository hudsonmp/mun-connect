"use client"

import React, { useState, useRef, useEffect } from 'react'
import { User, Bot, Send, AlertCircle, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Avatar } from '@/components/ui/avatar'
import { useToast } from '@/components/ui/use-toast'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useUserProfile } from '@/lib/user-profile-context'
import { OnboardingModal } from './onboarding-modal'
import { cn } from '@/lib/utils'

// Message types
type MessageType = 'user' | 'assistant' | 'system' | 'error' | 'form-submission'

interface Message {
  id: string
  type: MessageType
  content: string
  timestamp: Date
}

interface ProjectDetails {
  name: string
  goals: string
  timeline: string
  features: string[]
}

interface FormSubmission {
  [key: string]: string | string[]
}

export function AIChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()
  const { profile, isLoading } = useUserProfile()
  
  // Initialize chat once profile is loaded
  useEffect(() => {
    if (!isLoading && profile && messages.length === 0) {
      // Add welcome message based on profile info
      setMessages([
        {
          id: '1',
          type: 'assistant',
          content: profile.name 
            ? `Welcome, ${profile.name}! ${profile.projectName ? `Let's work on your project "${profile.projectName}".` : "How can I help you today?"}`
            : "Welcome! How can I help you today?",
          timestamp: new Date()
        }
      ])
    }
  }, [isLoading, profile, messages.length])
  
  // Auto-scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  // Add a new message to the chat
  const addMessage = (message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: crypto.randomUUID(),
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, newMessage])
  }
  
  // Handle sending a message
  const handleSendMessage = async () => {
    if (!inputValue.trim()) return
    
    // Add user message to chat
    addMessage({
      type: 'user',
      content: inputValue
    })
    
    // Clear input field
    setInputValue('')
    
    // Process message
    await processUserInput(inputValue)
  }
  
  // Process user input and generate a response
  const processUserInput = async (input: string) => {
    setIsProcessing(true)
    
    try {
      // Simulate processing delay
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      // Demo response - in a real app, this would call an API
      addMessage({
        type: 'assistant',
        content: `Thank you for your message. In a real implementation, this would call an API to process: "${input}"`
      })
    } catch (error) {
      console.error('Error processing input:', error)
      
      addMessage({
        type: 'error',
        content: 'Sorry, I encountered an error processing your request. Please try again.'
      })
      
      toast({
        title: 'Error',
        description: 'Failed to process your message',
        variant: 'destructive'
      })
    } finally {
      setIsProcessing(false)
    }
  }
  
  // Handle Enter key in input field
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }
  
  // Render message content based on type
  const renderMessageContent = (message: Message) => {
    switch (message.type) {
      case 'user':
        return <div className="text-sm whitespace-pre-wrap">{message.content}</div>
      
      case 'assistant':
        return <div className="text-sm whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: message.content }} />
      
      case 'system':
        return (
          <div className="text-sm bg-muted/50 p-3 rounded-md">
            <div className="font-medium mb-1">System Message</div>
            <div dangerouslySetInnerHTML={{ __html: message.content }} />
          </div>
        )
      
      case 'error':
        return (
          <Alert variant="destructive" className="text-sm">
            <AlertCircle className="h-4 w-4 mr-2" />
            <AlertDescription>{message.content}</AlertDescription>
          </Alert>
        )
      
      case 'form-submission':
        try {
          const data = JSON.parse(message.content)
          return (
            <div className="text-xs bg-muted/30 p-2 rounded-md">
              <div className="font-medium mb-1">Form Submission</div>
              {Object.entries(data).map(([key, value]) => (
                <div key={key} className="flex">
                  <span className="font-medium mr-1">{key}:</span>
                  <span>{Array.isArray(value) ? value.join(', ') : value as string}</span>
                </div>
              ))}
            </div>
          )
        } catch {
          return <div className="text-xs">{message.content}</div>
        }
      
      default:
        return <div className="text-sm">{message.content}</div>
    }
  }
  
  // Always show the onboarding modal
  // The modal component will handle its own visibility based on the profile state
  return (
    <>
      <OnboardingModal />
      
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[500px]">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-muted-foreground">Loading your profile...</p>
        </div>
      ) : (
        <div className="flex flex-col h-full max-h-[90vh] bg-gradient-to-b from-background to-background/80">
          {/* Messages container with subtle pattern background */}
          <div className="flex-1 overflow-y-auto p-4 space-y-6" 
               style={{
                 backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(0, 0, 0, 0.05) 1px, transparent 0)',
                 backgroundSize: '40px 40px'
               }}>
            {messages.length === 0 && !isProcessing && (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4 py-10 opacity-70">
                <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <Sparkles className="h-8 w-8 text-primary" />
                </div>
                <h3 className="text-xl font-semibold">Start a Conversation</h3>
                <p className="text-muted-foreground max-w-md">
                  Begin by typing your message below. The AI will provide assistance based on your onboarding preferences.
                </p>
              </div>
            )}
            
            {messages.map((message, index) => (
              <div 
                key={message.id} 
                className={`flex items-start ${message.type === 'user' ? 'justify-end' : 'justify-start'} 
                           ${index > 0 && messages[index - 1].type === message.type ? 'mt-2' : 'mt-6'}`}
              >
                {message.type !== 'user' && message.type !== 'system' && message.type !== 'error' && (
                  <div className="mr-3 flex-shrink-0">
                    <Avatar className="border-2 border-primary/20 h-9 w-9">
                      <div className="bg-gradient-to-br from-primary to-primary-foreground h-full w-full flex items-center justify-center">
                        <Bot className="h-5 w-5 text-white" />
                      </div>
                    </Avatar>
                  </div>
                )}
                
                <div 
                  className={cn(
                    "max-w-[85%] rounded-xl p-3 shadow-sm", 
                    message.type === 'user' 
                      ? "bg-gradient-to-r from-primary to-primary-foreground text-primary-foreground rounded-tr-none" 
                      : message.type === 'error'
                        ? "w-full bg-destructive/10 text-destructive-foreground"
                        : message.type === 'system'
                          ? "w-full bg-muted/70"
                          : "bg-card dark:bg-card/80 rounded-tl-none"
                  )}
                >
                  {renderMessageContent(message)}
                </div>
                
                {message.type === 'user' && (
                  <div className="ml-3 flex-shrink-0">
                    <Avatar className="border-2 border-primary/20 h-9 w-9">
                      <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-background to-muted">
                        <User className="h-5 w-5 text-primary" />
                      </div>
                    </Avatar>
                  </div>
                )}
              </div>
            ))}
            
            {isProcessing && (
              <div className="flex items-start">
                <div className="mr-3 flex-shrink-0">
                  <Avatar className="border-2 border-primary/20 h-9 w-9">
                    <div className="bg-gradient-to-br from-primary to-primary-foreground h-full w-full flex items-center justify-center">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                  </Avatar>
                </div>
                
                <div className="bg-card dark:bg-card/80 rounded-xl rounded-tl-none p-4 shadow-sm">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce"></div>
                    <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0.2s]"></div>
                    <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0.4s]"></div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input area with modern styling */}
          <div className="border-t p-4 bg-background/95 backdrop-blur-sm">
            <div className="flex items-end rounded-lg border bg-background shadow-sm focus-within:ring-1 focus-within:ring-primary/50 transition-all">
              <Textarea
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message AI..."
                className="resize-none min-h-[54px] max-h-[200px] flex-1 border-0 focus-visible:ring-0 focus-visible:ring-offset-0 rounded-lg"
                rows={1}
                disabled={isProcessing || !profile || profile.hasCompletedOnboarding !== true}
              />
              
              <Button 
                size="icon" 
                className="mb-1 mr-1 rounded-full h-9 w-9 bg-primary hover:bg-primary/90 transition-all"
                onClick={handleSendMessage}
                disabled={isProcessing || !inputValue.trim() || !profile || profile.hasCompletedOnboarding !== true}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="text-xs text-muted-foreground mt-2 flex items-center justify-center">
              {!profile || profile.hasCompletedOnboarding !== true
                ? (
                  <div className="flex items-center text-yellow-600 dark:text-yellow-400 font-medium bg-yellow-50 dark:bg-yellow-900/20 py-1 px-2 rounded-md">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    Please complete the onboarding to start chatting
                  </div>
                ) 
                : "AI responses are generated based on your project details and may not be perfect."}
            </div>
          </div>
        </div>
      )}
    </>
  )
} 