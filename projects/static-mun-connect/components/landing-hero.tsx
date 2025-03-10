"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { toast } from "./ui/use-toast"
import { Toaster } from "./ui/toaster"

export function LandingHero() {
  const [email, setEmail] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // This would connect to your backend service
    // For now, we'll just show a toast notification
    toast({
      title: "Success!",
      description: "You've been added to our waitlist. We'll notify you when we launch!",
    })

    setEmail("")
  }

  return (
    <section className="relative overflow-hidden py-20 md:py-32">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-blue-950/20 dark:via-indigo-950/20 dark:to-purple-950/20" />

      {/* Animated shapes */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-blue-400/20 blur-3xl"
          animate={{
            x: [0, 10, 0],
            y: [0, 15, 0],
          }}
          transition={{
            repeat: Number.POSITIVE_INFINITY,
            duration: 8,
            ease: "easeInOut",
          }}
        />
        <motion.div
          className="absolute top-1/2 left-1/4 h-64 w-64 rounded-full bg-indigo-400/20 blur-3xl"
          animate={{
            x: [0, -20, 0],
            y: [0, 10, 0],
          }}
          transition={{
            repeat: Number.POSITIVE_INFINITY,
            duration: 10,
            ease: "easeInOut",
          }}
        />
        <motion.div
          className="absolute bottom-20 right-1/4 h-72 w-72 rounded-full bg-purple-400/20 blur-3xl"
          animate={{
            x: [0, 15, 0],
            y: [0, -15, 0],
          }}
          transition={{
            repeat: Number.POSITIVE_INFINITY,
            duration: 9,
            ease: "easeInOut",
          }}
        />
      </div>

      <div className="container relative z-10">
        <div className="mx-auto max-w-3xl text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <h1 className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl md:text-6xl">
              Revolutionize Your MUN Experience
            </h1>
            <p className="mt-6 text-lg text-muted-foreground md:text-xl">
              Join the tech and diplomacy revolution. MUN Connect brings AI-powered tools, real-time collaboration, and
              professional networking to Model UN delegates worldwide.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-10"
          >
            <form onSubmit={handleSubmit} className="mx-auto flex max-w-md flex-col gap-2 sm:flex-row">
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-12"
              />
              <Button
                type="submit"
                size="lg"
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
              >
                Join Waitlist
              </Button>
            </form>
            <p className="mt-3 text-xs text-muted-foreground">Be the first to know when we launch. No spam, ever.</p>
          </motion.div>
        </div>
      </div>
      <Toaster />
    </section>
  )
}

