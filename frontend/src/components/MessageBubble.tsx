import React, { useEffect, useRef } from 'react';
import { User, Orbit } from 'lucide-react';
import { synthesizeAndPlayAudio } from '../services/chatApi';
import { ChatMessage, CoordinatorResponse, ClarificationRequired } from '../types/api';
import { HabitatResultCard } from './cards/HabitatResultCard';
import { WeatherResultCard } from './cards/WeatherResultCard';
import { GeofenceResultCard } from './cards/GeofenceResultCard';
import { ComparisonResultCard } from './cards/ComparisonResultCard';
import { AlertStateCard } from './cards/AlertStateCard';
import { ResearchIntelligenceCard } from './cards/ResearchIntelligenceCard';
import { FishingDecisionCard } from './cards/FishingDecisionCard';
import CycloneIntelligenceCard from './CycloneIntelligenceCard';

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender === 'user';
  const hasPlayedAudio = useRef(false);

  useEffect(() => {
    if (!isUser && !hasPlayedAudio.current && message.data && message.wasVoice) {
      hasPlayedAudio.current = true;
      const lang = window.sessionStorage.getItem('stt_lang') || 'en';
      
      const coord = message.data as CoordinatorResponse;
      
      let textToSpeak = '';
      if (coord.conversation_response) {
          textToSpeak = coord.conversation_response;
      } else if (coord.fishing_decision?.decision) {
            textToSpeak = coord.fishing_decision.narrative || 'Fishing decision is ready.';
        } else if (coord.weather?.safety_narrative) {
            textToSpeak = `${coord.weather.safety_narrative} ${coord.weather.safety_advice || ''}`;
        } else if (coord.cyclone?.narrative) {
            textToSpeak = coord.cyclone.narrative;
        } else if (coord.habitat?.scientific_explanation) {
            textToSpeak = coord.habitat.scientific_explanation;
        } else if (coord.geofencing?.geofence_narrative) {
            textToSpeak = coord.geofencing.geofence_narrative;
        }

        if (textToSpeak) {
            synthesizeAndPlayAudio(textToSpeak, lang);
        }
    }
  }, [message, isUser]);

  /* ── User message ── */
  if (isUser) {
    return (
      <div className="message-row user animate-fade-in">
        <div className="message-bubble user-bubble">{message.text}</div>
        <div className="message-avatar user-avatar" aria-hidden="true">
          <User size={14} />
        </div>
      </div>
    );
  }

  /* ── Error ── */
  if (message.isError) {
    return (
      <div className="message-row assistant animate-fade-in">
        <div className="message-avatar orca-avatar" aria-hidden="true">
          <Orbit size={13} />
        </div>
        <div className="message-bubble assistant-bubble">
          <AlertStateCard
            type="error"
            title="Communication Error"
            message={message.errorMessage || 'Unable to reach the ORCA decision engine.'}
          />
        </div>
      </div>
    );
  }

  /* ── Clarification ── */
  const data = message.data;
  if (data && 'needs_clarification' in data && data.needs_clarification) {
    const clar = data as ClarificationRequired;
    return (
      <div className="message-row assistant animate-fade-in">
        <div className="message-avatar orca-avatar" aria-hidden="true">
          <Orbit size={13} />
        </div>
        <div className="message-bubble assistant-bubble">
          <AlertStateCard
            type="clarification"
            title="Location or Date Required"
            message={clar.message}
            missingFields={clar.missing}
          />
        </div>
      </div>
    );
  }

  /* ── Standard coordinator response ── */
  const coord = data as CoordinatorResponse | null | undefined;
  const habitat       = coord?.habitat;
  const weather       = coord?.weather;
  const geofencing    = coord?.geofencing;
  const fishingDecision = coord?.fishing_decision;
  const comparison    = coord?.comparison || habitat?.comparison;

  const isFutureUnsupported = habitat?.temporal_mode === 'UNSUPPORTED_FUTURE';
  const isInsufficientData  = habitat && !habitat.success && habitat.error?.includes('unavailable');

  return (
    <div className="message-row assistant animate-fade-in">
      <div className="message-avatar orca-avatar" aria-hidden="true">
        <Orbit size={13} />
      </div>

      <div className="message-bubble assistant-bubble">
        {/* Domain Indicator Badge */}
        {coord?.intelligence_domain && coord.intelligence_domain !== 'UNKNOWN' && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '2px 8px',
            marginBottom: 8,
            borderRadius: 4,
            fontSize: '10.5px',
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            background: 'rgba(194, 198, 214, 0.08)',
            color: 'var(--accent)',
            border: '1px solid rgba(194, 198, 214, 0.15)',
          }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent)' }} />
            {coord.intelligence_domain.replace(/_/g, ' ')}
          </div>
        )}

        {/* Conversational narrative */}
        {coord?.conversation_response && (
          <div className="conversation-narrative">
            {coord.conversation_response}
          </div>
        )}

        {/* Plain text (rare) */}
        {message.text && !coord?.conversation_response && (
          <div className="conversation-narrative">{message.text}</div>
        )}

        {/* Research Intelligence Card */}
        {coord?.research?.success && (
          <ResearchIntelligenceCard research={coord.research} />
        )}

        {/* Maritime Safety Card (Coast Guard / Navigators) */}
        {!fishingDecision && coord?.safety_assessment && (
          <div style={{
            marginTop: 10,
            padding: '12px 14px',
            borderRadius: 8,
            background: 'rgba(18, 24, 38, 0.75)',
            border: '1px solid var(--border-default)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Maritime Safety Assessment
              </span>
              <span style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 6px',
                borderRadius: 4,
                background: coord.safety_assessment.risk_level === 'Low Risk' ? 'rgba(74, 222, 128, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: coord.safety_assessment.risk_level === 'Low Risk' ? 'var(--success)' : 'var(--danger)',
              }}>
                {coord.safety_assessment.risk_level}
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginTop: 8 }}>
              <div style={{ padding: '6px 8px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 6 }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Wind</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {coord.safety_assessment.wind_speed_kn != null ? `${coord.safety_assessment.wind_speed_kn.toFixed(1)} kn` : '—'}
                </div>
              </div>
              <div style={{ padding: '6px 8px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 6 }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Waves</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {coord.safety_assessment.wave_height_m != null ? `${coord.safety_assessment.wave_height_m.toFixed(1)} m` : '—'}
                </div>
              </div>
              <div style={{ padding: '6px 8px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 6 }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>EEZ Compliance</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {coord.safety_assessment.eez_compliance || 'Verified'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Multi-Domain Sector Overview Card (Researchers / Environmental Analysts) */}
        {!fishingDecision && !coord?.safety_assessment && coord?.sector_overview && (
          <div style={{
            marginTop: 10,
            padding: '12px 14px',
            borderRadius: 8,
            background: 'rgba(18, 24, 38, 0.75)',
            border: '1px solid var(--border-default)',
          }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8 }}>
              Coastal Sector Intelligence Overview
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {coord.sector_overview.marine && (
                <div style={{ padding: '6px 8px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 6 }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Marine Environment</div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {coord.sector_overview.marine.sst_c != null ? `${coord.sector_overview.marine.sst_c.toFixed(1)}°C SST` : '—'}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    {coord.sector_overview.marine.chlorophyll_mg_m3 != null ? `${coord.sector_overview.marine.chlorophyll_mg_m3.toFixed(2)} mg/m³` : ''}
                  </div>
                </div>
              )}
              {coord.sector_overview.sea_state && (
                <div style={{ padding: '6px 8px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 6 }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Sea State</div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {coord.sector_overview.sea_state.risk_level || 'Operational'}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    {coord.sector_overview.sea_state.wind_speed_kn != null ? `${coord.sector_overview.sea_state.wind_speed_kn.toFixed(0)} kn wind` : ''}
                  </div>
                </div>
              )}
              {coord.sector_overview.geospatial && (
                <div style={{ padding: '6px 8px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 6 }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Geospatial</div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {coord.sector_overview.geospatial.eez_status || 'Indian EEZ'}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    {coord.sector_overview.geospatial.distance_to_boundary_km != null ? `${coord.sector_overview.geospatial.distance_to_boundary_km.toFixed(0)} km to line` : 'Sovereign'}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Unified Fishing Decision — primary card */}
        {fishingDecision?.success && fishingDecision.decision && (
          <FishingDecisionCard data={fishingDecision} />
        )}

        {/* Cyclone intelligence */}
        {coord?.cyclone?.success && (
          <div style={{ marginTop: 12 }}>
            <CycloneIntelligenceCard
              latitude={coord.cyclone.location?.latitude || 0}
              longitude={coord.cyclone.location?.longitude || 0}
              data={coord.cyclone}
            />
          </div>
        )}

        {/* Future date */}
        {isFutureUnsupported && (
          <AlertStateCard
            type="unsupported_future"
            title="Future Marine Data Unavailable"
            message={
              habitat?.error ||
              'Blue Orbit does not have forecast marine data beyond available oceanographic observations.'
            }
          />
        )}

        {/* Insufficient data */}
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

        {/* Comparison */}
        {comparison && (
          <ComparisonResultCard
            comparison={comparison}
            scientificExplanation={habitat?.scientific_explanation}
            fishermanAdvice={habitat?.fisherman_advice}
          />
        )}

        {/* Habitat — if no comparison */}
        {!comparison && habitat?.success && !isFutureUnsupported && (
          <HabitatResultCard data={habitat} />
        )}

        {/* Weather */}
        {weather?.success && <WeatherResultCard data={weather} />}

        {/* Geofencing */}
        {geofencing?.success && <GeofenceResultCard data={geofencing} />}

        {/* System errors (shown only when no conversational response) */}
        {coord?.errors && coord.errors.length > 0 && !coord?.conversation_response && (
          <div style={{ marginTop: 10 }}>
            {coord.errors.map((err, i) => {
              const isDomainScope = err.includes('outside supported domain') || err.includes('ambiguous');
              return (
                <AlertStateCard
                  key={i}
                  type={isDomainScope ? 'clarification' : 'error'}
                  title={isDomainScope ? 'Domain Guidance' : 'Service Alert'}
                  message={
                    isDomainScope
                      ? 'ORCA covers fishing habitat, sea state safety and Indian EEZ compliance along the Indian West Coast. Please ask about these or provide a maritime location.'
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
