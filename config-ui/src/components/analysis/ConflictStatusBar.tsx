/**
 * ConflictStatusBar Component - Real-time status indicator for NLU analysis
 * 
 * Displays the current analysis status and provides a summary of detected conflicts
 * with appropriate visual indicators for different severity levels.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import type { ConflictReport } from '@/types';

interface ConflictStatusBarProps {
  conflicts: ConflictReport[];
  status: 'idle' | 'analyzing' | 'complete' | 'error';
  className?: string;
}

const ConflictStatusBar: React.FC<ConflictStatusBarProps> = ({
  conflicts,
  status,
  className = ''
}) => {
  const { t } = useTranslation('common');
  const blockers = conflicts.filter(c => c.severity === 'blocker');
  const warnings = conflicts.filter(c => c.severity === 'warning');
  const infos = conflicts.filter(c => c.severity === 'info');

  const getStatusIcon = () => {
    switch (status) {
      case 'analyzing':
        return <Clock className="w-4 h-4 animate-spin text-blue-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'complete':
        if (blockers.length > 0) {
          return <AlertCircle className="w-4 h-4 text-red-500" />;
        } else if (warnings.length > 0) {
          return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
        } else {
          return <CheckCircle className="w-4 h-4 text-green-500" />;
        }
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'analyzing':
        return t('conflicts.status.analyzing');
      case 'error':
        return t('conflicts.status.failed');
      case 'complete':
        if (blockers.length > 0) {
          return t('conflicts.status.blockingDetected', { count: blockers.length });
        } else if (warnings.length > 0) {
          return t('conflicts.status.warningsDetected', { count: warnings.length });
        } else if (infos.length > 0) {
          return t('conflicts.status.infoDetected', { count: infos.length });
        } else {
          return t('conflicts.status.none');
        }
      default:
        return t('conflicts.status.ready');
    }
  };

  const getStatusColor = () => {
    if (status === 'analyzing') return 'border-blue-200 bg-blue-50';
    if (status === 'error') return 'border-red-200 bg-red-50';
    if (blockers.length > 0) return 'border-red-200 bg-red-50';
    if (warnings.length > 0) return 'border-yellow-200 bg-yellow-50';
    if (infos.length > 0) return 'border-blue-200 bg-blue-50';
    return 'border-green-200 bg-green-50';
  };

  return (
    <div className={`flex items-center justify-between p-3 border rounded-lg ${getStatusColor()} ${className}`}>
      <div className="flex items-center space-x-2">
        {getStatusIcon()}
        <span className="text-sm font-medium text-gray-700">
          {getStatusText()}
        </span>
      </div>
      
      {status === 'complete' && conflicts.length > 0 && (
        <div className="flex items-center space-x-3 text-xs">
          {blockers.length > 0 && (
            <div className="flex items-center space-x-1 text-red-600">
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <span>{t('conflicts.count.blockers', { count: blockers.length })}</span>
            </div>
          )}
          {warnings.length > 0 && (
            <div className="flex items-center space-x-1 text-yellow-600">
              <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
              <span>{t('conflicts.count.warnings', { count: warnings.length })}</span>
            </div>
          )}
          {infos.length > 0 && (
            <div className="flex items-center space-x-1 text-blue-600">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span>{t('conflicts.count.info', { count: infos.length })}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConflictStatusBar;
