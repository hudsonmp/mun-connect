"use client"

import type { ReactNode } from "react"
import React from "react"
import { AuthProvider } from "../lib/auth-context"
import { Geist, Geist_Mono } from "next/font/google"
import "../globals.css"
import { Toaster } from "../components/ui/toaster"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

// Metadata is defined in a separate metadata file since this is a client component

interface RootLayoutProps {
  children: ReactNode
}

export default function RootLayout({
  children,
}: Readonly<RootLayoutProps>) {
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