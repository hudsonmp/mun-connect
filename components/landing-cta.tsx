"use client"

import type React from "react"

import { useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "@/components/ui/use-toast"
import { Toaster } from "@/components/ui/toaster"

export function LandingCTA() {
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
    <section className="py-20">
      <div className="container">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          viewport={{ once: true }}
          className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-16 sm:px-12 sm:py-20"
        >
          <div className="relative z-10">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Ready to Transform Your MUN Experience?
              </h2>
              <p className="mt-4 text-lg text-blue-100">
                Join our waitlist today and be the first to access our platform when we launch.
              </p>
              <form
                onSubmit={handleSubmit}
                className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center"
              >
                <Input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-12 min-w-0 flex-1 bg-white/10 text-white placeholder:text-blue-100 focus-visible:ring-white sm:max-w-xs"
                />
                <Button type="submit" size="lg" className="w-full bg-white text-blue-600 hover:bg-blue-50 sm:w-auto">
                  Join Waitlist
                </Button>
              </form>
              <p className="mt-4 text-sm text-blue-100">Be part of the tech and diplomacy revolution.</p>
            </div>
          </div>

          {/* Decorative elements */}
          <div className="absolute left-1/2 top-0 -z-10 h-[120%] w-[120%] -translate-x-1/2 opacity-20 blur-3xl">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-500" />
          </div>
        </motion.div>
      </div>
      <Toaster />
    </section>
  )
}

