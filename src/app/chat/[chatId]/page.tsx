"use client"

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { ChatInterface } from '@/components/chat-interface'
import { ChatList } from '@/components/chat-list'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { useAuth } from '@/lib/auth-context'
import { ArrowLeft, Menu } from 'lucide-react'

export default function ChatPage() {
  const params = useParams()
  const chatId = params?.chatId as string
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const { user } = useAuth()
  const { toast } = useToast()
  
  useEffect(() => {
    if (!user) {
      // Redirect to login if no user
      window.location.href = '/auth/login?redirect=/chat'
    }
  }, [user])
  
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    )
  }
  
  return (
    <div className="flex h-screen bg-background">
      {/* Mobile sidebar toggle */}
      <div className="md:hidden fixed top-4 left-4 z-20">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        >
          <Menu className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Sidebar */}
      <div 
        className={`
          fixed md:relative z-10 
          w-72 h-full border-r bg-background
          transition-transform duration-200 ease-in-out
          ${isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <ChatList userId={user.id} activeChat={chatId} />
      </div>
      
      {/* Mobile overlay */}
      {isMobileSidebarOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/20 z-[5]"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}
      
      {/* Main content */}
      <div className="flex-1 flex flex-col">
        <div className="border-b p-4 flex items-center">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => window.location.href = '/'}
            className="mr-2"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-xl font-semibold">MUN Connect</h1>
        </div>
        
        <div className="flex-1 overflow-hidden">
          <ChatInterface userId={user.id} chatId={chatId} />
        </div>
      </div>
    </div>
  )
} 