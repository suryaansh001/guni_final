'use client';

import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Hero Section */}
      <section className="bg-gradient-to-r from-blue-600 to-purple-600 py-20 text-center">
        <div className="container mx-auto px-4">
          <h1 className="text-5xl font-bold mb-4">Welcome to Your Humanoid Robot</h1>
          <p className="text-xl mb-8">
            Experience cutting-edge AI with advanced language processing, voice interaction, face and emotion recognition, and global remote control.
          </p>
          <Link
            href="/user-dashboard"
            className="bg-white text-blue-600 font-semibold py-3 px-6 rounded-lg hover:bg-gray-200 transition"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/admin"
            className="bg-white text-blue-600 font-semibold py-3 px-6 rounded-lg hover:bg-gray-200 transition"
          >
            Admin Dashboard          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-semibold text-center mb-12">Robot Capabilities</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="bg-gray-800 p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-bold mb-2">LLM Support</h3>
              <p>Engage in natural, intelligent conversations powered by advanced language models.</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-bold mb-2">TTS/STT</h3>
              <p>Seamless text-to-speech and speech-to-text for effortless voice communication.</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-bold mb-2">Face Recognition</h3>
              <p>Accurately identify and recognize faces in real-time.</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-bold mb-2">Emotion Recognition</h3>
              <p>Understand and respond to human emotions dynamically.</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-bold mb-2">Remote Control</h3>
              <p>Control your robot from anywhere in the world with secure connectivity.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gray-800 py-16 text-center">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-semibold mb-4">Ready to Explore?</h2>
          <p className="text-lg mb-8">Join the future of robotics and take control of your humanoid robot today.</p>
          <Link
            href="/user-dashboard"
            className="bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-blue-700 transition"
          >
            Get Started
          </Link>
        </div>
      </section>
    </div>
  );
}