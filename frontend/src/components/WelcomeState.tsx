import React from 'react';
import { Orbit, Waves, Wind, GitCompare, Shield } from 'lucide-react';

interface WelcomeStateProps {
  onSelectPrompt: (prompt: string, defaultLocation?: { lat: number; lon: number }) => void;
}

const STARTER_PROMPTS = [
  {
    icon: Waves,
    title: 'Live Habitat Potential',
    text: 'What is the habitat suitability at 19.5, 70.5 today?',
    prompt: 'What is the habitat suitability at 19.5, 70.5 today?',
    location: { lat: 19.5, lon: 70.5 },
  },
  {
    icon: Wind,
    title: 'Sea State & Safety Risk',
    text: 'Is it safe to fish near 19.5, 70.5?',
    prompt: 'Is it safe to fish near 19.5, 70.5?',
    location: { lat: 19.5, lon: 70.5 },
  },
  {
    icon: GitCompare,
    title: 'Multi-Temporal Comparison',
    text: 'Compare today with October 15, 2025 at 19.5, 70.5',
    prompt: "Compare today's habitat suitability with October 15, 2025",
    location: { lat: 19.5, lon: 70.5 },
  },
  {
    icon: Shield,
    title: 'Indian EEZ Geofencing',
    text: 'Is coordinate 19.5, 70.5 inside the Indian EEZ boundary?',
    prompt: 'Is this location inside the Indian EEZ and safe to fish?',
    location: { lat: 19.5, lon: 70.5 },
  },
];

export const WelcomeState: React.FC<WelcomeStateProps> = ({ onSelectPrompt }) => {
  return (
    <div className="welcome-container animate-fade-in">
      <div className="welcome-logo-badge">
        <Orbit size={14} />
        <span>ORCA DECISION SYSTEM</span>
      </div>

      <h1 className="welcome-heading">
        Marine Intelligence, when decisions matter.
      </h1>

      <p className="welcome-subheading">
        Real-time Copernicus Marine observations, spatial habitat modeling, sea state risk assessment,
        and Indian EEZ geofencing along the Indian West Coast.
      </p>

      <div className="starters-grid">
        {STARTER_PROMPTS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              className="starter-card"
              onClick={() => onSelectPrompt(item.prompt, item.location)}
            >
              <div className="starter-card-title">
                <Icon size={16} />
                <span>{item.title}</span>
              </div>
              <div className="starter-card-text">{item.text}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
