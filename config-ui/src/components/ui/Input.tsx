import React from 'react';
import type { InputProps } from '@/types';
import { Input as KitInput, Label, cn } from 'locveil-ui-kit';

export default function Input({
  label,
  value,
  onChange,
  placeholder,
  required = false,
  type = 'text',
  error,
  disabled = false,
  className = ''
}: InputProps) {
  const id = React.useId();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (type === 'number') {
      const numValue = e.target.value === '' ? '' : Number(e.target.value);
      onChange(String(numValue));
    } else {
      onChange(e.target.value);
    }
  };

  return (
    <div className={cn('mb-3', className)}>
      {label && (
        <Label htmlFor={id} className="mb-1">
          {label}
          {required && <span className="text-destructive">*</span>}
        </Label>
      )}
      <KitInput
        id={id}
        value={value ?? ''}
        onChange={handleChange}
        placeholder={placeholder}
        type={type}
        disabled={disabled}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        className={error ? 'border-destructive focus-visible:ring-destructive' : undefined}
      />
      {error && (
        <div id={`${id}-error`} className="mt-1 text-sm text-destructive">
          {error}
        </div>
      )}
    </div>
  );
}
