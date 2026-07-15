import React from 'react';
import type { ToggleProps } from '@/types';
import { Checkbox, cn } from 'locveil-ui-kit';

export default function Toggle({
  label,
  checked,
  onChange,
  disabled = false,
  className = ''
}: ToggleProps) {
  const id = React.useId();

  return (
    <div className={cn('mb-2 flex items-center gap-3', className)}>
      <Checkbox
        id={id}
        checked={!!checked}
        onCheckedChange={(state) => onChange(state === true)}
        disabled={disabled}
      />
      <label
        htmlFor={id}
        className={cn(
          'select-none text-sm text-foreground',
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
        )}
      >
        {label}
      </label>
    </div>
  );
}
