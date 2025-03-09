import Link from "next/link"

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950">
      <div className="container mx-auto px-4 py-6">
        <header className="flex justify-center mb-8">
          <Link href="/" className="flex items-center space-x-2">
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-2xl font-bold text-transparent">
              MUN Connect
            </span>
          </Link>
        </header>
        <main>{children}</main>
      </div>
    </div>
  )
} 