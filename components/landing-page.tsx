import { LandingHeader } from "./landing-header"
import { LandingHero } from "./landing-hero"
import { LandingFeatures } from "./landing-features"
import { LandingTestimonials } from "./landing-testimonials"
import { LandingCTA } from "./landing-cta"
import { LandingFooter } from "./landing-footer"

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col w-full">
      <LandingHeader />
      <main className="flex-1 w-full">
        <LandingHero />
        <LandingFeatures />
        <LandingTestimonials />
        <LandingCTA />
      </main>
      <LandingFooter />
    </div>
  )
}

