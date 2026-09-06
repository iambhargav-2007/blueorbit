import React, { useRef, useEffect, useState } from 'react';
import { ArrowUp, Compass, Calendar, Loader2, Mic, Square } from 'lucide-react';
import { LocationContext } from '../types/api';

interface MessageComposerProps {
  input: string;
  onChangeInput: (val: string) => void;
  onSend: () => void;
  isLoading: boolean;
  location: { lat: number; lon: number } | null;
  locationContext?: LocationContext | null;
  dateStr: string | null;
  onOpenLocation: () => void;
  onOpenDate: () => void;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  input,
  onChangeInput,
  onSend,
  isLoading,
  location,
  locationContext,
  dateStr,
  onOpenLocation,
  onOpenDate,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading && !isTranscribing) onSend();
    }
  };

  const handleRecordToggle = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          setIsTranscribing(true);
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');
          const lang = window.sessionStorage.getItem('stt_lang');
          if (lang) {
            formData.append('language', lang);
          }
          
          try {
            // Assume backend is on port 8000, can use env if available. Defaulting to relative or localhost.
            const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const res = await fetch(`${backendUrl}/api/v1/voice/transcribe`, {
              method: 'POST',
              body: formData,
            });
            if (res.ok) {
              const data = await res.json();
              if (data.transcript) {
                window.sessionStorage.setItem('last_input_was_voice', 'true');
                if (data.language && (!lang || lang === 'auto')) {
                    window.sessionStorage.setItem('stt_lang', data.language);
                }
                onChangeInput(input ? `${input} ${data.transcript}` : data.transcript);
              }
            } else {
              console.error('Transcription failed with status:', res.status);
            }
          } catch (err) {
            console.error('Transcription request failed', err);
          } finally {
            setIsTranscribing(false);
            stream.getTracks().forEach(track => track.stop());
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        console.error('Microphone access denied', err);
        alert('Please allow microphone access to use voice typing.');
      }
    }
  };

  const formatDate = (date: string | null) => {
    if (!date || date === 'today') return 'Today (LIVE)';
    return date;
  };

  const formatLocation = () => {
    if (locationContext) {
      if (locationContext.source === 'gps') {
        const acc = locationContext.accuracy_m ? ` (~${Math.round(locationContext.accuracy_m)}m)` : '';
        return `GPS${acc}`;
      }
      return locationContext.display_name;
    }
    if (location) return `${location.lat.toFixed(2)}°N · ${location.lon.toFixed(2)}°E`;
    return 'Set location';
  };

  const hasLocation = !!(locationContext || location);

  return (
    <div className="composer-dock">
      <div className="composer-box" role="form" aria-label="Ask ORCA">
        {/* Context row */}
        <div className="composer-context-bar">
          <div className="context-pill-group">
            <button
              id="composer-location-pill"
              type="button"
              className={`context-pill ${hasLocation ? 'active' : ''}`}
              onClick={onOpenLocation}
              title="Set sector location"
              aria-label="Set location"
            >
              <Compass size={11} />
              <span>{formatLocation()}</span>
            </button>

            <button
              id="composer-date-pill"
              type="button"
              className={`context-pill ${dateStr && dateStr !== 'today' ? 'active' : ''}`}
              onClick={onOpenDate}
              title="Set temporal context"
              aria-label="Set date"
            >
              <Calendar size={11} />
              <span>{formatDate(dateStr)}</span>
            </button>
          </div>

          <span style={{ fontSize: 10.5, color: 'var(--text-dim)' }}>⇧ Enter for newline</span>
        </div>

        {/* Input row */}
        <div className="composer-input-area">
          <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
            <textarea
              ref={textareaRef}
              id="composer-textarea"
              rows={1}
              className="composer-textarea"
              placeholder={isRecording ? "Listening... (Click the red square to stop & transcribe)" : isTranscribing ? "Transcribing..." : "Ask ORCA about marine conditions, sea state, EEZ boundaries…"}
              value={input}
              onChange={(e) => onChangeInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading || isRecording || isTranscribing}
              aria-label="Ask ORCA"
            />
          </div>

          <div className="composer-actions">
            <select
              id="stt-lang-select"
              defaultValue=""
              style={{
                fontSize: 10,
                padding: '2px 4px',
                background: 'transparent',
                color: 'var(--text-muted)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--r-sm)',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="">Auto</option>
              <option value="te">Telugu</option>
              <option value="hi">Hindi</option>
              <option value="en">English</option>
            </select>

            <button
              type="button"
              className={`btn-mic ${isRecording ? 'recording' : ''}`}
              onClick={() => {
                // If starting recording, grab the language value
                if (!isRecording) {
                  const sel = document.getElementById('stt-lang-select') as HTMLSelectElement;
                  window.sessionStorage.setItem('stt_lang', sel?.value || '');
                }
                handleRecordToggle();
              }}
              disabled={isLoading || isTranscribing}
              aria-label={isRecording ? "Stop recording" : "Start recording"}
              title={isRecording ? "Stop recording" : "Start recording"}
            >
              {isTranscribing ? (
                <Loader2 size={16} className="animate-spin text-accent" />
              ) : isRecording ? (
                <Square size={14} className="icon-pulse-red" fill="currentColor" />
              ) : (
                <Mic size={16} />
              )}
            </button>

            <button
              id="btn-send"
              type="button"
              className="btn-send"
              disabled={!input.trim() || isLoading || isTranscribing}
              onClick={onSend}
              aria-label="Send query"
            >
              {isLoading
                ? <Loader2 size={14} className="animate-spin" />
                : <ArrowUp size={16} />
              }
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
