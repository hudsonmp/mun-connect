"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { v4 as uuidv4 } from 'uuid'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { PlusCircle, MessageCircle, Trash2 } from 'lucide-react'
import { useToast } from '@/components/ui/use-toast'
import { listUserChats, createChat, deleteChat } from '@/lib/chat-service'
import type { Chat } from '@/lib/chat-service'

interface ChatListProps {
  userId: string
  activeChat?: string
}

export function ChatList({ userId, activeChat }: ChatListProps) {
  const [chats, setChats] = useState<Chat[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const { toast } = useToast()

  // Load user's chats
  useEffect(() => {
    const loadChats = async () => {
      setIsLoading(true)
      const { chats, error } = await listUserChats(userId)
      
      if (chats && !error) {
        setChats(chats)
      } else {
        console.error('Error loading chats:', error)
        toast({
          title: 'Error',
          description: 'Failed to load chat history',
          variant: 'destructive',
        })
      }
      
      setIsLoading(false)
    }
    
    if (userId) {
      loadChats()
    }
  }, [userId])
  
  // Handle creating a new chat
  const handleNewChat = async () => {
    const { chat, error } = await createChat(userId)
    
    if (chat && !error) {
      setChats(prev => [chat, ...prev])
      router.push(`/chat/${chat.id}`)
    } else {
      console.error('Error creating new chat:', error)
      toast({
        title: 'Error',
        description: 'Failed to create a new chat',
        variant: 'destructive',
      })
    }
  }
  
  // Handle selecting a chat
  const handleSelectChat = (chatId: string) => {
    router.push(`/chat/${chatId}`)
  }
  
  // Handle deleting a chat
  const handleDeleteChat = async (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation() // Prevent selecting the chat when deleting
    
    const { success, error } = await deleteChat(chatId)
    
    if (success && !error) {
      setChats(prev => prev.filter(chat => chat.id !== chatId))
      toast({
        title: 'Success',
        description: 'Chat deleted successfully',
      })
      
      // If the active chat was deleted, redirect to a new chat
      if (activeChat === chatId) {
        handleNewChat()
      }
    } else {
      console.error('Error deleting chat:', error)
      toast({
        title: 'Error',
        description: 'Failed to delete chat',
        variant: 'destructive',
      })
    }
  }
  
  // Format date for display
  const formatDate = (date: Date) => {
    if (isToday(date)) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }
  
  // Check if a date is today
  const isToday = (date: Date) => {
    const today = new Date()
    return date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
  }
  
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <Button 
          onClick={handleNewChat} 
          className="w-full" 
          variant="default"
        >
          <PlusCircle className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {isLoading ? (
          // Loading skeletons
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center space-x-4 mb-4">
              <Skeleton className="h-12 w-12 rounded-full" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-3 w-[200px]" />
              </div>
            </div>
          ))
        ) : chats.length > 0 ? (
          // Chat list
          chats.map(chat => (
            <Card 
              key={chat.id}
              onClick={() => handleSelectChat(chat.id)}
              className={`p-3 cursor-pointer hover:bg-accent transition-colors ${
                activeChat === chat.id ? 'bg-accent' : ''
              }`}
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-3">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <MessageCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <div className="font-medium truncate max-w-[200px]">
                      {chat.title || 'New Chat'}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(chat.updatedAt)}
                    </div>
                  </div>
                </div>
                
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => handleDeleteChat(e, chat.id)}
                  className="opacity-0 group-hover:opacity-100 hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))
        ) : (
          // Empty state
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground py-12">
            <MessageCircle className="h-12 w-12 mb-4 opacity-20" />
            <p className="text-center">No chats yet</p>
            <p className="text-center text-sm">Start a new conversation to create your first chat</p>
          </div>
        )}
      </div>
    </div>
  )
} 