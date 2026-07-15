import type { BadgeProps } from '@/types';
import { Badge as KitBadge, StatusChip, type StatusVariant } from 'locveil-ui-kit';

// Status variants map onto the kit's status contract (StatusChip, never raw palette
// classes); 'custom' keeps the neutral pill shell and lets the caller style it.
const statusFor: Record<Exclude<NonNullable<BadgeProps['variant']>, 'custom'>, StatusVariant> = {
  default: 'pristine',
  success: 'persisted',
  warning: 'edited',
  error: 'conflict',
  info: 'tested',
};

export default function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  if (variant === 'custom') {
    return (
      <KitBadge variant="outline" className={className}>
        {children}
      </KitBadge>
    );
  }
  return (
    <StatusChip variant={statusFor[variant]} className={className}>
      {children}
    </StatusChip>
  );
}
