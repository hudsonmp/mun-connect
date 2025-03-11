'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../lib/auth-context';
import { Loader2 } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (user) {
        // If user is logged in, redirect to dashboard
        router.replace('/dashboard');
      } else {
        // If no user, redirect to login
        router.replace('/login');
      }
    }
  }, [router, user, isLoading]);

  return (
    <div className="h-screen w-full flex flex-col items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
          Loading MUN Connect...
        </h1>
      </div>
    </div>
  );
} 