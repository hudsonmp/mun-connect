"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"
import { useAuth } from "@/lib/auth-context"
import { motion } from "framer-motion"
import { createClient } from '@supabase/supabase-js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

// Initialize Supabase client with URL and anon key
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export interface ConferenceFormProps {
  onSuccess?: (conferenceId?: number, conferenceName?: string) => void
  onCancel?: () => void
}

export function ConferenceForm({ onSuccess, onCancel }: ConferenceFormProps) {
  const { user } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    name: "",
    committee: "",
    role: "Delegate",
    dates: "",
    coDelegate: "",
    status: "upcoming"
  })

  // Auto-generate acronym
  const generateAcronym = (name: string) => {
    if (!name) return "";
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleSelectChange = (field: string, value: string) => {
    setFormData({
      ...formData,
      [field]: value
    });
  };

  const handleContinue = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast({
        title: "Conference name required",
        description: "Please enter a conference name",
        variant: "destructive",
      });
      return;
    }
    
    setStep(2);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!user?.id) {
      toast({
        title: "Authentication required",
        description: "Please sign in to add a conference",
        variant: "destructive",
      });
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Create a Supabase client
      const supabase = createClient(supabaseUrl, supabaseKey);
      
      // Generate acronym from name
      const acronym = generateAcronym(formData.name);
      
      // Create conference directly with Supabase
      const { data, error } = await supabase
        .from('conferences')
        .insert({
          user_id: user.id,
          name: formData.name,
          acronym: acronym,
          committee: formData.committee || "TBD",
          role: formData.role || "Delegate",
          dates: formData.dates || "",
          co_delegate: formData.coDelegate || "",
          status: formData.status || "upcoming",
          progress: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .select()
        .single();
      
      if (error) {
        throw new Error(error.message || "Failed to create conference");
      }
      
      toast({
        title: "Conference added",
        description: "Your conference has been added successfully",
      });
      
      if (onSuccess) onSuccess(data.id, data.name);
    } catch (error: any) {
      console.error("Conference creation error:", error);
      toast({
        title: "Error adding conference",
        description: error.message || "An unexpected error occurred",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card className="w-full max-w-md mx-auto">
        <CardHeader>
          <CardTitle>{step === 1 ? "New Conference" : "Conference Details"}</CardTitle>
          <CardDescription>
            {step === 1 
              ? "Enter your conference name to get started" 
              : "Add additional details about your conference"}
          </CardDescription>
        </CardHeader>
        
        {step === 1 ? (
          <form onSubmit={handleContinue}>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Conference Name *</Label>
                  <Input
                    id="name"
                    name="name"
                    placeholder="e.g., Harvard National Model United Nations"
                    value={formData.name}
                    onChange={handleInputChange}
                    className="text-lg"
                    autoFocus
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting || !formData.name.trim()}
              >
                Continue <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </CardFooter>
          </form>
        ) : (
          <form onSubmit={handleSubmit}>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="committee">Committee (Optional)</Label>
                  <Input
                    id="committee"
                    name="committee"
                    placeholder="e.g., UN Security Council"
                    value={formData.committee}
                    onChange={handleInputChange}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="role">Your Role</Label>
                  <Select
                    value={formData.role}
                    onValueChange={(value) => handleSelectChange("role", value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select your role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Delegate">Delegate</SelectItem>
                      <SelectItem value="Head Delegate">Head Delegate</SelectItem>
                      <SelectItem value="Chair">Chair</SelectItem>
                      <SelectItem value="Vice Chair">Vice Chair</SelectItem>
                      <SelectItem value="Director">Director</SelectItem>
                      <SelectItem value="Secretariat">Secretariat</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="dates">Conference Dates (Optional)</Label>
                  <Input
                    id="dates"
                    name="dates"
                    placeholder="e.g., Feb 10-13, 2024"
                    value={formData.dates}
                    onChange={handleInputChange}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="coDelegate">Co-Delegate Name (Optional)</Label>
                  <Input
                    id="coDelegate"
                    name="coDelegate"
                    placeholder="e.g., John Smith"
                    value={formData.coDelegate}
                    onChange={handleInputChange}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(value) => handleSelectChange("status", value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="upcoming">Upcoming</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep(1)}
              >
                Back
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Creating..." : "Add Conference"}
              </Button>
            </CardFooter>
          </form>
        )}
      </Card>
    </motion.div>
  )
} 