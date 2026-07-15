import React from 'react';
import type { TextAreaProps } from '@/types';
import { Textarea as KitTextarea, Label, cn } from 'locveil-ui-kit';

export default function TextArea({
  label,
  value,
  onChange,
  placeholder,
  error,
  disabled = false,
  required = false,
  rows = 4,
  className = ''
}: TextAreaProps) {
  const id = React.useId();

  return (
    <div className={cn('mb-3', className)}>
      {label && (
        <Label htmlFor={id} className="mb-1">
          {label}
          {required && <span className="text-destructive">*</span>}
        </Label>
      )}
      <KitTextarea
        id={id}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        rows={rows}
        className="resize-y"
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error && (
        <div id={`${id}-error`} className="mt-1 text-sm text-destructive">
          {error}
        </div>
      )}
    </div>
  );
}
