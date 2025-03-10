"use client"

import React from "react"
import { motion } from "framer-motion"
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar"
import { Card, CardContent } from "./ui/card"

const testimonials = [
  {
    quote: "MUN Connect transformed how I prepare for conferences. The AI tools are game-changing!",
    name: "Alex Johnson",
    role: "Harvard MUN Delegate",
    avatar: "/placeholder.svg?height=40&width=40",
  },
  {
    quote: "As a MUN advisor, I've seen my students' performance improve dramatically with MUN Connect.",
    name: "Dr. Sarah Chen",
    role: "MUN Faculty Advisor",
    avatar: "/placeholder.svg?height=40&width=40",
  },
  {
    quote: "The networking features helped me connect with diplomats and secure an internship at the UN.",
    name: "Miguel Sanchez",
    role: "NMUN Outstanding Delegate",
    avatar: "/placeholder.svg?height=40&width=40",
  },
]

export function LandingTestimonials() {
  return (
    <section className="py-20 bg-muted/50">
      <div className="container">
        <div className="mx-auto max-w-3xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">What Our Users Say</h2>
          <p className="mt-4 text-muted-foreground">
            Join thousands of delegates who have elevated their MUN experience with our platform.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              viewport={{ once: true }}
            >
              <Card className="h-full">
                <CardContent className="p-6">
                  <div className="flex flex-col h-full">
                    <blockquote className="flex-1 mb-6 text-lg italic">&quot;{testimonial.quote}&quot;</blockquote>
                    <div className="flex items-center">
                      <Avatar className="h-10 w-10 mr-3">
                        <AvatarImage src={testimonial.avatar} alt={testimonial.name} />
                        <AvatarFallback>{testimonial.name.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium">{testimonial.name}</div>
                        <div className="text-sm text-muted-foreground">{testimonial.role}</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

