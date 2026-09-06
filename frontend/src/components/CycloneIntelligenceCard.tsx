import React, { useState, useEffect } from 'react';
import { CycloneAgentResponse } from '../types/api';
import { fetchCycloneIntelligence } from '../services/spatialApi';

interface CycloneIntelligenceCardProps {
  latitude: number;
  longitude: number;
  date?: string | null;
  autoFetch?: boolean;
  data?: CycloneAgentResponse | null;
}

const CycloneIntelligenceCard: React.FC<CycloneIntelligenceCardProps> = ({
  latitude,
  longitude,
  date,
  autoFetch = false,
  data: propData
}) => {
  const [data, setData] = useState<CycloneAgentResponse | null>(propData || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (propData) {
      setData(propData);
    }
  }, [propData]);

  useEffect(() => {
    if (autoFetch && !propData) {
      const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
          const res = await fetchCycloneIntelligence(latitude, longitude, date);
          setData(res);
        } catch (err: any) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      };
      loadData();
    }
  }, [latitude, longitude, date, autoFetch, propData]);

  if (loading) {
    return (
      <div className="bg-ocean-900/40 border border-ocean-700/50 rounded-xl p-5 animate-pulse flex flex-col gap-3">
        <div className="h-6 bg-ocean-800/60 rounded w-1/3"></div>
        <div className="h-4 bg-ocean-800/60 rounded w-full mt-2"></div>
        <div className="h-4 bg-ocean-800/60 rounded w-5/6"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-5 text-red-200">
        <h4 className="font-semibold mb-1">Cyclone Intelligence Error</h4>
        <p className="text-sm opacity-80">{error}</p>
      </div>
    );
  }

  if (!data || !data.severe_weather) {
    return null;
  }

  const { severe_weather, cyclone_alert, narrative, advice, distance_to_center_km } = data;
  const isSevere = severe_weather.risk_level === 'SEVERE' || severe_weather.risk_level === 'EXTREME';
  const isElevated = severe_weather.risk_level === 'ELEVATED';
  const noData = severe_weather.affected_status === 'NO_VERIFIED_DATA';

  const getBorderColor = () => {
    if (isSevere) return 'border-red-500/50';
    if (isElevated) return 'border-amber-500/50';
    if (noData) return 'border-ocean-700/50';
    return 'border-emerald-500/30';
  };

  const getBgColor = () => {
    if (isSevere) return 'bg-red-900/10';
    if (isElevated) return 'bg-amber-900/10';
    if (noData) return 'bg-ocean-900/30';
    return 'bg-emerald-900/10';
  };

  const getHeaderColor = () => {
    if (isSevere) return 'text-red-400';
    if (isElevated) return 'text-amber-400';
    if (noData) return 'text-slate-400';
    return 'text-emerald-400';
  };

  return (
    <div
      className="result-card animate-fade-in"
      style={{
        borderLeft: isSevere
          ? '3px solid var(--danger)'
          : isElevated
          ? '3px solid var(--warning)'
          : '3px solid var(--border-default)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <svg className={`w-4 h-4 ${getHeaderColor()}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
          </svg>
          <span style={{ fontSize: '11px', fontWeight: 500, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
            {cyclone_alert?.status === 'UNAVAILABLE' 
              ? 'Severe Weather Intelligence' 
              : 'Cyclone Intelligence'}
          </span>
        </div>
        <div className="flex gap-2">
          <span style={{
            padding: '2px 8px',
            borderRadius: 'var(--r-sm)',
            fontSize: '11px',
            fontWeight: 500,
            letterSpacing: '0.03em',
            background: 'var(--bg-surface)',
            color: isSevere ? 'var(--danger)' : isElevated ? 'var(--warning)' : 'var(--text-muted)',
            border: '1px solid var(--border-default)',
          }}>
            {severe_weather.risk_level}
          </span>
        </div>
      </div>

      {cyclone_alert && cyclone_alert.status !== 'UNAVAILABLE' ? (
        <div className="metrics-row-divided" style={{ marginBottom: '14px' }}>
          <div className="metric-col">
            <span className="metric-label">System</span>
            <span className="metric-val">{cyclone_alert.name || 'Unnamed System'}</span>
          </div>
          {distance_to_center_km !== null && distance_to_center_km !== undefined && (
            <div className="metric-col">
              <span className="metric-label">Distance</span>
              <span className="metric-val">{distance_to_center_km.toFixed(0)} km</span>
            </div>
          )}
          {cyclone_alert.maximum_wind_knots !== null && cyclone_alert.maximum_wind_knots !== undefined && (
            <div className="metric-col">
              <span className="metric-label">Max Wind</span>
              <span className="metric-val">{cyclone_alert.maximum_wind_knots} kt</span>
            </div>
          )}
          {cyclone_alert.affected_radius_km !== null && cyclone_alert.affected_radius_km !== undefined && (
            <div className="metric-col">
              <span className="metric-label">Radius</span>
              <span className="metric-val">{cyclone_alert.affected_radius_km} km</span>
            </div>
          )}
        </div>
      ) : (
        <div style={{ padding: '10px 0', borderBottom: '1px solid var(--neutral-border)', marginBottom: '12px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            No Verified Cyclone Alerts Available
          </span>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {narrative && (
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
            {narrative}
          </p>
        )}
        {advice && (
          <div style={{
            background: 'var(--surface-elevated)',
            borderRadius: 'var(--r-sm)',
            padding: '10px 12px',
            fontSize: '12.5px',
            color: 'var(--text-secondary)',
            border: '1px solid var(--neutral-border)',
          }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: '3px' }}>Guidance</span>
            {advice}
          </div>
        )}
      </div>

      <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: 'var(--text-muted)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
        <span>Source: {cyclone_alert?.source || 'Provider Abstraction'}</span>
        <span>Mode: {data.temporal_mode}</span>
      </div>
    </div>
  );
};

export default CycloneIntelligenceCard;
