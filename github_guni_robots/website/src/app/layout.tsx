import './globals.css';
import { ClerkProvider } from '@clerk/nextjs';
import { Navigation } from './components/navigation';
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});


export const metadata = {
  title: 'Humanoid Robot Control',
  description: 'Control your humanoid robot with advanced AI',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  console.log('Rendering RootLayout with ClerkProvider'); // Debug log
  return (
    <ClerkProvider>
      <html lang="en" className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <body className="bg-gray-900 text-white">
          
          <header className="container mx-auto p-4">
            <Navigation />
          </header>
          <main>{children}</main>
          <footer className="container mx-auto p-4 text-center">
            <p>© 2025 Humanoid Robot Control. All rights reserved.</p>
          </footer>
        </body>
      </html>
    </ClerkProvider>
  );
}