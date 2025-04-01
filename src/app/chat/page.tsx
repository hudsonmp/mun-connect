"use client"

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createChat, listUserChats } from '@/lib/chat-service'
import { useAuth } from '@/lib/auth-context'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

export default function ChatIndexPage() {
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const { user } = useAuth()
  
  useEffect(() => {
    const initializeChat = async () => {
      if (!user) {
        // Redirect to login if no user
        router.push('/auth/login?redirect=/chat')
        return
      }
      
      setIsLoading(true)
      
      try {
        // Check if user has any existing chats
        const { chats, error } = await listUserChats(user.id)
        
        if (error) throw error
        
        if (chats && chats.length > 0) {
          // Redirect to the most recent chat
          router.push(`/chat/${chats[0].id}`)
        } else {
          // Create a new chat and redirect
          const { chat, error: createError } = await createChat(user.id)
          
          if (createError) throw createError
          
          if (chat) {
            router.push(`/chat/${chat.id}`)
          } else {
            throw new Error('Failed to create chat')
          }
        }
      } catch (error) {
        console.error('Error initializing chat:', error)
        // If all else fails, just redirect to home
        router.push('/')
      } finally {
        setIsLoading(false)
      }
    }
    
    initializeChat()
  }, [user, router])
  
  return (
    <div className="flex items-center justify-center min-h-screen">
      {isLoading && (
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-muted-foreground">Preparing your chat...</p>
        </div>
      )}
    </div>
  )
} 