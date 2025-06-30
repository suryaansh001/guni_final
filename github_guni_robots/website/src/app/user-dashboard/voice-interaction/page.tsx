"use client";
import { useState, useRef, Suspense } from 'react';
import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

function VoiceInteractionContent() {
  const [isRecording, setIsRecording] = useState(false);
  const [message, setMessage] = useState('');
  const [transcription, setTranscription] = useState('');
  const [emotion, setEmotion] = useState('');
  const [responseText, setResponseText] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);
  const timeoutRef = useRef(null);
  const isConversationActive = useRef(false);
  
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const threadId = useRef(`thread_${crypto.randomUUID()}`);

  const getSupportedMimeType = () => {
    const types = ['audio/webm', 'audio/mp4', 'audio/wav'];
    return types.find(type => MediaRecorder.isTypeSupported(type)) || null;
  };

  const convertToWav = async (blob) => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    const offlineContext = new OfflineAudioContext(1, audioBuffer.length, 16000);
    const source = offlineContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(offlineContext.destination);
    source.start();
    const renderedBuffer = await offlineContext.startRendering();
    const wavBlob = audioBufferToWav(renderedBuffer);
    return wavBlob;
  };

  const audioBufferToWav = (buffer) => {
    const wavLength = buffer.length + 44;
    const bufferArray = new ArrayBuffer(wavLength);
    const view = new DataView(bufferArray);
    const writeString = (str, offset) => {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    };
    writeString('RIFF', 0);
    view.setUint32(4, 36 + buffer.length * 2, true);
    writeString('WAVE', 8);
    writeString('fmt ', 12);
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, 16000, true);
    view.setUint32(28, 32000, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString('data', 36);
    view.setUint32(40, buffer.length * 2, true);
    const samples = buffer.getChannelData(0);
    for (let i = 0; i < samples.length; i++) {
      view.setInt16(44 + i * 2, samples[i] * 0x7FFF, true);
    }
    return new Blob([bufferArray], { type: 'audio/wav' });
  };

  const startRecording = async () => {
    if (!isLoaded || !user) {
      setMessage('Please sign in to use voice interaction.');
      router.push('/sign-in');
      return;
    }

    try {
      const mimeType = getSupportedMimeType();
      if (!mimeType) throw new Error('No supported audio MIME type.');
      console.log(`Starting recording in ${mimeType}`);
      setMessage(`Recording in ${mimeType}...`);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        console.log('Recording stopped');
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        let finalBlob = audioBlob;
        if (mimeType !== 'audio/wav') {
          console.log('Converting to WAV...');
          setMessage('Converting to WAV...');
          finalBlob = await convertToWav(audioBlob);
        }
        await sendAudio(finalBlob);
        stream.getTracks().forEach(track => track.stop());
        
        if (isConversationActive.current) {
          console.log('Starting new recording');
          startRecording();
        } else {
          console.log('Conversation stopped');
          setIsRecording(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      
      timeoutRef.current = setTimeout(() => {
        if (isConversationActive.current && mediaRecorderRef.current?.state === 'recording') {
          console.log('Stopping recording after 7 seconds');
          mediaRecorderRef.current.stop();
        }
      }, 7000);
    } catch (error) {
      console.error('Error starting recording:', error);
      setMessage(`Error: ${error.message}`);
      setIsRecording(false);
    }
  };

  const stopConversation = () => {
    isConversationActive.current = false;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setMessage('Conversation stopped.');
    setTranscription('');
    setEmotion('');
    setResponseText('');
    threadId.current = `thread_${crypto.randomUUID()}`;
  };
const sendAudio = async (audioBlob: Blob, mimeType: string) => {
  // Check if user exists; exit if not
  if (!user) return;

  // Extract file extension from MIME type (e.g., 'webm' from 'audio/webm')
  const extension = mimeType.split('/')[1];
  const filename = `audio.${extension}`;

  // Prepare FormData for the POST request
  const formData = new FormData();
  formData.append('audio', audioBlob, filename); // Audio file with filename
  formData.append('user_name', user.firstName || 'User'); // User name fallback
  formData.append('thread_id', threadId.current); // Thread ID

  try {
    // Determine API URL with fallback to local development
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';
    const response = await fetch(`${apiUrl}/process-audio`, {
      method: 'POST',
      body: formData,
    });

    // Check if the response is successful
    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }

    // Log success and update UI
    console.log('API Success');
    setMessage('✅ Audio sent successfully');

    // Extract and set metadata from response headers
    setTranscription(response.headers.get('X-Transcription') || 'N/A');
    setEmotion(response.headers.get('X-Emotion') || 'N/A');
    setResponseText(response.headers.get('X-Response') || 'N/A');

    // Handle audio response if present
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('audio/wav')) {
      const audioBlob = await response.blob();
      if (audioRef.current) {
        audioRef.current.src = URL.createObjectURL(audioBlob);
        audioRef.current.play();
        setMessage('🔊 Playing response...');
        audioRef.current.onended = () => setMessage('Ready.');
      }
    }
  } catch (error) {
    // Handle and report errors
    console.error('Fetch error:', error);
    setMessage(`❌ Fetch Error: ${error.message}. Is the backend running?`);
  }
};

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-semibold">Voice Interaction</h2>
      <div className="bg-gray-800 p-6 rounded-lg shadow-md">
        <h3 className="text-xl font-bold mb-4">Talk to Your Robot</h3>
        <p className="mb-4">Records and sends audio in 7-second chunks.</p>
        <div className="flex space-x-4 mb-4">
          {!isRecording ? (
            <button
              onClick={() => {
                isConversationActive.current = true;
                startRecording();
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
              disabled={!isLoaded || !user}
            >
              Start Conversation
            </button>
          ) : (
            <button
              onClick={stopConversation}
              className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded"
            >
              Stop Conversation
            </button>
          )}
        </div>
        {message && (
          <p className={`mb-4 ${message.includes('Error') ? 'text-red-400' : 'text-green-400'}`}>
            {message}
          </p>
        )}
        {(transcription || emotion || responseText) && (
          <div className="space-y-2">
            {transcription && <p><strong>Transcription:</strong> {transcription}</p>}
            {emotion && <p><strong>Emotion:</strong> {emotion}</p>}
            {responseText && <p><strong>Response:</strong> {responseText}</p>}
          </div>
        )}
        <audio ref={audioRef} controls className="mt-4 w-full hidden" />
      </div>
    </div>
  );
}

export default function VoiceInteractionPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <VoiceInteractionContent />
    </Suspense>
  );
}