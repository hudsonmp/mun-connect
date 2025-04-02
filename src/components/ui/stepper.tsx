"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

// Stepper container
export interface StepperProps extends React.HTMLAttributes<HTMLDivElement> {
  activeStep: number
  orientation?: "horizontal" | "vertical"
  children: React.ReactNode
}

export function Stepper({
  activeStep,
  orientation = "horizontal",
  children,
  className,
  ...props
}: StepperProps) {
  return (
    <div 
      className={cn(
        "flex gap-4",
        orientation === "vertical" ? "flex-col" : "flex-row",
        className
      )} 
      {...props}
    >
      {React.Children.map(children, (child, index) => {
        if (!React.isValidElement(child)) {
          return child;
        }
        
        // We don't clone elements here to avoid type issues
        return (
          <div 
            className={cn(
              index === activeStep ? "block" : "hidden"
            )}
          >
            {child}
          </div>
        );
      })}
    </div>
  )
}

// Step component
export interface StepProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Step({
  children,
  className,
  ...props
}: StepProps) {
  return (
    <div 
      className={cn(
        "flex flex-col w-full",
        className
      )} 
      {...props}
    >
      {children}
    </div>
  )
}

// Step label
export interface StepLabelProps extends React.HTMLAttributes<HTMLDivElement> {
  optional?: React.ReactNode
}

export function StepLabel({
  children,
  optional,
  className,
  ...props
}: StepLabelProps) {
  return (
    <div 
      className={cn(
        "flex items-center gap-2 font-medium",
        className
      )} 
      {...props}
    >
      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
        <span className="text-sm">•</span>
      </div>
      <div>
        <div>{children}</div>
        {optional && <div className="text-xs text-muted-foreground">{optional}</div>}
      </div>
    </div>
  )
}

// Step content
export interface StepContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export function StepContent({
  children,
  className,
  ...props
}: StepContentProps) {
  return (
    <div 
      className={cn(
        "mt-2 ml-10 pl-4 border-l border-muted pb-8",
        className
      )} 
      {...props}
    >
      {children}
    </div>
  )
} 