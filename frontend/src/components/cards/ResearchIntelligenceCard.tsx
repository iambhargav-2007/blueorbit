import React from 'react';
import { ResearchAgentResponse, ResearchMetric } from '../../types/api';
import { Database, MapPin, Calendar, Activity, Info, BarChart2 } from 'lucide-react';

interface Props {
  research: ResearchAgentResponse;
}

const MetricDisplay = ({ label, metric }: { label: string; metric?: ResearchMetric | null }) => {
  if (!metric || metric.mean === null) {
    return (
      <div className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
        <span className="text-sm text-slate-400">{label}</span>
        <span className="text-sm font-medium text-slate-500">N/A</span>
      </div>
    );
  }
  return (
    <div className="flex flex-col py-2 border-b border-white/5 last:border-0">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-slate-400">{label} (Mean)</span>
        <span className="text-sm font-semibold text-slate-200">{metric.mean}</span>
      </div>
      <div className="flex justify-between items-center text-xs text-slate-500">
        <span>Min: {metric.min}</span>
        <span>Max: {metric.max}</span>
      </div>
    </div>
  );
};

export const ResearchIntelligenceCard: React.FC<Props> = ({ research }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col mb-4 shadow-xl">
      
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-950/50 to-slate-900 border-b border-slate-800 px-4 py-3 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Database className="w-5 h-5 text-indigo-400" />
          <h3 className="font-semibold text-slate-200 text-sm tracking-wide">HISTORICAL RESEARCH</h3>
        </div>
        <div className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs font-medium text-slate-300">
          {research.analysis_type}
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Context */}
        <div className="flex flex-wrap gap-4 text-sm text-slate-400">
          <div className="flex items-center space-x-1.5 bg-slate-800/50 px-3 py-1.5 rounded border border-slate-700/50">
            <Calendar className="w-4 h-4 text-indigo-400" />
            <span>{research.temporal_range}</span>
          </div>
          {research.location && (
            <div className="flex items-center space-x-1.5 bg-slate-800/50 px-3 py-1.5 rounded border border-slate-700/50">
              <MapPin className="w-4 h-4 text-indigo-400" />
              <span>{research.location.latitude.toFixed(4)}, {research.location.longitude.toFixed(4)}</span>
            </div>
          )}
        </div>

        {/* Narrative */}
        {research.summary_explanation && (
          <div className="bg-indigo-950/20 border border-indigo-900/50 rounded p-3">
            <div className="flex space-x-2 mb-2">
              <BarChart2 className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
              <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">Analysis Summary</h4>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {research.summary_explanation}
            </p>
          </div>
        )}

        {/* Data Grid for Point/Temporal */}
        {research.analysis_type !== "SPATIAL_COMPARISON" && research.marine && research.weather && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-800/30 rounded border border-slate-700/50 p-3">
              <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Marine Data</h4>
              <MetricDisplay label="Sea Surface Temp (°C)" metric={research.marine.temperature_c} />
              <MetricDisplay label="Chlorophyll (mg/m³)" metric={research.marine.chlorophyll_mg_m3} />
            </div>
            <div className="bg-slate-800/30 rounded border border-slate-700/50 p-3">
              <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Weather Data</h4>
              <MetricDisplay label="Wind Speed (kn)" metric={research.weather.mean_wind_speed_knots} />
              <MetricDisplay label="Wave Height (m)" metric={research.weather.mean_wave_height_meters} />
            </div>
          </div>
        )}

        {/* Data Grid for Spatial Comparison */}
        {research.analysis_type === "SPATIAL_COMPARISON" && research.locations && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {research.locations.map((loc, idx) => (
              <div key={idx} className="bg-slate-800/30 rounded border border-slate-700/50 p-3">
                <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                  Location {idx + 1} ({loc.latitude.toFixed(2)}, {loc.longitude.toFixed(2)})
                </h4>
                {loc.data?.marine && (
                  <>
                    <MetricDisplay label="SST (°C)" metric={loc.data.marine.temperature_c} />
                    <MetricDisplay label="Chlorophyll" metric={loc.data.marine.chlorophyll_mg_m3} />
                  </>
                )}
                {loc.data?.weather && (
                  <>
                    <MetricDisplay label="Wind Speed" metric={loc.data.weather.mean_wind_speed_knots} />
                    <MetricDisplay label="Wave Height" metric={loc.data.weather.mean_wave_height_meters} />
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Provenance Footer */}
      {research.provenance && (
        <div className="bg-slate-900 border-t border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center space-x-1.5">
            <Info className="w-3.5 h-3.5" />
            <span>Source: {research.provenance.source}</span>
          </div>
          <span className="hidden sm:inline">Coverage: {research.provenance.coverage}</span>
        </div>
      )}
    </div>
  );
};
