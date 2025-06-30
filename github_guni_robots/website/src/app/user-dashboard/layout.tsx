import { ReactNode } from 'react';
import Link from 'next/link';

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <nav className="bg-gray-800 p-4 shadow-md">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold">Humanoid Robot Dashboard</h1>
          <div className="space-x-4">
            <Link href="/user-dashboard" className="hover:text-blue-400">Home</Link>
            <Link href="/user-dashboard/face-recognition" className="hover:text-blue-400">Face Recognition</Link>
            <Link href="/user-dashboard/remote-control" className="hover:text-blue-400">Remote Control</Link>
            <Link href="/user-dashboard/voice-interaction" className="hover:text-blue-400">Voice Interaction</Link>
            <Link href="/user-dashboard/predefined-knowledge" className="hover:text-blue-400">Profile</Link>
            <Link href="/sign-out" className="hover:text-blue-400">Logout</Link>
          </div>
        </div>
      </nav>
      <main className="container mx-auto p-6">{children}</main>
      <footer className="bg-gray-800 p-4 mt-8">
        <div className="container mx-auto text-center">
          <p>© 2025 Humanoid Robot Control. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}