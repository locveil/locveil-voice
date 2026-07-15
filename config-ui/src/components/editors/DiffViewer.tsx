/**
 * DiffViewer Component - Dedicated component for viewing configuration changes
 * 
 * Phase 6 Feature: Provides side-by-side diff view for TOML configuration changes
 * with Monaco editor integration for professional diff experience.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { DiffEditor } from '@monaco-editor/react';
import Badge from '@/components/ui/Badge';

interface DiffViewerProps {
  original: string;
  modified: string;
  title?: string;
  language?: string;
  theme?: 'light' | 'dark';
  height?: string;
  className?: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  original,
  modified,
  title,
  language = "toml",
  theme = 'light',
  height = "400px",
  className = ""
}) => {
  const { t } = useTranslation('configuration');
  return (
    <div className={`border border-border rounded-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted">
        <h4 className="text-sm font-medium text-foreground">{title || t('diff.title')}</h4>
        <div className="flex items-center space-x-2">
          <Badge variant="error">{t('diff.original')}</Badge>
          <Badge variant="success">{t('diff.modified')}</Badge>
        </div>
      </div>
      
      {/* Diff Editor */}
      <div className="p-0">
        <DiffEditor
          original={original}
          modified={modified}
          language={language}
          height={height}
          theme={theme === 'dark' ? 'vs-dark' : 'vs'}
          options={{
            readOnly: true,
            renderSideBySide: true,
            diffWordWrap: 'on',
            automaticLayout: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 14,
            lineHeight: 20,
            folding: true,
            lineNumbers: 'on',
            originalEditable: false,
            enableSplitViewResizing: true,
            renderOverviewRuler: true,
            ignoreTrimWhitespace: false
          }}
          loading={
            <div className="flex items-center justify-center p-8 text-muted-foreground">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-2"></div>
              <span>{t('diff.loading')}</span>
            </div>
          }
        />
      </div>
    </div>
  );
};

export default DiffViewer;
