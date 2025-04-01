"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { DashboardContent } from "@/components/dashboard-content"
import { ChatInterface } from "@/components/chat-interface"
import { useAuth } from "@/lib/auth-context"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { LayoutDashboard, MessageSquare } from "lucide-react"

export default function Home() {
  const { user } = useAuth()
  const [viewMode, setViewMode] = useState<'chat' | 'dashboard'>('chat')
  
  return (
    <DashboardLayout>
      <div className="h-full flex flex-col">
        <div className="flex justify-end mb-4 gap-2">
          <Button 
            variant={viewMode === 'chat' ? 'default' : 'outline'} 
            size="sm"
            onClick={() => setViewMode('chat')}
            className="flex items-center gap-1"
          >
            <MessageSquare className="h-4 w-4" />
            Chat
          </Button>
          <Button 
            variant={viewMode === 'dashboard' ? 'default' : 'outline'} 
            size="sm"
            onClick={() => setViewMode('dashboard')}
            className="flex items-center gap-1"
          >
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Button>
        </div>
        
        {viewMode === 'chat' ? (
          <div className="flex-1 overflow-hidden border rounded-md">
            {user ? (
              <ChatInterface userId={user.id} />
            ) : (
              <div className="flex items-center justify-center h-full">
                <p>Please log in to use the chat interface</p>
              </div>
            )}
          </div>
        ) : (
          <DashboardContent />
        )}
      </div>
    </DashboardLayout>
  )
}

