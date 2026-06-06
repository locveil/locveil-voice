/**
 * Sidebar Component - Collapsible navigation sidebar
 * 
 * Provides navigation between different sections of the admin interface
 * with support for collapsing to save space.
 */

import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ChevronLeft, 
  ChevronRight, 
  Home, 
  FileText, 
  Code,
  Activity, 
  Settings,
  Menu,
  LucideIcon,
  MessageSquare,
  Globe
} from 'lucide-react';
import type { SidebarProps } from '@/types';

interface NavigationSection {
  id: string;
  titleKey: 'sidebar.sections.overview.title' | 'sidebar.sections.donations.title'
    | 'sidebar.sections.templates.title' | 'sidebar.sections.prompts.title'
    | 'sidebar.sections.localizations.title' | 'sidebar.sections.monitoring.title'
    | 'sidebar.sections.configuration.title';
  descriptionKey: 'sidebar.sections.overview.description' | 'sidebar.sections.donations.description'
    | 'sidebar.sections.templates.description' | 'sidebar.sections.prompts.description'
    | 'sidebar.sections.localizations.description' | 'sidebar.sections.monitoring.description'
    | 'sidebar.sections.configuration.description';
  icon: LucideIcon;
  path: string;
}

// Navigation sections configuration — titles/descriptions are i18n keys (resolved in render).
const navigationSections: NavigationSection[] = [
  { id: 'overview', titleKey: 'sidebar.sections.overview.title', descriptionKey: 'sidebar.sections.overview.description', icon: Home, path: '/' },
  { id: 'donations', titleKey: 'sidebar.sections.donations.title', descriptionKey: 'sidebar.sections.donations.description', icon: FileText, path: '/donations' },
  { id: 'templates', titleKey: 'sidebar.sections.templates.title', descriptionKey: 'sidebar.sections.templates.description', icon: Code, path: '/templates' },
  { id: 'prompts', titleKey: 'sidebar.sections.prompts.title', descriptionKey: 'sidebar.sections.prompts.description', icon: MessageSquare, path: '/prompts' },
  { id: 'localizations', titleKey: 'sidebar.sections.localizations.title', descriptionKey: 'sidebar.sections.localizations.description', icon: Globe, path: '/localizations' },
  { id: 'monitoring', titleKey: 'sidebar.sections.monitoring.title', descriptionKey: 'sidebar.sections.monitoring.description', icon: Activity, path: '/monitoring' },
  { id: 'configuration', titleKey: 'sidebar.sections.configuration.title', descriptionKey: 'sidebar.sections.configuration.description', icon: Settings, path: '/configuration' },
];

const Sidebar = ({ collapsed, onToggle }: SidebarProps) => {
  const { t } = useTranslation('layout');
  const navigate = useNavigate();
  const location = useLocation();

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  const isActivePath = (path: string): boolean => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className={`bg-gray-900 text-white transition-all duration-300 flex flex-col ${
      collapsed ? 'w-16' : 'w-64'
    }`}>
      {/* Header with toggle */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        {!collapsed && (
          <div>
            <h2 className="text-lg font-semibold">{t('sidebar.navigation')}</h2>
            <p className="text-xs text-gray-300 mt-0.5">{t('sidebar.adminInterface')}</p>
          </div>
        )}
        <button
          onClick={() => onToggle(!collapsed)}
          className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
          title={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
          aria-label={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation menu */}
      <nav className="flex-1 mt-6" role="navigation">
        <div className="px-2 space-y-1">
          {navigationSections.map((section) => {
            const Icon = section.icon;
            const isActive = isActivePath(section.path);
            
            return (
              <button
                key={section.id}
                onClick={() => handleNavigation(section.path)}
                className={`w-full flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors group ${
                  isActive
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
                title={collapsed ? t(section.descriptionKey) : ''}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed && (
                  <>
                    <span className="ml-3">{t(section.titleKey)}</span>
                    {isActive && (
                      <div 
                        className="ml-auto w-2 h-2 bg-blue-400 rounded-full"
                        aria-hidden="true"
                      />
                    )}
                  </>
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Footer with version info */}
      {!collapsed && (
        <div className="p-4 border-t border-gray-700">
          <div className="text-xs text-gray-400">
            <p className="font-medium">{t('sidebar.footerTitle')}</p>
            <p className="mt-1">{t('sidebar.footerSubtitle')}</p>
          </div>
        </div>
      )}

      {/* Collapsed footer */}
      {collapsed && (
        <div className="p-4 border-t border-gray-700 flex justify-center">
          <Menu className="w-4 h-4 text-gray-400" />
        </div>
      )}
    </div>
  );
};

export default Sidebar;
