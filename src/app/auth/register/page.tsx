"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useAuth } from "@/lib/auth-context"
import { useToast } from "@/components/ui/use-toast"

export default function RegisterPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [validationError, setValidationError] = useState("")
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { signUp, error, clearError, isInitialized, isLoading } = useAuth()
  const { toast } = useToast()

  // Clear any auth errors when component mounts or unmounts
  useEffect(() => {
    clearError()
    return () => clearError()
  }, [clearError])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Prevent signup attempts if auth is not initialized
    if (!isInitialized) {
      console.error("Auth system not initialized")
      return
    }
    
    setLoading(true)
    setValidationError("")

    // Basic validation
    if (password !== confirmPassword) {
      setValidationError("Passwords do not match")
      setLoading(false)
      return
    }

    if (password.length < 6) {
      setValidationError("Password must be at least 6 characters")
      setLoading(false)
      return
    }

    try {
      const result = await signUp(email, password)
      
      if (result.success) {
        toast({
          title: "Registration successful",
          description: "Please check your email to confirm your account, then you can log in.",
        })
        router.push("/auth/login")
      }
    } catch (err) {
      // Error handling is managed by auth context
      console.error("Registration error:", err)
    } finally {
      setLoading(false)
    }
  }

  // Show either validation error or auth error
  const displayError = validationError || error

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">Create an account</CardTitle>
          <CardDescription>Enter your email and create a password to register</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {displayError && (
              <Alert variant="destructive">
                <AlertDescription>{displayError}</AlertDescription>
              </Alert>
            )}
            
            {!isInitialized && !isLoading && (
              <Alert variant="destructive">
                <AlertDescription>
                  Authentication system is not initialized. Please check your configuration or try again later.
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading || !isInitialized}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading || !isInitialized}
                required
              />
              <p className="text-xs text-muted-foreground">Password must be at least 6 characters</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading || !isInitialized}
                required
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={loading || !isInitialized}
            >
              {loading ? "Creating account..." : "Create account"}
            </Button>
          </CardFooter>
        </form>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-gray-600">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-blue-600 hover:text-blue-800">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
} 