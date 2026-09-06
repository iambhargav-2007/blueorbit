import React from 'react';
import { Orbit, Waves, Wind, GitCompare, Shield, ArrowRight } from 'lucide-react';

interface WelcomeStateProps {
  onSelectPrompt: (prompt: string, defaultLocation?: { lat: number; lon: number }) => void;
}

const STARTER_PROMPTS = [
  {
    icon: Waves,
    title: 'Habitat Suitability',
    text: 'Check environmental conditions and fishing potential',
    prompt: 'What is the habitat suitability at 19.5, 70.5 today?',
    location: { lat: 19.5, lon: 70.5 },
  },
  {
    icon: Wind,
    title: 'Sea State Safety',
    text: 'Assess wind, wave and weather risk',
    prompt: 'Is it safe to fish near 19.5, 70.5?',
    location: { lat: 19.5, lon: 70.5 },
  },
  {
    icon: GitCompare,
    title: 'Temporal Comparison',
    text: 'Compare current vs historical marine conditions',
    prompt: "Compare today's habitat suitability with October 15, 2025",
    location: { lat: 19.5, lon: 70.5 },
  },
  {
    icon: Shield,
    title: 'EEZ Compliance',
    text: 'Verify Indian EEZ boundary and legal status',
    prompt: 'Is this location inside the Indian EEZ and safe to fish?',
    location: { lat: 19.5, lon: 70.5 },
  },
];

export const WelcomeState: React.FC<WelcomeStateProps> = ({ onSelectPrompt }) => {
  return (
    <div className="welcome-container animate-fade-in">
      <div className="welcome-logo-badge">
        <Orbit size={13} className="welcome-badge-icon" />
        <span>ORCA Intelligence System</span>
      </div>

      <h1 className="welcome-heading">
        Marine intelligence,<br />when decisions matter.
      </h1>

      <p className="welcome-subheading">
        Real-time Copernicus marine observations, habitat modelling,
        sea state risk and EEZ compliance along the Indian West Coast.
      </p>

      {/* Clean horizontal capability strip — no boxy borders or dashboard tiles */}
      <div className="welcome-capabilities-row">
        {STARTER_PROMPTS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              id={`starter-${idx}`}
              className="capability-item"
              onClick={() => onSelectPrompt(item.prompt, item.location)}
              aria-label={item.title}
              title={item.text}
            >
              <Icon size={12} className="capability-icon" />
              <span className="capability-title">{item.title}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
