'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function PredefinedKnowledgePage() {
  const [name, setName] = useState('');
  const [hobbies, setHobbies] = useState('');
  const [background, setBackground] = useState('');
  const [preferences, setPreferences] = useState('');
  const [message, setMessage] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) {
      setMessage('Name is required.');
      return;
    }
    const facePhoto = sessionStorage.getItem('facePhoto');
    if (!facePhoto) {
      setMessage('Please register your face first.');
      router.push('/user-dashboard/face-recognition');
      return;
    }

    const profileData = {
      name: name.trim(),
      face_photo: facePhoto,
      info: {
        hobbies: hobbies ? hobbies.split(',').map(h => h.trim()) : [],
        background: background.trim(),
        preferences: preferences.trim(),
      },
    };

    try {
      const formData = new FormData();
      const jsonBlob = new Blob([JSON.stringify(profileData)], { type: 'application/json' });
      formData.append('file', jsonBlob, 'profile.json');

      const response = await fetch('http://localhost:8001/upload-profile', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to upload profile.');
      }

      const data = await response.json();
      setMessage(data.message || 'Profile uploaded successfully!');
      sessionStorage.removeItem('facePhoto');
      setName('');
      setHobbies('');
      setBackground('');
      setPreferences('');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-semibold">Profile Upload</h2>
      <div className="bg-gray-800 p-6 rounded-lg shadow-md">
        <h3 className="text-xl font-bold mb-4">Personalize Your Assistant</h3>
        <p className="mb-4">Enter your details to customize the robot's interactions.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-1">
              Your Name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
              className="w-full p-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <div>
            <label htmlFor="hobbies" className="block text-sm font-medium mb-1">
              Hobbies (comma-separated)
            </label>
            <input
              id="hobbies"
              type="text"
              value={hobbies}
              onChange={(e) => setHobbies(e.target.value)}
              placeholder="e.g., coding, gaming"
              className="w-full p-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <div>
            <label htmlFor="background" className="block text-sm font-medium mb-1">
              Background
            </label>
            <textarea
              id="background"
              value={background}
              onChange={(e) => setBackground(e.target.value)}
              placeholder="e.g., Computer Science student"
              className="w-full p-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-600"
              rows={4}
            />
          </div>
          <div>
            <label htmlFor="preferences" className="block text-sm font-medium mb-1">
              Preferences
            </label>
            <textarea
              id="preferences"
              value={preferences}
              onChange={(e) => setPreferences(e.target.value)}
              placeholder="e.g., Likes concise responses"
              className="w-full p-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-600"
              rows={4}
            />
          </div>
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
          >
            Submit Profile
          </button>
        </form>
        {message && (
          <p className={`mt-4 ${message.includes('Error') ? 'text-red-400' : 'text-green-400'}`}>
            {message}
          </p>
        )}
      </div>
    </div>
  );
}