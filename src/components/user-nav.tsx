"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { User, LogOut } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"

export function UserNav() {
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
    <div className="flex items-center gap-2">
      <Button 
        variant="ghost" 
        size="icon" 
        onClick={() => router.push('/profile')}
        title="Profile"
      >
        <User className="h-5 w-5" />
      </Button>
      <Avatar title={user?.email || "User"} className="cursor-pointer" onClick={() => router.push('/profile')}>
        <AvatarImage src="/placeholder.svg?height=32&width=32" alt="User" />
        <AvatarFallback>{getInitials()}</AvatarFallback>
      </Avatar>
      <Button 
        variant="ghost" 
        size="icon" 
        onClick={handleSignOut}
        title="Sign out"
      >
        <LogOut className="h-5 w-5" />
      </Button>
    </div>
  )
}

