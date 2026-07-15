/**
 * Smart Microphone Configuration Section
 * 
 * Provides intelligent microphone configuration with device detection,
 * automatic field population, and real-time capability validation.
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, Mic, Info } from 'lucide-react';
import { Checkbox, Input, Label } from 'locveil-ui-kit';
import apiClient from '@/utils/apiClient';
import type { AudioDeviceInfo } from '@/types/api';
// ConfigWidgetProps import removed - not used in this component

interface MicrophoneConfigSectionProps {
  data: any;
  schema: any;
  onChange: (data: any) => void;
  disabled?: boolean;
}

export const MicrophoneConfigSection: React.FC<MicrophoneConfigSectionProps> = ({
  data,
  schema,
  onChange,
  disabled = false
}) => {
  const { t } = useTranslation('configuration');
  const [devices, setDevices] = useState<AudioDeviceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<AudioDeviceInfo | null>(null);

  useEffect(() => {
    void loadAudioDevices();
  }, []);

  useEffect(() => {
    // Update selected device when device_id changes
    if (data?.device_id !== undefined && devices.length > 0) {
      const device = devices.find(d => d.id === data.device_id) || null;
      setSelectedDevice(device);
    }
  }, [data?.device_id, devices]);

  const loadAudioDevices = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getAvailableAudioDevices();
      if (response.success) {
        setDevices(response.devices);
      } else {
        console.warn('Failed to load audio devices:', response.message);
        setDevices([]);
      }
    } catch (error) {
      console.warn('Failed to load audio devices:', error);
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeviceChange = (deviceId: string) => {
    const numericId = deviceId === '' ? null : parseInt(deviceId, 10);
    const device = deviceId === '' ? null : devices.find(d => d.id === numericId);
    
    setSelectedDevice(device || null);
    
    // Auto-populate device capabilities
    const newData = {
      ...data,
      device_id: numericId,
      // Auto-set sample rate and channels from device capabilities
      sample_rate: device?.sample_rate || data.sample_rate || 16000,
      channels: device?.channels || data.channels || 1
    };
    
    onChange(newData);
  };

  const handleFieldChange = (fieldName: string, value: any) => {
    onChange({
      ...data,
      [fieldName]: value
    });
  };

  return (
    <div className="space-y-4 p-4 border border-border rounded-lg bg-muted">
      <div className="flex items-center space-x-2 mb-4">
        <Mic className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-medium text-foreground">{t('microphone.title')}</h3>
      </div>

      {/* Device Selection */}
      <div className="space-y-1">
        <Label>
          {t('microphone.audioDevice')}
          {schema?.device_id?.required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <div className="relative">
          <select
            value={data?.device_id === null || data?.device_id === undefined ? '' : data.device_id.toString()}
            onChange={(e) => handleDeviceChange(e.target.value)}
            disabled={disabled || loading}
            className="w-full appearance-none rounded-md border border-input bg-background px-3 py-2 pr-9 text-sm text-foreground transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="">{t('widgets.device.default')}</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name} {device.is_default ? t('widgets.device.systemDefault') : ''} - {device.channels}ch, {device.sample_rate}Hz
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
        {loading && (
          <div className="text-xs text-muted-foreground">{t('widgets.device.loading')}</div>
        )}
        {!loading && devices.length === 0 && (
          <div className="text-xs text-destructive">{t('widgets.device.none')}</div>
        )}
        {schema?.device_id?.description && (
          <div className="flex items-center">
            <Info className="h-3 w-3 text-muted-foreground mr-1" />
            <span className="text-xs text-muted-foreground">{schema.device_id.description}</span>
          </div>
        )}
      </div>

      {/* Device Capabilities (Read-only) */}
      {selectedDevice && (
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label>{t('microphone.sampleRate')}</Label>
            <div className="w-full px-3 py-2 border border-input rounded-md bg-muted text-muted-foreground text-sm">
              {selectedDevice.sample_rate}
            </div>
            <div className="text-xs text-muted-foreground">{t('microphone.autoDetected')}</div>
          </div>

          <div className="space-y-1">
            <Label>{t('microphone.channels')}</Label>
            <div className="w-full px-3 py-2 border border-input rounded-md bg-muted text-muted-foreground text-sm">
              {selectedDevice.channels}
            </div>
            <div className="text-xs text-muted-foreground">{t('microphone.autoDetected')}</div>
          </div>
        </div>
      )}

      {/* Other Configuration Fields */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <Label>
            {t('microphone.chunkSize')}
            {schema?.chunk_size?.required && <span className="text-destructive ml-1">*</span>}
          </Label>
          <Input
            type="number"
            value={data?.chunk_size ?? schema?.chunk_size?.default ?? 1024}
            onChange={(e) => handleFieldChange('chunk_size', parseInt(e.target.value, 10))}
            disabled={disabled}
          />
          {schema?.chunk_size?.description && (
            <div className="flex items-center">
              <Info className="h-3 w-3 text-muted-foreground mr-1" />
              <span className="text-xs text-muted-foreground">{schema.chunk_size.description}</span>
            </div>
          )}
        </div>

        <div className="space-y-1">
          <Label>
            {t('microphone.bufferQueueSize')}
            {schema?.buffer_queue_size?.required && <span className="text-destructive ml-1">*</span>}
          </Label>
          <Input
            type="number"
            value={data?.buffer_queue_size ?? schema?.buffer_queue_size?.default ?? 50}
            onChange={(e) => handleFieldChange('buffer_queue_size', parseInt(e.target.value, 10))}
            disabled={disabled}
          />
          {schema?.buffer_queue_size?.description && (
            <div className="flex items-center">
              <Info className="h-3 w-3 text-muted-foreground mr-1" />
              <span className="text-xs text-muted-foreground">{schema.buffer_queue_size.description}</span>
            </div>
          )}
        </div>
      </div>

      {/* Enable/Disable Toggle */}
      <div className="flex items-center space-x-3">
        <Checkbox
          id="microphone-enabled"
          checked={data?.enabled ?? true}
          onCheckedChange={(state) => handleFieldChange('enabled', state === true)}
          disabled={disabled}
        />
        <label htmlFor="microphone-enabled" className="text-sm font-medium text-foreground">
          {t('microphone.enableInput')}
        </label>
      </div>
    </div>
  );
};

export default MicrophoneConfigSection;
