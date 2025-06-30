'use client';

import { useState } from 'react';

export default function RemoteControlPage() {
  const [robotStatus, setRobotStatus] = useState('Online');
  const [commandStatus, setCommandStatus] = useState('');

  const handleRemoteControl = async (action: string) => {
    setCommandStatus(`Sending command: ${action}`);
    try {
      const response = await fetch('http://localhost:8001/control-robot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to send command.');
      }
      const data = await response.json();
      setCommandStatus(data.message || `Command ${action} sent successfully!`);
    } catch (error) {
      setCommandStatus(`Error: ${error.message}`);
    }
    setTimeout(() => setCommandStatus(''), 3000);
  };

  const toggleRobotStatus = () => {
    setRobotStatus(robotStatus === 'Online' ? 'Offline' : 'Online');
  };

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-semibold">Remote Control</h2>
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
        <h3 className="text-xl font-bold mb-4">Control Robot</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => handleRemoteControl('move_forward')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
            disabled={robotStatus === 'Offline'}
          >
            Move Forward
          </button>
          <button
            onClick={() => handleRemoteControl('move_backward')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
            disabled={robotStatus === 'Offline'}
          >
            Move Backward
          </button>
          <button
            onClick={() => handleRemoteControl('left_handshake')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
            disabled={robotStatus === 'Offline'}
          >
            Left Handshake
          </button>
          <button
            onClick={() => handleRemoteControl('right_handshake')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
            disabled={robotStatus === 'Offline'}
          >
            Right Handshake
          </button>
        </div>
        {commandStatus && (
          <p className={`mt-4 ${commandStatus.includes('Error') ? 'text-red-400' : 'text-green-400'}`}>
            {commandStatus}
          </p>
        )}
      </div>
    </div>
  );
}