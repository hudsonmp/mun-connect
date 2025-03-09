"use client"

import Link from "next/link"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Bell, Settings, User, Home } from "lucide-react"

export function DashboardHeader() {
  const [activeConference, setActiveConference] = useState("HMUN 2023")

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

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8 border-2 border-blue-200 dark:border-blue-800">
                  <AvatarImage src="/placeholder.svg?height=32&width=32" alt="User" />
                  <AvatarFallback>UN</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <User className="mr-2 h-4 w-4" />
                <span>Profile</span>
              </DropdownMenuItem>
              <DropdownMenuItem>Settings</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Log out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}

