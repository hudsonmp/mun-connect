"use client"

import React from "react"
import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "../../lib/auth-context"
import { Button } from "../../components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "../../components/ui/avatar"
import { Bell, Settings, User, Home, LogOut } from "lucide-react"
import { useToast } from "../../components/ui/use-toast"

export function DashboardHeader() {
  const { user, signOut, isProfileComplete } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [activeConference, setActiveConference] = useState("HMUN 2023")

  const handleSignOut = async () => {
    try {
      await signOut()
      toast({
        title: "Signed out",
        description: "You have been signed out successfully.",
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to sign out. Please try again.",
      })
    }
  }

  return (
    <header className="sticky top-0 z-50 h-16 w-full border-b bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 backdrop-blur supports-[backdrop-filter]:bg-opacity-80">
      <div className="flex h-16 items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-xl font-bold text-transparent">
              MUN Connect
            </span>
          </Link>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-[180px] justify-between border-blue-200 dark:border-blue-800">
                  {activeConference}
                  <span className="sr-only">Toggle conference</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[180px]">
                <DropdownMenuLabel>Switch Conference</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setActiveConference("HMUN 2023")}>HMUN 2023</DropdownMenuItem>
                <DropdownMenuItem onClick={() => setActiveConference("NMUN 2023")}>NMUN 2023</DropdownMenuItem>
                <DropdownMenuItem onClick={() => setActiveConference("WIMUN 2024")}>WIMUN 2024</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {user ? (
            <>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Notifications"
                className="text-blue-600 hover:text-blue-700 hover:bg-blue-100/50"
              >
                <Bell className="h-5 w-5" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                aria-label="Settings"
                className="text-blue-600 hover:text-blue-700 hover:bg-blue-100/50"
              >
                <Settings className="h-5 w-5" />
              </Button>
            </>
          ) : null}

          <Link href="/">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Return to Home"
              className="text-blue-600 hover:text-blue-700 hover:bg-blue-100/50"
            >
              <Home className="h-5 w-5" />
            </Button>
          </Link>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                  <Avatar className="h-8 w-8 border-2 border-blue-200 dark:border-blue-800">
                    <AvatarImage src="/placeholder.svg?height=32&width=32" alt="User" />
                    <AvatarFallback>
                      {user.email?.substring(0, 2).toUpperCase() || "UN"}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => router.push("/dashboard/profile")}>
                  <User className="mr-2 h-4 w-4" />
                  <span>Profile</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/dashboard/settings")}>
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleSignOut}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => router.push("/dashboard/login")}
                className="border-blue-200 dark:border-blue-800"
              >
                Log in
              </Button>
              <Button 
                size="sm"
                onClick={() => router.push("/dashboard/register")}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
              >
                Register
              </Button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

