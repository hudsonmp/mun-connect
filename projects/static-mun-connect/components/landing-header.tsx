"use client"

import React from "react"
import Link from "next/link"
import { useState } from "react"
import { Button } from "./ui/button"
import { Menu, X } from "lucide-react"
import { useRouter } from "next/navigation"

export function LandingHeader() {
  const router = useRouter()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  
  // Dashboard URL - this should be configurable based on environment
  const dashboardUrl = process.env.NEXT_PUBLIC_DASHBOARD_URL || "https://mun-connect-dashboard.vercel.app"

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-2">
          <Link href="/" className="flex items-center space-x-2">
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-xl font-bold text-transparent">
              MUN Connect
            </span>
          </Link>
        </div>

        {/* Mobile menu button */}
        <button className="block md:hidden" onClick={() => setIsMenuOpen(!isMenuOpen)}>
          {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        {/* Desktop navigation */}
        <nav className="hidden md:flex items-center gap-6">
          <Link href="/" className="text-sm font-medium transition-colors hover:text-primary">
            Home
          </Link>
          <Link
            href="/about"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            About Us
          </Link>
          <Link
            href="/contact"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            Contact
          </Link>
          <Link
            href="/waitlist"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            Waitlist
          </Link>
          <Link
            href="/resources"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            Resources
          </Link>
          <Link
            href="/features"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            Features
          </Link>
          
          <div className="flex items-center gap-2">
            <Link href={`${dashboardUrl}/dashboard/login`} passHref>
              <Button variant="outline">
                Log in
              </Button>
            </Link>
            <Link href={`${dashboardUrl}/dashboard/register`} passHref>
              <Button
                variant="default"
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
              >
                Register
              </Button>
            </Link>
          </div>
        </nav>

        {/* Mobile navigation */}
        {isMenuOpen && (
          <div className="absolute top-16 left-0 right-0 bg-background border-b md:hidden">
            <div className="container py-4 flex flex-col gap-4">
              <Link href="/" className="text-sm font-medium transition-colors hover:text-primary">
                Home
              </Link>
              <Link
                href="/about"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
              >
                About Us
              </Link>
              <Link
                href="/contact"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
              >
                Contact
              </Link>
              <Link
                href="/waitlist"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
              >
                Waitlist
              </Link>
              <Link
                href="/resources"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
              >
                Resources
              </Link>
              <Link
                href="/features"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
              >
                Features
              </Link>
              
              <Link href={`${dashboardUrl}/dashboard/login`} passHref className="w-full">
                <Button variant="outline" className="w-full">
                  Log in
                </Button>
              </Link>
              <Link href={`${dashboardUrl}/dashboard/register`} passHref className="w-full">
                <Button
                  variant="default"
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                >
                  Register
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

