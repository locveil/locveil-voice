import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { SectionProps } from '@/types';
import { Card, CardTitle, Icon, cn } from 'locveil-ui-kit';

export default function Section({
  title,
  children,
  collapsible = true,
  defaultCollapsed = false,
  className = '',
  badge,
  actions
}: SectionProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const contentId = `section-content-${title.replace(/\s+/g, '-').toLowerCase()}`;

  if (!collapsible) {
    return (
      <Card className={cn('shadow-sm', className)}>
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg font-semibold">{title}</CardTitle>
            {badge}
          </div>
          {actions}
        </div>
        <div className="px-4 py-4">{children}</div>
      </Card>
    );
  }

  return (
    <Card className={cn('shadow-sm', className)}>
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex w-full items-center justify-between px-4 py-3 transition-colors duration-200 hover:bg-muted/60"
        aria-expanded={!isCollapsed}
        aria-controls={contentId}
      >
        <div className="flex items-center gap-2">
          <CardTitle className="text-left text-lg font-semibold">{title}</CardTitle>
          {badge}
        </div>
        <div className="flex items-center gap-2">
          {actions}
          <Icon
            icon={isCollapsed ? ChevronRight : ChevronDown}
            size="button"
            className="text-muted-foreground"
          />
        </div>
      </button>
      {!isCollapsed && (
        <div id={contentId} className="px-4 pb-4">
          {children}
        </div>
      )}
    </Card>
  );
}
