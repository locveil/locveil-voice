/**
 * ValidationErrorDisplay Component - Displays TOML validation errors
 * 
 * Phase 6 Feature: Professional error display for real-time TOML validation
 * with proper formatting and error categorization.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { Alert, AlertTitle, AlertDescription, type AlertProps } from 'locveil-ui-kit';

interface ValidationError {
  msg: string;
  type: string;
  line?: number;
  column?: number;
}

interface ValidationErrorDisplayProps {
  errors: ValidationError[];
  className?: string;
}

export const ValidationErrorDisplay: React.FC<ValidationErrorDisplayProps> = ({
  errors,
  className = ""
}) => {
  const { t } = useTranslation('configuration');
  if (errors.length === 0) {
    return null;
  }

  const getErrorIcon = (errorType: string) => {
    switch (errorType) {
      case 'syntax_error':
      case 'parse_error':
        return <AlertCircle />;
      case 'validation_error':
        return <AlertTriangle className="text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]" />;
      case 'network_error':
        return <Info />;
      default:
        return <AlertCircle />;
    }
  };

  const getErrorVariant = (errorType: string): AlertProps['variant'] => {
    switch (errorType) {
      case 'syntax_error':
      case 'parse_error':
        return 'destructive';
      case 'validation_error':
        return 'default';
      case 'network_error':
        return 'accent';
      default:
        return 'destructive';
    }
  };

  const getErrorTitle = (errorType: string) => {
    switch (errorType) {
      case 'syntax_error':
        return t('validation.errorTitles.syntax');
      case 'parse_error':
        return t('validation.errorTitles.parse');
      case 'validation_error':
        return t('validation.errorTitles.validation');
      case 'network_error':
        return t('validation.errorTitles.network');
      default:
        return t('validation.errorTitles.default');
    }
  };

  return (
    <div className={`mt-4 space-y-2 ${className}`}>
      <div className="flex items-center space-x-2">
        <h4 className="text-sm font-medium text-destructive">
          {t('validation.title', { count: errors.length })}
        </h4>
        <div className="text-xs text-muted-foreground">
          {t('validation.fixBeforeSaving')}
        </div>
      </div>

      {errors.map((error, index) => (
        <Alert key={index} variant={getErrorVariant(error.type)}>
          {getErrorIcon(error.type)}
          <div>
            <AlertTitle>
              {getErrorTitle(error.type)}
              {error.line && error.column && (
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {t('validation.lineColumn', { line: error.line, column: error.column })}
                </span>
              )}
            </AlertTitle>
            <AlertDescription>
              {error.msg}
            </AlertDescription>
          </div>
        </Alert>
      ))}
    </div>
  );
};

export default ValidationErrorDisplay;
