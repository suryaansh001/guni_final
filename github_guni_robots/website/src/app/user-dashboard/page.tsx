'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useUser } from '@clerk/nextjs';

export default function DashboardPage() {
  const [robotStatus, setRobotStatus] = useState('Online');
  const [command, setCommand] = useState('');
  const [summary, setSummary] = useState('');
  const { user } = useUser();

  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) {
      setSummary('Please sign in to send commands.');
      return;
    }
    try {
      const response = await fetch('http://localhost:8001/process-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: command,
          user_name: user.firstName || user.username || 'Anonymous',
          thread_id: `thread_${user.id}`,
        }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process command.');
      }
      const data = await response.json();
      setSummary(data.response);
      setCommand('');
    } catch (error) {
      setSummary(`Error: ${error.message}`);
    }
  };

  const toggleRobotStatus = () => {
    setRobotStatus(robotStatus === 'Online' ? 'Offline' : 'Online');
  };

  useEffect(() => {
    if (user) {
      fetch(`http://localhost:8001/get-summary/${user.firstName || user.username || 'Anonymous'}`)
        .then(res => res.json())
        .then(data => setSummary(data.summary))
        .catch(() => setSummary('No previous conversations found.'));
    }
  }, [user]);

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-semibold">Robot Control Dashboard</h2>
      <div className="bg-gray-800 p-6 rounded-lg shadow-md">
        <h3 className="text-xl font-bold mb-4">Robot Status</h3>
        <p className="text-lg">
          Status: <span className={robotStatus === 'Online' ? 'text-green-400' : 'text-red-400'}>{robotStatus}</span>
        </p>
        <button
          onClick={toggleRobotStatus}
          className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
        >
          Toggle {robotStatus === 'Online' ? 'Offline' : 'Online'}
        </button>
      </div>
      <div className="bg-gray-800 p-6 rounded-lg shadow-md">
        <h3 className="text-xl font-bold mb-4">Conversation Summary</h3>
        <p className="text-lg">{summary || 'No summary available.'}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-bold mb-2">LLM Support</h3>
          <p>Interact with advanced language models.</p>
          <Link
            href="/user-dashboard/voice-interaction"
            className="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
          >
            Voice Interaction
          </Link>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-bold mb-2">TTS/STT</h3>
          <p>Seamless voice communication.</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-bold mb-2">Face Recognition</h3>
          <p>Identify faces with accuracy.</p>
          <Link
            href="/user-dashboard/face-recognition"
            className="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
          >
            Enable Face Recognition
          </Link>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-bold mb-2">Emotion Recognition</h3>
          <p>Detect human emotions.</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-bold mb-2">Remote Control</h3>
          <p>Control from anywhere.</p>
          <Link
            href="/user-dashboard/remote-control"
            className="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
          >
            Go to Remote Control
          </Link>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-md">
          <h3 className="text-xl font-bold mb-2">User Profile</h3>
          <p>Customize your interactions.</p>
          <Link
            href="/user-dashboard/predefined-knowledge"
            className="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
          >
            Upload Profile
          </Link>
        </div>
      </div>
      <div className="bg-gray-800 p-6 rounded-lg shadow-md">
        <h3 className="text-xl font-bold mb-4">Send Text Command</h3>
        <form onSubmit={handleCommandSubmit} className="flex space-x-4">
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Enter command (e.g., 'move forward')"
            className="flex-1 p-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}