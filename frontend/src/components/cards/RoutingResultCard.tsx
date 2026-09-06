import React from 'react';
import { RoutingAgentResponse } from '../../types/api';

interface RoutingResultCardProps {
  data: RoutingAgentResponse;
}

export const RoutingResultCard: React.FC<RoutingResultCardProps> = ({ data }) => {
  if (!data || !data.routing) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 p-4 rounded-xl text-sm border border-red-200 dark:border-red-800/50">
        Routing failed: {data?.error || 'Unknown error'}
      </div>
    );
  }

  const { routing } = data;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          Decision-Support Route
        </h4>
        <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
          routing.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' :
          'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
        }`}>
          {routing.status}
        </span>
      </div>

      {routing.status === 'SUCCESS' && (
        <>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-100 dark:border-slate-700/50">
              <span className="block text-slate-500 dark:text-slate-400 text-xs mb-1">Total Distance</span>
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                {routing.total_distance_km.toFixed(1)} km
              </span>
            </div>
            
            <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-100 dark:border-slate-700/50">
              <span className="block text-slate-500 dark:text-slate-400 text-xs mb-1">Waypoints</span>
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                {routing.route_points.length} nodes
              </span>
            </div>
          </div>

          <div className="text-sm text-slate-600 dark:text-slate-300 space-y-1">
            <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-slate-700/50">
              <span className="text-slate-500 dark:text-slate-400">Weather Check</span>
              <span className="font-medium text-slate-700 dark:text-slate-300">
                {routing.weather_assessment || 'Evaluated'}
              </span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-500 dark:text-slate-400">Boundary Check</span>
              <span className="font-medium text-slate-700 dark:text-slate-300">
                {routing.geofence_assessment || 'Evaluated'}
              </span>
            </div>
          </div>

          {routing.warnings && routing.warnings.length > 0 && (
            <div className="bg-amber-50 dark:bg-amber-900/20 p-3 rounded-lg border border-amber-200 dark:border-amber-800/50">
              <p className="text-xs font-semibold text-amber-800 dark:text-amber-400 mb-1 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Route Warnings
              </p>
              <ul className="list-disc list-inside text-xs text-amber-700 dark:text-amber-300 space-y-0.5">
                {routing.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {data.narrative && (
        <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
          <p className="text-sm text-slate-600 dark:text-slate-400 italic">
            "{data.narrative}"
          </p>
        </div>
      )}

      <div className="text-[10px] text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800/50">
        {data.disclaimer}
      </div>
    </div>
  );
};
