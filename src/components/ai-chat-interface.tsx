"use client"

import React, { useState, useRef, useEffect } from 'react'
import { User, Bot, Send, AlertCircle, Sparkles, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Avatar } from '@/components/ui/avatar'
import { useToast } from '@/components/ui/use-toast'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useUserProfile } from '@/lib/user-profile-context'
import { useMUNOnboarding } from '@/lib/mun-onboarding-context'
import { MUNOnboardingModal } from './mun-onboarding-modal'
import { cn } from '@/lib/utils'
import { v4 as uuidv4 } from 'uuid'
import { supabase } from '@/lib/supabase-client'

// Message types
type MessageType = 'user' | 'assistant' | 'system' | 'error'

interface Message {
  id: string
  type: MessageType
  content: string
  timestamp: Date
}

export function AIChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()
  const { profile, isLoading: isProfileLoading } = useUserProfile()
  const { munData, isLoading: isMunDataLoading } = useMUNOnboarding()
  
  // Initialize chat
  useEffect(() => {
    const createNewChat = async () => {
      if (!profile?.id) return;
      
      try {
        // Create a new chat in Supabase
        const chatId = uuidv4();
        const { error } = await supabase
          .from('chats')
          .insert({
            id: chatId,
            user_id: profile.id,
            title: `Position Paper - ${munData?.topic || 'New Topic'}`
          });
          
        if (error) throw error;
        
        setCurrentChatId(chatId);
        
        // Add welcome message
        const welcomeMessage = {
          id: uuidv4(),
          type: 'assistant' as MessageType,
          content: generateWelcomeMessage(),
          timestamp: new Date()
        };
        
        setMessages([welcomeMessage]);
        
        // Save welcome message to Supabase
        await supabase
          .from('messages')
          .insert({
            id: welcomeMessage.id,
            chat_id: chatId,
            role: welcomeMessage.type,
            content: welcomeMessage.content,
            order_index: 0
          });
          
      } catch (error) {
        console.error('Error creating chat:', error);
        toast({
          title: 'Error',
          description: 'Failed to create new chat',
          variant: 'destructive'
        });
      }
    };
    
    if (!isProfileLoading && !isMunDataLoading && profile && messages.length === 0) {
      createNewChat();
    }
  }, [isProfileLoading, isMunDataLoading, profile, munData, messages.length, toast]);
  
  // Generate welcome message based on MUN data
  const generateWelcomeMessage = () => {
    if (munData) {
      return `
        <div>
          <p><strong>Welcome to Position Paper Writing Assistant!</strong></p>
          <p>I'll help you write a position paper for:</p>
          <ul class="list-disc list-inside my-2">
            <li><strong>Conference:</strong> ${munData.conferenceName}</li>
            <li><strong>Committee:</strong> ${munData.committeeName}</li>
            <li><strong>Country/Position:</strong> ${munData.positionCountry}</li>
            <li><strong>Topic:</strong> ${munData.topic}</li>
          </ul>
          <p>You can start by asking me questions about the topic, requesting research assistance, or asking for help crafting specific sections of your position paper.</p>
          <p>Type your message below to get started!</p>
        </div>
      `;
    } else {
      return `
        <div>
          <p><strong>Welcome to the MUN Position Paper Assistant!</strong></p>
          <p>To get started, please set up your MUN conference details by clicking the "Setup MUN Position" button at the top.</p>
          <p>Once configured, I'll help you research, outline, and write your position paper directly in this chat.</p>
        </div>
      `;
    }
  };
  
  // Auto-scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  // Add a new message to the chat
  const addMessage = async (message: Omit<Message, 'id' | 'timestamp'>) => {
    if (!currentChatId) return;
    
    const newMessage: Message = {
      ...message,
      id: uuidv4(),
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, newMessage])
    
    // Save message to Supabase
    try {
      await supabase
        .from('messages')
        .insert({
          id: newMessage.id,
          chat_id: currentChatId,
          role: newMessage.type,
          content: newMessage.content,
          order_index: messages.length
        });
    } catch (error) {
      console.error('Error saving message:', error);
      // Continue with the chat even if message saving fails
    }
    
    return newMessage;
  }
  
  // Handle sending a message
  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentChatId) return
    
    // Add user message to chat
    await addMessage({
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
      // In a real implementation, send to API with context of MUN data
      // Mock response for demonstration purposes
      setTimeout(async () => {
        const response = generateMockResponse(input);
        
        await addMessage({
          type: 'assistant',
          content: response
        });
        
        setIsProcessing(false);
      }, 1000);
      
    } catch (error) {
      console.error('Error processing input:', error)
      
      await addMessage({
        type: 'error',
        content: 'Sorry, I encountered an error processing your request. Please try again.'
      })
      
      toast({
        title: 'Error',
        description: 'Failed to process your message',
        variant: 'destructive'
      })
      
      setIsProcessing(false)
    }
  }
  
  // Simple mock response generator for testing
  const generateMockResponse = (input: string) => {
    const lowercaseInput = input.toLowerCase();
    
    if (lowercaseInput.includes('write') && lowercaseInput.includes('position paper')) {
      if (munData) {
        return `
          <div>
            <p>Here's a draft position paper for ${munData.positionCountry} on ${munData.topic}:</p>
            <div class="my-4 p-4 bg-muted/30 rounded-md">
              <h2 class="text-lg font-bold mb-2">Position Paper: ${munData.positionCountry} on ${munData.topic}</h2>
              <p class="mb-2"><strong>Committee:</strong> ${munData.committeeName}</p>
              <p class="mb-4"><strong>Topic:</strong> ${munData.topic}</p>
              
              <p class="mb-2">As a representative of ${munData.positionCountry}, we recognize the critical importance of addressing ${munData.topic}. Our nation has consistently advocated for a comprehensive approach that balances security concerns with the right to peaceful development.</p>
              
              <p class="mb-2">${munData.countryStance || "Our country strongly supports international cooperation on this issue while respecting national sovereignty."}</p>
              
              ${munData.keyPoints && munData.keyPoints.length > 0 ? 
                `<p class="mb-2">We emphasize the following key points:</p>
                <ul class="list-disc list-inside mb-4">
                  ${munData.keyPoints.map(point => `<li>${point}</li>`).join('')}
                </ul>`
                : ''}
                
              <p>Moving forward, ${munData.positionCountry} proposes the following solutions: increased diplomatic engagement, stronger verification mechanisms, and international aid programs to address root causes. We look forward to collaborating with all member states to develop a comprehensive resolution that addresses this critical global challenge.</p>
            </div>
            <p>Would you like me to expand on any particular section or make any revisions to this draft?</p>
          </div>
        `;
      } else {
        return "Before I can help write your position paper, please set up your MUN details using the 'Setup MUN Position' button.";
      }
    } else if (lowercaseInput.includes('research') || lowercaseInput.includes('information')) {
      return `
        <div>
          <p>Here are some key facts and research points on this topic:</p>
          <ul class="list-disc list-inside my-3">
            <li>The United Nations has adopted numerous resolutions addressing this issue since 1995</li>
            <li>Major international agreements include the Nuclear Non-Proliferation Treaty (NPT), which has been signed by 191 countries</li>
            <li>Regional tensions continue to complicate diplomatic efforts</li>
            <li>Economic sanctions have been used as both incentives and deterrents</li>
            <li>The IAEA plays a crucial role in verification and monitoring</li>
          </ul>
          <p>Would you like me to explore any of these points in more detail?</p>
        </div>
      `;
    } else {
      return `I'll help you with your question about ${input}. What specific aspects would you like me to address related to your position paper for ${munData?.positionCountry || 'your country'} on ${munData?.topic || 'this topic'}?`;
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
      
      default:
        return <div className="text-sm">{message.content}</div>
    }
  }
  
  const isLoading = isProfileLoading || isMunDataLoading;
  
  return (
    <>
      <div className="flex items-center justify-between p-2 border-b">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <span className="font-medium">Position Paper Assistant</span>
        </div>
        <MUNOnboardingModal buttonTrigger={true} />
      </div>
      
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[500px]">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      ) : (
        <div className="flex flex-col h-full max-h-[calc(100vh-120px)]">
          {/* Messages container */}
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
                <h3 className="text-xl font-semibold">Position Paper Assistant</h3>
                <p className="text-muted-foreground max-w-md">
                  I'll help you write a position paper for your Model UN conference. Set up your MUN details to get started.
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
              <div className="flex items-center justify-start mt-4">
                <div className="mr-3 flex-shrink-0">
                  <Avatar className="border-2 border-primary/20 h-9 w-9">
                    <div className="bg-gradient-to-br from-primary to-primary-foreground h-full w-full flex items-center justify-center">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                  </Avatar>
                </div>
                <div className="bg-card dark:bg-card/80 rounded-xl rounded-tl-none p-4 w-auto shadow-sm">
                  <LoadingSpinner size="small" />
                </div>
              </div>
            )}
            
            {/* Empty div for auto-scrolling */}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input area */}
          <div className="p-4 border-t bg-background">
            <div className="flex gap-2">
              <Textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message here..."
                className="min-h-12 resize-none flex-1"
                disabled={isProcessing || !currentChatId}
              />
              <Button 
                onClick={handleSendMessage} 
                size="icon" 
                className="shrink-0"
                disabled={isProcessing || !inputValue.trim() || !currentChatId}
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
            
            <div className="mt-2 text-xs text-muted-foreground text-center">
              {!munData ? (
                <span>Please set up your MUN details to get started</span>
              ) : (
                <span>Writing position paper for {munData.positionCountry} on {munData.topic}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
} 