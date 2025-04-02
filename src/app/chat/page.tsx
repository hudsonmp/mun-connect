"use client"

import { useEffect, useState } from 'react'
import { AIChatInterface } from '@/components/ai-chat-interface'
import { ChatList } from '@/components/chat-list'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth-context'
import { 
  ArrowLeft,
  Menu,
  PanelLeftClose, 
  PanelLeft,
  Home,
  UserCircle,
  Plus,
  Settings,
  LogOut
} from 'lucide-react'
import { OnboardingModal } from '@/components/onboarding-modal'
import Link from 'next/link'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, signOut } = useAuth()
  
  // Track if we need a responsive layout
  const [isMobile, setIsMobile] = useState(false)
  
  useEffect(() => {
    // Check if we're on mobile
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768)
      // Auto-close sidebar on mobile
      if (window.innerWidth < 768) {
        setSidebarOpen(false)
      } else {
        setSidebarOpen(true)
      }
    }
    
    // Initial check
    checkIsMobile()
    
    // Add resize listener
    window.addEventListener('resize', checkIsMobile)
    return () => window.removeEventListener('resize', checkIsMobile)
  }, [])
  
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
      {/* Sidebar */}
      <div 
        className={cn(
          "fixed md:relative z-20 h-full bg-gradient-to-b from-background via-background to-muted/20",
          "border-r transition-all duration-300 ease-in-out",
          isMobile ? "w-[280px]" : "w-[260px]",
          !sidebarOpen && (isMobile ? "translate-x-[-280px]" : "w-16")
        )}
      >
        <div className={`h-full flex flex-col ${!sidebarOpen && !isMobile ? 'items-center pt-4' : ''}`}>
          {/* Sidebar header */}
          <div className="p-4 flex items-center justify-between">
            <h2 className={cn(
              "text-lg font-semibold transition-all",
              !sidebarOpen && !isMobile ? "opacity-0 w-0" : "opacity-100"
            )}>
              MUN Connect
            </h2>
            
            {sidebarOpen && (
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => setSidebarOpen(false)}
                className="md:flex"
              >
                <PanelLeftClose className="h-5 w-5" />
              </Button>
            )}
          </div>
          
          {/* User profile section */}
          <div className={cn(
            "px-4 py-2",
            !sidebarOpen && !isMobile ? "hidden" : "block"
          )}>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                <UserCircle className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{user.email}</p>
                <p className="text-xs text-muted-foreground truncate">Your AI Assistant</p>
              </div>
            </div>
            
            {/* Onboarding button */}
            <OnboardingModal buttonTrigger={true} />
          </div>
          
          <Separator className={!sidebarOpen && !isMobile ? "hidden" : "block my-2"} />
          
          {/* New chat button */}
          <div className={cn(
            "px-3 py-2",
            !sidebarOpen && !isMobile ? "px-0" : ""
          )}>
            <Link href="/chat" className="block w-full">
              <Button 
                variant="default" 
                className={cn(
                  "w-full gap-2",
                  !sidebarOpen && !isMobile ? "w-10 h-10 p-0" : ""
                )}
              >
                <Plus className="h-4 w-4" />
                <span className={!sidebarOpen && !isMobile ? "hidden" : "block"}>New Chat</span>
              </Button>
            </Link>
          </div>
          
          {/* Chat list */}
          <div className={cn(
            "flex-1 overflow-y-auto",
            !sidebarOpen && !isMobile ? "hidden" : "block"
          )}>
            <ChatList userId={user.id} activeChat="new" />
          </div>
          
          {/* Navigation buttons */}
          <div className={cn(
            "p-3 space-y-2",
            !sidebarOpen && !isMobile ? "flex flex-col items-center p-2" : ""
          )}>
            <Link href="/">
              <Button 
                variant="ghost" 
                className={cn(
                  "w-full justify-start",
                  !sidebarOpen && !isMobile ? "w-10 h-10 justify-center p-0" : ""
                )}
              >
                <Home className="h-4 w-4 mr-2" />
                <span className={!sidebarOpen && !isMobile ? "hidden" : "block"}>Home</span>
              </Button>
            </Link>
            
            <Link href="/settings">
              <Button 
                variant="ghost" 
                className={cn(
                  "w-full justify-start",
                  !sidebarOpen && !isMobile ? "w-10 h-10 justify-center p-0" : ""
                )}
              >
                <Settings className="h-4 w-4 mr-2" />
                <span className={!sidebarOpen && !isMobile ? "hidden" : "block"}>Settings</span>
              </Button>
            </Link>
            
            <Button 
              variant="ghost" 
              className={cn(
                "w-full justify-start",
                !sidebarOpen && !isMobile ? "w-10 h-10 justify-center p-0" : ""
              )}
              onClick={() => signOut()}
            >
              <LogOut className="h-4 w-4 mr-2" />
              <span className={!sidebarOpen && !isMobile ? "hidden" : "block"}>Logout</span>
            </Button>
          </div>
          
          {/* Toggle sidebar button - only visible on collapsed state */}
          {!sidebarOpen && !isMobile && (
            <div className="p-3">
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => setSidebarOpen(true)}
                className="mt-2"
              >
                <PanelLeft className="h-5 w-5" />
              </Button>
            </div>
          )}
        </div>
      </div>
      
      {/* Mobile overlay - only visible when sidebar is open on mobile */}
      {sidebarOpen && isMobile && (
        <div 
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-10"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Main content */}
      <div className="flex-1 flex flex-col w-full">
        <div className="border-b p-4 flex items-center">
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => window.location.href = '/'}
              className="mr-1"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            
            {/* Toggle sidebar button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeft className="h-5 w-5" />}
            </Button>
          </div>
          
          <h1 className="text-xl font-semibold ml-4">MUN Connect AI</h1>
        </div>
        
        <div className="flex-1 overflow-hidden">
          <AIChatInterface />
        </div>
      </div>
    </div>
  )
} 