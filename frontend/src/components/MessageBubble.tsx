import React from 'react';
import { User, Orbit, Loader2 } from 'lucide-react';
import { ChatMessage, CoordinatorResponse, ClarificationRequired } from '../types/api';
import { HabitatResultCard } from './cards/HabitatResultCard';
import { WeatherResultCard } from './cards/WeatherResultCard';
import { GeofenceResultCard } from './cards/GeofenceResultCard';
import { ComparisonResultCard } from './cards/ComparisonResultCard';
import { AlertStateCard } from './cards/AlertStateCard';
import { FishingDecisionCard } from './cards/FishingDecisionCard';

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender === 'user';

  if (isUser) {
    return (
      <div className="message-row user animate-fade-in">
        <div className="message-bubble user-bubble">
          {message.text}
        </div>
        <div className="message-avatar user-avatar">
          <User size={16} />
        </div>
      </div>
    );
  }

  // Assistant Message
  const data = message.data;

  // Handle Error state
  if (message.isError) {
    return (
      <div className="message-row assistant animate-fade-in">
        <div className="message-avatar orca-avatar">
          <Orbit size={16} />
        </div>
        <div className="message-bubble assistant-bubble">
          <AlertStateCard
            type="error"
            title="Communication Error"
            message={message.errorMessage || 'Unable to retrieve marine intelligence.'}
          />
        </div>
      </div>
    );
  }

  // Handle Clarification Required response
  if (data && 'needs_clarification' in data && data.needs_clarification) {
    const clar = data as ClarificationRequired;
    return (
      <div className="message-row assistant animate-fade-in">
        <div className="message-avatar orca-avatar">
          <Orbit size={16} />
        </div>
        <div className="message-bubble assistant-bubble">
          <AlertStateCard
            type="clarification"
            title="Location or Date Context Required"
            message={clar.message}
            missingFields={clar.missing}
          />
        </div>
      </div>
    );
  }

  // Handle Standard CoordinatorResponse
  const coord = data as CoordinatorResponse | null | undefined;
  const habitat = coord?.habitat;
  const weather = coord?.weather;
  const geofencing = coord?.geofencing;
  const fishingDecision = coord?.fishing_decision;
  const comparison = coord?.comparison || habitat?.comparison;

  // Check if habitat failed due to UNSUPPORTED_FUTURE
  const isFutureUnsupported =
    habitat &&
    habitat.temporal_mode === 'UNSUPPORTED_FUTURE';

  // Check if habitat failed due to INSUFFICIENT_DATA
  const isInsufficientData =
    habitat &&
    !habitat.success &&
    habitat.error &&
    habitat.error.includes('unavailable');

  return (
    <div className="message-row assistant animate-fade-in">
      <div className="message-avatar orca-avatar">
        <Orbit size={16} />
      </div>

      <div className="message-bubble assistant-bubble">
        {message.text && (
          <div style={{ marginBottom: coord ? '10px' : '0' }}>
            {message.text}
          </div>
        )}

        {/* Conversational Narrative */}
        {coord?.conversation_response && (
          <div className="conversation-narrative" style={{ lineHeight: 1.6, whiteSpace: 'pre-line', color: 'var(--text-main)' }}>
            {coord.conversation_response}
          </div>
        )}

        {/* Unified Fishing Decision Card (Step 20) */}
        {fishingDecision && fishingDecision.success && fishingDecision.decision && (
          <FishingDecisionCard data={fishingDecision} />
        )}

        {/* Unsupported Future Date Alert */}
        {isFutureUnsupported && (
          <AlertStateCard
            type="unsupported_future"
            title="Future Marine Data Unavailable"
            message={
              habitat?.error ||
              'Blue Orbit cannot provide habitat forecast data for future dates beyond available oceanographic observations.'
            }
          />
        )}

        {/* Insufficient Data Alert */}
        {isInsufficientData && !isFutureUnsupported && (
          <AlertStateCard
            type="insufficient_data"
            title="Insufficient Marine Observations"
            message={
              habitat?.error ||
              'Required temperature or chlorophyll data is unavailable for this date and coordinate.'
            }
          />
        )}

        {/* Comparison Result Card */}
        {comparison && (
          <ComparisonResultCard
            comparison={comparison}
            scientificExplanation={habitat?.scientific_explanation}
            fishermanAdvice={habitat?.fisherman_advice}
          />
        )}

        {/* Habitat Card (when not comparison and succeeded or has partial data) */}
        {!comparison && habitat && habitat.success && !isFutureUnsupported && (
          <HabitatResultCard data={habitat} />
        )}

        {/* Weather Card */}
        {weather && weather.success && (
          <WeatherResultCard data={weather} />
        )}

        {/* Geofencing Card */}
        {geofencing && geofencing.success && (
          <GeofenceResultCard data={geofencing} />
        )}

        {/* Errors list if any (suppressed if friendly conversational response is displayed) */}
        {coord?.errors && coord.errors.length > 0 && !coord?.conversation_response && (
          <div style={{ marginTop: '12px' }}>
            {coord.errors.map((err, i) => {
              const isDomainScope = err.includes('outside supported domain') || err.includes('ambiguous');
              return (
                <AlertStateCard
                  key={i}
                  type={isDomainScope ? 'clarification' : 'error'}
                  title={isDomainScope ? 'Blue Orbit Domain Guidance' : 'Service Alert'}
                  message={
                    isDomainScope
                      ? 'I can assist you with fishing habitat suitability, sea state weather safety, and Indian EEZ compliance along the Indian West Coast. Please ask about these capabilities or provide a maritime location.'
                      : err
                  }
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
