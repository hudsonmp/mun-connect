"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth-context'
import { ArrowRight } from 'lucide-react'

export default function Home() {
  const router = useRouter()
  const { user } = useAuth()
  const [isRedirecting, setIsRedirecting] = useState(false)
  
  const handleGetStarted = () => {
    setIsRedirecting(true)
    if (user) {
      router.push('/chat')
    } else {
      router.push('/auth/login?redirect=/chat')
    }
  }
  
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-background">
      <div className="max-w-3xl text-center">
        <h1 className="text-4xl font-bold sm:text-6xl mb-6">
          MUN Connect
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl mx-auto mb-10">
          AI-powered assistant to help you prepare and excel at Model UN conferences.
        </p>
        
        <Button 
          onClick={handleGetStarted} 
          className="px-8 py-6 text-lg"
          disabled={isRedirecting}
        >
          {isRedirecting ? 'Loading...' : 'Get Started'} 
          <ArrowRight className="ml-2 h-5 w-5" />
        </Button>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Position Papers</h3>
            <p className="text-muted-foreground">Generate well-researched position papers for your committee assignments.</p>
          </div>
          
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Resolutions</h3>
            <p className="text-muted-foreground">Draft effective resolutions with proper UN formatting and structure.</p>
          </div>
          
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Speeches</h3>
            <p className="text-muted-foreground">Create compelling speeches for opening statements and committee debates.</p>
          </div>
        </div>
      </div>
    </main>
  )
}

