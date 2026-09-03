import React, { useState, useEffect, useRef } from 'react';
import { TopBar } from './components/TopBar';
import { Sidebar } from './components/Sidebar';
import { MessageComposer } from './components/MessageComposer';
import { MessageBubble } from './components/MessageBubble';
import { WelcomeState } from './components/WelcomeState';
import { LocationControl } from './components/LocationControl';
import { DateControl } from './components/DateControl';
import { checkBackendHealth, sendChatMessage, ApiError } from './services/chatApi';
import { ChatMessage, SessionRecord, CoordinatorResponse, ClarificationRequired, LocationContext } from './types/api';
import { Loader2 } from 'lucide-react';
import { MarineSpatialView } from './components/spatial/MarineSpatialView';

const createSessionId = () => `orca-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;

export const App: React.FC = () => {
  // Navigation View State: 'map' (Spatial Intelligence Centerpiece) | 'chat' (Decision Assistant)
  const [activeView, setActiveView] = useState<'map' | 'chat'>('map');

  // Session & Conversations
  const [currentSessionId, setCurrentSessionId] = useState<string>(createSessionId);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Context: Location & Date (default center to Goa Coastal Zone)
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>({ lat: 15.41, lon: 73.80 });
  const [locationContext, setLocationContext] = useState<LocationContext | null>({
    latitude: 15.41,
    longitude: 73.80,
    display_name: 'Goa Coastal Zone',
    source: 'map',
    timestamp: new Date().toISOString(),
  });
  const [dateStr, setDateStr] = useState<string | null>('today');

  // Modals & UI States
  const [isLocationOpen, setIsLocationOpen] = useState<boolean>(false);
  const [isDateOpen, setIsDateOpen] = useState<boolean>(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);

  // Input & Network State
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Initial backend health check & periodic poll
  const verifyHealth = async () => {
    setIsCheckingHealth(true);
    const res = await checkBackendHealth();
    setIsBackendHealthy(res.healthy);
    setIsCheckingHealth(false);
  };

  useEffect(() => {
    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Sync current conversation into sessions array
  useEffect(() => {
    if (messages.length === 0) return;

    setSessions((prev) => {
      const firstUserMsg = messages.find((m) => m.sender === 'user');
      const title = firstUserMsg?.text?.slice(0, 32) || 'Marine Analysis';

      const existingIndex = prev.findIndex((s) => s.id === currentSessionId);
      const record: SessionRecord = {
        id: currentSessionId,
        title: existingIndex >= 0 ? prev[existingIndex].title : title,
        createdAt: existingIndex >= 0 ? prev[existingIndex].createdAt : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        messages,
        location,
        locationContext,
        dateStr,
      };

      if (existingIndex >= 0) {
        const updated = [...prev];
        updated[existingIndex] = record;
        return updated;
      }
      return [record, ...prev];
    });
  }, [messages, currentSessionId, location, locationContext, dateStr]);

  // Handle New Chat
  const handleNewChat = () => {
    const newId = createSessionId();
    setCurrentSessionId(newId);
    setMessages([]);
    setInput('');
    setIsLoading(false);
  };

  // Handle Switch Session
  const handleSelectSession = (id: string) => {
    const target = sessions.find((s) => s.id === id);
    if (target) {
      setCurrentSessionId(target.id);
      setMessages(target.messages);
      if (target.location) setLocation(target.location);
      if (target.locationContext) setLocationContext(target.locationContext);
      else if (target.location) setLocationContext(null);
      if (target.dateStr) setDateStr(target.dateStr);
    }
  };

  // Execute message submission
  const handleSendMessage = async (textToSend?: string, overrideLocation?: { lat: number; lon: number }) => {
    const messageText = (textToSend !== undefined ? textToSend : input).trim();
    if (!messageText || isLoading) return;

    const activeLoc = overrideLocation !== undefined ? overrideLocation : location;

    // Add user message to UI
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      sender: 'user',
      timestamp: new Date().toISOString(),
      text: messageText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendChatMessage({
        session_id: currentSessionId,
        message: messageText,
        latitude: activeLoc?.lat,
        longitude: activeLoc?.lon,
        date_str: dateStr === 'today' ? undefined : dateStr || undefined,
        location_context: locationContext || undefined,
      });

      // Update location state from coordinator response if backend resolved coordinates
      if ('request' in response && response.request) {
        const reqLat = response.request.latitude;
        const reqLon = response.request.longitude;
        if (reqLat !== null && reqLat !== undefined && reqLon !== null && reqLon !== undefined) {
          setLocation({ lat: reqLat, lon: reqLon });
          if (!locationContext) {
            setLocationContext({
              latitude: reqLat,
              longitude: reqLon,
              display_name: `${reqLat.toFixed(2)}° N · ${reqLon.toFixed(2)}° E`,
              source: 'manual',
              timestamp: new Date().toISOString(),
            });
          }
        }
      }

      // Add assistant response
      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}-orca`,
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        data: response,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-${Date.now()}-error`,
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        isError: true,
        errorMessage: err.message || 'Unable to communicate with the Blue Orbit decision engine.',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Starter Click
  const handleSelectStarter = (prompt: string, defaultLoc?: { lat: number; lon: number }) => {
    if (defaultLoc && !location) {
      setLocation(defaultLoc);
    }
    handleSendMessage(prompt, defaultLoc || location || undefined);
  };

  // Switch to Chat from Spatial Map
  const handleSwitchToChatWithLocation = (locName: string, lat: number, lon: number) => {
    setLocation({ lat, lon });
    setLocationContext({
      latitude: lat,
      longitude: lon,
      display_name: locName,
      source: 'map',
      timestamp: new Date().toISOString(),
    });
    setActiveView('chat');
    handleSendMessage(`Can I go fishing near ${locName} today?`, { lat, lon });
  };

  return (
    <div className="app-shell">
      {/* Sidebar for session management */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        activeLocation={location}
      />

      <div className="main-layout">
        {/* Top Navigation */}
        <TopBar
          isBackendHealthy={isBackendHealthy}
          onRefreshHealth={verifyHealth}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          isCheckingHealth={isCheckingHealth}
          activeView={activeView}
          onChangeView={setActiveView}
        />

        {/* View 1: Spatial Marine Intelligence (Centerpiece Map View) */}
        {activeView === 'map' && (
          <MarineSpatialView
            currentLocationContext={locationContext}
            onUpdateLocationContext={(loc) => {
              setLocationContext(loc);
              setLocation({ lat: loc.latitude, lon: loc.longitude });
            }}
            observationDate={dateStr}
            onOpenDateModal={() => setIsDateOpen(true)}
            onSwitchToChatWithLocation={handleSwitchToChatWithLocation}
          />
        )}

        {/* View 2: Conversational Decision Assistant */}
        {activeView === 'chat' && (
          <main className="chat-workspace">
            <div className="messages-scroll-area">
              {messages.length === 0 ? (
                <WelcomeState onSelectPrompt={handleSelectStarter} />
              ) : (
                <div className="messages-wrapper">
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} />
                  ))}

                  {isLoading && (
                    <div className="message-row assistant animate-fade-in">
                      <div className="message-avatar orca-avatar">
                        <Loader2 size={16} className="animate-spin" />
                      </div>
                      <div className="message-bubble assistant-bubble">
                        <div className="loading-indicator">
                          <Loader2 size={16} className="animate-spin" />
                          <span>Analyzing marine conditions & spatial intelligence...</span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Bottom Docked Message Composer */}
            <MessageComposer
              input={input}
              onChangeInput={setInput}
              onSend={() => handleSendMessage()}
              isLoading={isLoading}
              location={location}
              locationContext={locationContext}
              dateStr={dateStr}
              onOpenLocation={() => setIsLocationOpen(true)}
              onOpenDate={() => setIsDateOpen(true)}
            />
          </main>
        )}
      </div>

      {/* Location Selector Popover */}
      {isLocationOpen && (
        <LocationControl
          currentLocationContext={locationContext}
          onSaveLocation={(locCtx) => {
            setLocationContext(locCtx);
            if (locCtx) {
              setLocation({ lat: locCtx.latitude, lon: locCtx.longitude });
            } else {
              setLocation(null);
            }
          }}
          onClose={() => setIsLocationOpen(false)}
        />
      )}

      {/* Date Context Popover */}
      {isDateOpen && (
        <DateControl
          currentDateStr={dateStr}
          onSaveDate={(dt) => setDateStr(dt)}
          onClose={() => setIsDateOpen(false)}
        />
      )}
    </div>
  );
};

export default App;
