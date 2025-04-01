"use client"

import React from "react"
import { Globe, LogOut, User } from "lucide-react"
import { ModeToggle } from "./mode-toggle"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth()
  const router = useRouter()

  const handleSignOut = async () => {
    try {
      await signOut()
    } catch (error) {
      console.error("Error signing out:", error)
    }
  }

  // Get initials for avatar fallback
  const getInitials = () => {
    if (!user?.email) return "U"
    const email = user.email
    return email.substring(0, 2).toUpperCase()
  }

  return (
    <div className="flex h-screen w-full overflow-hidden">
      {/* Simplified sidebar */}
      <div className="hidden w-64 flex-col bg-card p-4 border-r md:flex">
        <div className="flex items-center gap-2 mb-8">
          <Globe className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-semibold">MUN Connect</h1>
        </div>
        
        <nav className="flex-1 space-y-4">
          <div className="space-y-1">
            <NavLink href="/" icon={<Globe className="h-4 w-4" />} active>
              Dashboard
            </NavLink>
            <NavLink href="/documents" icon={<Globe className="h-4 w-4" />}>
              Documents
            </NavLink>
            <NavLink href="/research" icon={<Globe className="h-4 w-4" />}>
              Research
            </NavLink>
          </div>
        </nav>
        
        {/* User profile at bottom of sidebar */}
        <div className="mt-auto pt-4 border-t">
          <div className="flex items-center gap-2 mb-2">
            <Avatar className="h-8 w-8">
              <AvatarImage src="/placeholder.svg?height=32&width=32" alt="Avatar" />
              <AvatarFallback>{getInitials()}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="text-sm font-medium">{user?.email?.split('@')[0] || "User"}</span>
              <span className="text-xs text-muted-foreground truncate max-w-[140px]">
                {user?.email || ""}
              </span>
            </div>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            className="w-full justify-start" 
            onClick={handleSignOut}
          >
            <LogOut className="h-4 w-4 mr-2" />
            <span>Logout</span>
          </Button>
        </div>
      </div>
      
      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center border-b bg-background px-4 md:px-6">
          <button className="mr-2 rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground md:hidden">
            <Globe className="h-5 w-5" />
          </button>
          <div className="flex flex-1 items-center justify-between">
            <div className="md:hidden flex items-center gap-2">
              <Globe className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-semibold">MUN Connect</h1>
            </div>
            <div className="flex items-center gap-2">
              <ModeToggle />
              <ProfileButton 
                email={user?.email} 
                onSignOut={handleSignOut} 
                onProfile={() => router.push('/profile')} 
              />
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

// Simple ProfileButton component
function ProfileButton({ 
  email, 
  onSignOut, 
  onProfile 
}: { 
  email?: string, 
  onSignOut: () => void, 
  onProfile: () => void 
}) {
  return (
    <div className="flex items-center gap-2">
      <Button variant="ghost" size="icon" onClick={onProfile}>
        <User className="h-5 w-5" />
      </Button>
      <Button variant="ghost" size="icon" onClick={onSignOut}>
        <LogOut className="h-5 w-5" />
      </Button>
    </div>
  )
}

// Simple NavLink component
function NavLink({ 
  href, 
  icon, 
  active = false, 
  children 
}: { 
  href: string, 
  icon: React.ReactNode, 
  active?: boolean, 
  children: React.ReactNode 
}) {
  return (
    <a 
      href={href} 
      className={`flex items-center gap-2 px-3 py-2 text-sm rounded-md ${
        active 
          ? 'bg-primary/10 text-primary font-medium' 
          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
      }`}
    >
      {icon}
      <span>{children}</span>
    </a>
  )
}

