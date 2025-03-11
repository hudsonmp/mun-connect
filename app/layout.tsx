"use client"

import type { ReactNode } from "react"
import React from "react"
import { AuthProvider } from "../projects/dashboard-mun-connect/lib/auth-context"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import { Toaster } from "../projects/dashboard-mun-connect/components/ui/toaster"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

interface RootLayoutProps {
  children: ReactNode
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>
          {children}
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  )
} 