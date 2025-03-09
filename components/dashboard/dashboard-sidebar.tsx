"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { PenTool, BookOpen, Users, Globe, User } from "lucide-react"
import { cn } from "../../lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "../../components/ui/avatar"
import { useAuth } from "../../lib/auth-context"
import { supabase } from "../../lib/supabase"
import { Button } from "../../components/ui/button"

// Define the feature categories
const featureCategories = [
  {
    id: "write",
    name: "Write",
    icon: PenTool,
    href: "/dashboard/write",
  },
  {
    id: "prepare",
    name: "Prepare/Research",
    icon: BookOpen,
    href: "/dashboard/prepare",
  },
  {
    id: "conference",
    name: "At Conference",
    icon: Users,
    href: "/dashboard/conference",
  },
  {
    id: "network",
    name: "Network",
    icon: Globe,
    href: "/dashboard/network",
  },
]

export function DashboardSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user } = useAuth()
  const [isExpanded, setIsExpanded] = useState(false)
  const [hoverTimeout, setHoverTimeout] = useState<NodeJS.Timeout | null>(null)
  const [profileData, setProfileData] = useState<{
    username?: string;
    full_name?: string;
    country?: string;
  } | null>(null)
  
  // Add CSS variable to document root for sidebar width
  useEffect(() => {
    const root = document.documentElement
    root.style.setProperty('--sidebar-width', isExpanded ? '16rem' : '4rem')
    
    // Add a class to the main content to shift it
    const mainContent = document.querySelector('.dashboard-main')
    if (mainContent) {
      if (isExpanded) {
        mainContent.classList.remove('ml-16')
        mainContent.classList.add('ml-64')
      } else {
        mainContent.classList.remove('ml-64')
        mainContent.classList.add('ml-16')
      }
    }
  }, [isExpanded])

  // Fetch profile data
  useEffect(() => {
    async function fetchProfile() {
      if (!user) return
      
      try {
        const { data, error } = await supabase
          .from('profiles')
          .select('username, full_name, country')
          .eq('id', user.id)
          .single()
        
        if (error) {
          console.error('Error fetching profile:', error)
          return
        }
        
        if (data) {
          setProfileData(data)
        }
      } catch (error) {
        console.error('Error:', error)
      }
    }
    
    fetchProfile()
  }, [user])

  const handleMouseEnter = () => {
    // Clear any existing timeout
    if (hoverTimeout) {
      clearTimeout(hoverTimeout)
      setHoverTimeout(null)
    }
    setIsExpanded(true)
  }

  const handleMouseLeave = () => {
    // Add a delay before collapsing to make hover behavior more forgiving
    const timeout = setTimeout(() => {
      setIsExpanded(false)
    }, 300)
    setHoverTimeout(timeout)
  }

  return (
    <div
      className={cn(
        "fixed left-0 top-16 h-[calc(100vh-4rem)] z-40 transition-all duration-300 ease-in-out",
        isExpanded ? "w-64" : "w-16",
      )}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <aside className="h-full bg-gradient-to-b from-blue-50 to-white dark:from-blue-950/30 dark:to-background border-r border-blue-200 dark:border-blue-800">
        <div
          className={cn(
            "p-4 font-medium text-sm text-blue-600 transition-opacity duration-300",
            isExpanded ? "opacity-100" : "opacity-0",
          )}
        >
          FEATURES
        </div>

        <nav className="flex-1">
          <ul className="space-y-2 px-3 py-2">
            {featureCategories.map((category) => {
              const isActive = pathname.startsWith(`/dashboard/${category.id}`)
              
              return (
                <li
                  key={category.id}
                  className="relative"
                >
                  <Link
                    href={category.href}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-3 text-sm font-medium transition-all duration-300",
                      isActive
                        ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
                        : "hover:bg-blue-100/80 dark:hover:bg-blue-900/20 text-blue-800 dark:text-blue-200",
                      !isExpanded && "justify-center",
                    )}
                  >
                    <category.icon className="h-5 w-5 flex-shrink-0" />
                    <span 
                      className={cn(
                        "transition-all duration-300 whitespace-nowrap", 
                        isExpanded ? "opacity-100 w-auto" : "opacity-0 w-0 overflow-hidden"
                      )}
                    >
                      {category.name}
                    </span>
                  </Link>
                </li>
              )
            })}
            
            {/* Profile link */}
            <li className="relative">
              <Link
                href="/profile"
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-3 text-sm font-medium transition-all duration-300",
                  pathname === "/profile"
                    ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
                    : "hover:bg-blue-100/80 dark:hover:bg-blue-900/20 text-blue-800 dark:text-blue-200",
                  !isExpanded && "justify-center",
                )}
              >
                <User className="h-5 w-5 flex-shrink-0" />
                <span 
                  className={cn(
                    "transition-all duration-300 whitespace-nowrap", 
                    isExpanded ? "opacity-100 w-auto" : "opacity-0 w-0 overflow-hidden"
                  )}
                >
                  Profile
                </span>
              </Link>
            </li>
          </ul>
        </nav>

        <div
          className={cn(
            "absolute bottom-0 left-0 right-0 p-4 border-t border-blue-200 dark:border-blue-800 transition-all duration-300",
            isExpanded ? "opacity-100" : "opacity-0",
          )}
        >
          {user ? (
            <div className="flex items-center gap-3">
              <Avatar className="h-8 w-8 border-2 border-blue-200 dark:border-blue-800">
                <AvatarImage src="/placeholder.svg?height=32&width=32" alt="User" />
                <AvatarFallback>
                  {profileData?.username?.substring(0, 2).toUpperCase() || 
                   user.email?.substring(0, 2).toUpperCase() || "UN"}
                </AvatarFallback>
              </Avatar>
              <div className={cn("transition-all duration-300", isExpanded ? "opacity-100" : "opacity-0")}>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  {profileData?.full_name || profileData?.username || user.email?.split('@')[0] || "User"}
                </p>
                <p className="text-xs text-blue-600/70 dark:text-blue-400/70">
                  {profileData?.country || "Set your country"}
                </p>
              </div>
            </div>
          ) : (
            <div className={cn("transition-all duration-300", isExpanded ? "opacity-100" : "opacity-0")}>
              <Button 
                onClick={() => router.push("/login")}
                className="w-full mb-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
              >
                Log in
              </Button>
              <Button 
                variant="outline"
                onClick={() => router.push("/register")}
                className="w-full border-blue-200 dark:border-blue-800"
              >
                Register
              </Button>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}

