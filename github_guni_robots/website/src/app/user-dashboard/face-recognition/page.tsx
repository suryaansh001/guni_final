'use client';

import { useState, useEffect, useRef } from 'react';

export default function FaceRecognitionPage() {
  const [name, setName] = useState('');
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [message, setMessage] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraOn(true);
      }
    } catch (err) {
      console.error('Error accessing camera:', err);
      setMessage('Could not access camera. Check permissions.');
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
      setIsCameraOn(false);
    }
  };

  const captureImage = async () => {
    if (!name) {
      setMessage('Please enter a name.');
      return;
    }
    if (videoRef.current && canvasRef.current) {
      const context = canvasRef.current.getContext('2d');
      if (context) {
        canvasRef.current.width = videoRef.current.videoWidth;
        canvasRef.current.height = videoRef.current.videoHeight;
        context.drawImage(videoRef.current, 0, 0);
        const imageData = canvasRef.current.toDataURL('image/jpeg');
        
        try {
          // Send subject name to /receive-subject
          const subjectResponse = await fetch('http://localhost:8001/receive-subject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject: name }),
          });
          if (!subjectResponse.ok) {
            const error = await subjectResponse.json();
            throw new Error(error.detail || 'Failed to register subject.');
          }

          // Store image in sessionStorage for profile upload
          sessionStorage.setItem('facePhoto', imageData);
          setMessage(`Face registered for ${name}!`);
          setName('');
          stopCamera();
          setTimeout(() => setMessage(''), 3000);
        } catch (error) {
          setMessage(`Error: ${error.message}`);
        }
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    captureImage();
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-semibold">Face Recognition Registration</h2>
      <div className="bg-gray-800 p-6 rounded-lg shadow-md">
        <h3 className="text-xl font-bold mb-4">Register Face</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-1">
              Name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter name"
              className="w-full p-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <div className="flex space-x-4">
            {!isCameraOn ? (
              <button
                type="button"
                onClick={startCamera}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
              >
                Start Camera
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={stopCamera}
                  className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded"
                >
                  Stop Camera
                </button>
                <button
                  type="submit"
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded"
                >
                  Capture Face
                </button>
              </>
            )}
          </div>
        </form>
        {message && (
          <p className={`mt-4 ${message.includes('Error') ? 'text-red-400' : 'text-green-400'}`}>
            {message}
          </p>
        )}
        <div className="mt-6 flex justify-center">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="w-full max-w-md rounded-lg"
            style={{ display: isCameraOn ? 'block' : 'none' }}
          />
        </div>
        <canvas ref={canvasRef} style={{ display: 'none' }} />
      </div>
    </div>
  );
}