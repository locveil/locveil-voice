/**
 * TypeScript type definitions for Irene API responses and data structures
 */

// Base API response structure - matches backend standard
export interface BaseApiResponse {
  success: boolean;
  timestamp: number;
}

// Error response structure
export interface ApiError {
  error: string;
  details?: any;
  status_code?: number;
}

// Validation error/warning types - matches backend schemas
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ValidationWarning {
  type: string;
  message: string;
  path?: string;
}

// Legacy validation result structure for compatibility
export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  details?: any;
}

// Donation-related types
export interface DonationMethod {
  method_name: string;
  intent_suffix: string;
  description: string;
  phrases?: string[];
  lemmas?: string[];
  parameters?: any[];
  token_patterns?: Array<Array<Record<string, any>>>;
  slot_patterns?: Record<string, Array<Array<Record<string, any>>>>;
  examples?: Array<string | { text: string; parameters: Record<string, any> }>;
  boost?: number;
  
  // Legacy field mappings for backward compatibility
  name?: string; // Maps to method_name
  global_params?: string[]; // Legacy field
}

export interface DonationData {
  schema_version?: string;
  donation_version?: string;
  handler_domain: string;
  description: string;
  intent_name_patterns?: string[];
  action_patterns?: string[];
  domain_patterns?: string[];
  fallback_conditions?: any[];
  additional_recognition_patterns?: any[];
  language_detection?: any;
  train_keywords?: string[];
  method_donations: DonationMethod[];
  global_parameters?: any[];
  negative_patterns?: any[];
  
  // Legacy field mappings for backward compatibility
  domain?: string; // Maps to handler_domain
  methods?: DonationMethod[]; // Maps to method_donations
}

// Donation metadata - matches backend DonationMetadata schema exactly
export interface DonationListItem {
  handler_name: string;
  domain: string;
  description: string;
  methods_count: number;
  global_parameters_count: number;
  file_size: number;
  last_modified: number; // Unix timestamp
}

// Legacy donation types removed - replaced by language-aware types below

// Schema-related types
export interface JsonSchema {
  $schema?: string;
  type: string;
  properties?: Record<string, any>;
  required?: string[];
  definitions?: Record<string, any>;
  [key: string]: any;
}

// Updated to match backend DonationSchemaResponse schema exactly
export interface SchemaResponse extends BaseApiResponse {
  json_schema: Record<string, any>; // Backend uses "additionalProperties": true
  schema_version: string;
  supported_versions: string[];
}

// Legacy request/response types removed - replaced by language-aware types below

// System status types
export interface SystemStatus {
  status: 'healthy' | 'warning' | 'error';
  component: string;
  message?: string;
  last_updated: string;
  details?: any;
}

// Updated to match backend IntentSystemStatusResponse schema exactly
export interface IntentStatusResponse extends BaseApiResponse {
  status: string;
  handlers_count: number;
  handlers: string[];
  donations_count: number;
  donations: string[];
  registry_patterns: string[];
  donation_routing_enabled: boolean;
  parameter_extraction_integrated: boolean;
  configuration: Record<string, any> | null;
}

// Simplified handlers response (backend /intents/handlers returns basic JSON)
export interface IntentHandlersResponse {
  handlers: Array<{
    name: string;
    type: string;
    enabled: boolean;
    description?: string;
  }>;
  total_count: number;
}

// Updated to match backend IntentReloadResponse schema exactly
export interface ReloadResponse extends BaseApiResponse {
  status: string;
  handlers_count: number;
  handlers: string[];
  error?: string | null;
}

// ============================================================
// LANGUAGE-AWARE DONATION TYPES (Phase 3)
// ============================================================

export interface HandlerLanguageInfo {
  handler_name: string;
  languages: string[];
  total_languages: number;
  supported_languages: string[];
  default_language: string;
}

export interface DonationHandlerListResponse extends BaseApiResponse {
  handlers: HandlerLanguageInfo[];
  total_handlers: number;
}

export interface LanguageDonationMetadata {
  file_path: string;
  language: string;
  file_size: number;
  last_modified: number;
}

export interface CrossLanguageValidation {
  is_consistent: boolean;
  missing_methods: string[];
  extra_methods: string[];
  inconsistent_parameters: string[];
  total_methods: number;
  languages_compared: string[];
}

export interface LanguageDonationContentResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  donation_data: DonationData;
  metadata: LanguageDonationMetadata;
  available_languages: string[];
  cross_language_validation: CrossLanguageValidation;
}

export interface LanguageDonationUpdateResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  validation_passed: boolean;
  reload_triggered: boolean;
  backup_created: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface LanguageDonationValidationResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  is_valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  validation_types: string[];
}

export interface CreateLanguageResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  created: boolean;
  copied_from?: string;
}

export interface DeleteLanguageResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  deleted: boolean;
}

export interface ReloadDonationResponse extends BaseApiResponse {
  handler_name: string;
  reloaded: boolean;
  merged_languages: string[];
}

// ============================================================
// Phase 4: Cross-Language Validation Types
// ============================================================

export interface ValidationReport {
  handler_name: string;
  languages_checked: string[];
  parameter_consistency: boolean;
  missing_parameters: string[];
  extra_parameters: string[];
  type_mismatches: string[];
  warnings: string[];
  timestamp: number;
}

export interface CompletenessReport {
  handler_name: string;
  languages_checked: string[];
  method_completeness: boolean;
  missing_methods: string[];
  extra_methods: string[];
  all_methods: string[];
  method_counts_by_language: Record<string, number>;
  warnings: string[];
  timestamp: number;
}

export interface CrossLanguageValidationResponse extends BaseApiResponse {
  validation_type: string;
  parameter_report?: ValidationReport;
  completeness_report?: CompletenessReport;
}

// UI-5: SyncParameters*/SuggestTranslations*/TranslationSuggestions/MissingPhraseInfo removed —
// the parameter-sync feature is gone (params are single-source under v1.1) and rule-based
// suggest-translations is superseded by the LLM translate service (QUAL-42).

// ============================================================
// TEMPLATE MANAGEMENT TYPES (Phase 6)
// ============================================================

export interface TemplateMetadata {
  file_path: string;
  language: string;
  file_size: number;
  last_modified: number;
  template_count: number;
}

export interface TemplateContentResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  template_data: Record<string, any>;
  metadata: TemplateMetadata;
  available_languages: string[];
  schema_info: {
    expected_keys: string[];
    key_types: Record<string, string>;
  };
}

export interface TemplateUpdateResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  validation_passed: boolean;
  reload_triggered: boolean;
  backup_created: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface TemplateValidationResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  is_valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  validation_types: string[];
}

export interface CreateTemplateLanguageResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  created: boolean;
  copied_from?: string;
}

export interface DeleteTemplateLanguageResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  deleted: boolean;
  backup_created: boolean;
}

export interface TemplateHandlerListResponse extends BaseApiResponse {
  handlers: HandlerLanguageInfo[];
  total_handlers: number;
}

// ============================================================
// PROMPT MANAGEMENT TYPES (Phase 7)
// ============================================================

export interface PromptDefinition {
  description: string;
  usage_context: string;
  variables: Array<{ name: string; description: string }>;
  prompt_type: 'system' | 'template' | 'user';
  content: string;
}

export interface PromptMetadata {
  file_path: string;
  language: string;
  file_size: number;
  last_modified: number;
  prompt_count: number;
}

export interface PromptContentResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  prompt_data: Record<string, PromptDefinition>;
  metadata: PromptMetadata;
  available_languages: string[];
  schema_info: {
    required_fields: string[];
    prompt_types: string[];
  };
}

export interface PromptUpdateResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  validation_passed: boolean;
  reload_triggered: boolean;
  backup_created: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface PromptValidationResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  is_valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  validation_types: string[];
}

export interface CreatePromptLanguageResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  created: boolean;
  copied_from?: string;
}

export interface DeletePromptLanguageResponse extends BaseApiResponse {
  handler_name: string;
  language: string;
  deleted: boolean;
  backup_created: boolean;
}

export interface PromptHandlerListResponse extends BaseApiResponse {
  handlers: HandlerLanguageInfo[];
  total_handlers: number;
}

// ============================================================
// LOCALIZATION MANAGEMENT TYPES (Phase 8)
// ============================================================

export interface LocalizationMetadata {
  file_path: string;
  language: string;
  file_size: number;
  last_modified: number;
  entry_count: number;
}

export interface LocalizationContentResponse extends BaseApiResponse {
  domain: string;
  language: string;
  localization_data: Record<string, any>;
  metadata: LocalizationMetadata;
  available_languages: string[];
  schema_info: {
    expected_keys: string[];
    key_types: Record<string, string>;
    domain_description: string;
  };
}

export interface LocalizationUpdateResponse extends BaseApiResponse {
  domain: string;
  language: string;
  validation_passed: boolean;
  reload_triggered: boolean;
  backup_created: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface LocalizationValidationResponse extends BaseApiResponse {
  domain: string;
  language: string;
  is_valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  validation_types: string[];
}

export interface CreateLocalizationLanguageResponse extends BaseApiResponse {
  domain: string;
  language: string;
  created: boolean;
  copied_from?: string;
}

export interface DeleteLocalizationLanguageResponse extends BaseApiResponse {
  domain: string;
  language: string;
  deleted: boolean;
  backup_created: boolean;
}

export interface DomainLanguageInfo {
  domain: string;
  languages: string[];
  total_languages: number;
  supported_languages: string[];
  default_language: string;
}

export interface LocalizationDomainListResponse extends BaseApiResponse {
  domains: DomainLanguageInfo[];
  total_domains: number;
}

// ============================================================
// CONFIGURATION MANAGEMENT TYPES
// ============================================================

// QUAL-85: config interfaces are DERIVED from the generated OpenAPI types
// (`npm run gen:api-types` after `scripts/dump_openapi.py`) — the backend's Pydantic
// models are the single source of truth, so hand-written drift (phantom fields,
// missing sections) is structurally impossible here.
type ConfigSchemas = import('./openapi.gen').components['schemas'];

export type CoreConfig = ConfigSchemas['CoreConfig'];
export type OutputConfig = ConfigSchemas['OutputConfig'];
export type BridgeOutputConfig = ConfigSchemas['BridgeOutputConfig'];
export type TraceConfig = ConfigSchemas['TraceConfig'];
export type ReportsConfig = ConfigSchemas['ReportsConfig'];
export type SatelliteTLSConfig = ConfigSchemas['SatelliteTLSConfig'];
export type SatelliteConfig = ConfigSchemas['SatelliteConfig'];
export type SystemConfig = ConfigSchemas['SystemConfig'];
export type InputConfig = ConfigSchemas['InputConfig'];
export type MicrophoneInputConfig = ConfigSchemas['MicrophoneInputConfig'];
export type WebInputConfig = ConfigSchemas['WebInputConfig'];
export type CLIInputConfig = ConfigSchemas['CLIInputConfig'];
export type ComponentConfig = ConfigSchemas['ComponentConfig'];
export type TTSConfig = ConfigSchemas['TTSConfig'];
export type AudioConfig = ConfigSchemas['AudioConfig'];
export type ASRConfig = ConfigSchemas['ASRConfig'];
export type LLMConfig = ConfigSchemas['LLMConfig'];
export type VoiceTriggerConfig = ConfigSchemas['VoiceTriggerConfig'];
export type NLUConfig = ConfigSchemas['NLUConfig'];
export type TextProcessorConfig = ConfigSchemas['TextProcessorConfig'];
export type IntentSystemConfig = ConfigSchemas['IntentSystemConfig'];
export type ContextualCommandsConfig = ConfigSchemas['ContextualCommandsConfig'];
export type IntentHandlerListConfig = ConfigSchemas['IntentHandlerListConfig'];
export type VADConfig = ConfigSchemas['VADConfig'];
export type MonitoringConfig = ConfigSchemas['MonitoringConfig'];
export type NLUAnalysisConfig = ConfigSchemas['NLUAnalysisConfig'];
export type AssetConfig = ConfigSchemas['AssetConfig'];
export type WorkflowConfig = ConfigSchemas['WorkflowConfig'];
export type UnifiedVoiceAssistantWorkflowConfig = ConfigSchemas['UnifiedVoiceAssistantWorkflowConfig'];

// Configuration schema metadata (from Pydantic introspection)
export interface ConfigFieldSchema {
  type: string;
  description: string;
  required: boolean;
  default?: any;
  constraints?: Record<string, any>;
  properties?: Record<string, ConfigFieldSchema>; // For nested objects
  items?: ConfigFieldSchema; // For arrays of objects, e.g. wake_words: WakeWordSpec[] (QUAL-20)
  // UI-16 (E9): backend-declared widget hint (json_schema_extra.widget) — the widget
  // factory dispatches on this; absent = plain type-based widget.
  widget?: string;
}

// A single wake word, uniform across voice-trigger providers (QUAL-20; derived — QUAL-85).
export type WakeWordSpec = ConfigSchemas['WakeWordSpec'];

export interface ConfigSectionSchema {
  fields: Record<string, ConfigFieldSchema>;
  title: string;
  description: string;
}

export interface ConfigSchemaResponse {
  [sectionName: string]: ConfigSectionSchema;
}

// Section order and titles response for frontend auto-generation
export interface ConfigSectionOrderResponse extends BaseApiResponse {
  section_order: string[];
  section_titles: Record<string, string>;
  // UI-16 (E7): section name -> live-testable component name (the /{component}/configure
  // surface); the component roster derives from this, not a hardcoded list.
  component_sections?: Record<string, string>;
  total_sections: number;
}

// Configuration API responses (matching backend schemas)
export interface ConfigUpdateResponse extends BaseApiResponse {
  message: string;
  reload_triggered: boolean;
  backup_created?: string;
}

export interface ConfigValidationResponse extends BaseApiResponse {
  valid: boolean;
  data?: Record<string, any>;
  validation_errors?: ValidationError[];
}

export interface ConfigStatusResponse extends BaseApiResponse {
  config_path?: string;
  config_exists: boolean;
  hot_reload_active: boolean;
  component_initialized: boolean;
  last_modified?: number;
  file_size?: number;
}

export interface ProviderInfo {
  name: string;
  description: string;
  version: string;
  enabled_by_default: boolean;
}

export interface ProvidersResponse {
  [providerName: string]: ProviderInfo;
}

export interface AudioDeviceInfo {
  id: number;
  name: string;
  channels: number;
  sample_rate: number;
  is_default: boolean;
}

export interface AudioDevicesResponse {
  success: boolean;
  devices: AudioDeviceInfo[];
  total_count: number;
  message?: string;
}

// ============================================================
// RAW TOML CONFIGURATION TYPES (Phase 5)
// ============================================================

export interface RawTomlRequest {
  toml_content: string;
  validate_before_save?: boolean;
}

export interface RawTomlResponse extends BaseApiResponse {
  toml_content: string;
  config_path: string;
  file_size: number;
  last_modified: number;
}

export interface RawTomlSaveResponse extends BaseApiResponse {
  message: string;
  backup_created?: string;
  config_cached: boolean;
}

export interface RawTomlValidationRequest {
  toml_content: string;
}

export interface RawTomlValidationResponse extends BaseApiResponse {
  valid: boolean;
  data?: any;
  errors?: Array<{
    msg: string;
    type: string;
    loc?: (string | number)[];
  }>;
}

export interface SectionToTomlRequest {
  section_data: Record<string, any>;
}

export interface SectionToTomlResponse extends BaseApiResponse {
  toml_content: string;
  section_name: string;
  comments_preserved: boolean;
}

// ============================================================
// NLU ANALYSIS TYPES (Phase 3 - Comprehensive Implementation)
// ============================================================

// Core analysis request types
export interface AnalyzeDonationRequest {
  handler_name: string;
  language: string;
  donation_data: Record<string, any>;
}

export interface AnalyzeChangesRequest {
  changes: Record<string, Record<string, any>>;
  language?: string;
}

// Conflict and issue reporting types
export interface ConflictReport {
  intent_a: string;
  intent_b: string;
  language: string;
  severity: 'blocker' | 'warning' | 'info';
  score: number;
  conflict_type: string;
  signals: Record<string, any>;
  suggestions: string[];
}

export interface ScopeIssue {
  intent_name: string;
  language: string;
  issue_type: string;
  severity: 'blocker' | 'warning' | 'info';
  score: number;
  evidence: Record<string, any>;
  suggestions: string[];
}

// Validation results
export interface NLUValidationResult extends BaseApiResponse {
  is_valid: boolean;
  has_blocking_conflicts: boolean;
  has_warnings: boolean;
  conflicts: ConflictReport[];
  suggestions: string[];
  validation_time_ms: number;
}

// Analysis results
export interface NLUAnalysisResult extends BaseApiResponse {
  conflicts: ConflictReport[];
  scope_issues: ScopeIssue[];
  performance_metrics: Record<string, any>;
  language_coverage: Record<string, number>;
  analysis_time_ms: number;
}

export interface ChangeImpactAnalysisResponse extends BaseApiResponse {
  changes: Record<string, any>;
  affected_intents: string[];
  new_conflicts: ConflictReport[];
  resolved_conflicts: ConflictReport[];
  impact_score: number;
  recommendations: string[];
  analysis_time_ms: number;
}

export interface BatchAnalysisResponse extends BaseApiResponse {
  summary: Record<string, number>;
  conflicts: ConflictReport[];
  scope_issues: ScopeIssue[];
  system_health: Record<string, number>;
  language_breakdown: Record<string, Record<string, number>>;
  performance_metrics: Record<string, any>;
  recommendations: string[];
  analysis_time_ms: number;
  timestamp: number;
}

// System health reporting
export interface SystemHealthResponse extends BaseApiResponse {
  status: 'healthy' | 'degraded' | 'critical';
  health_score: number;
  component_status: Record<string, string>;
  conflict_summary: Record<string, number>;
  performance_summary: Record<string, number>;
  recommendations: string[];
  last_analysis: number;
}

// Legacy compatibility - kept for backward compatibility during transition
export interface BasicNLUAnalysisResult extends BaseApiResponse {
  conflicts: Array<Record<string, any>>;
  scope_issues: Array<Record<string, any>>;
  performance_metrics: Record<string, number>;
  language_coverage: Record<string, number>;
  analysis_time_ms: number;
}

// ============================================================
// PHASE 4: CONFIGURE RESPONSE TYPES FOR LIVE TESTING
// ============================================================

// Configure Response Types - matching backend schemas exactly
export interface TTSConfigureResponse extends BaseApiResponse {
  message: string;
  default_provider?: string;
  enabled_providers: string[];
  fallback_providers: string[];
}

export interface ASRConfigureResponse extends BaseApiResponse {
  message: string;
  default_provider?: string;
  enabled_providers: string[];
  language?: string;
}

export interface AudioConfigureResponse extends BaseApiResponse {
  message: string;
  default_provider?: string;
  enabled_providers: string[];
  fallback_providers: string[];
}

export interface LLMConfigureResponse extends BaseApiResponse {
  message: string;
  default_provider?: string;
  enabled_providers: string[];
  fallback_providers: string[];
}

export interface NLUConfigureResponse extends BaseApiResponse {
  message: string;
  default_provider?: string;
  enabled_providers: string[];
  confidence_threshold?: number;
}

export interface VoiceTriggerConfigureResponse extends BaseApiResponse {
  message: string;
  default_provider?: string;
  enabled_providers: string[];
  wake_words: (string | WakeWordSpec)[];  // runtime response may carry names or full specs (QUAL-20)
}

export interface TextProcessorConfigureResponse extends BaseApiResponse {
  message: string;
  enabled_providers: string[];
  stages: string[];
  normalizers: string[];
}

export interface IntentSystemConfigureResponse extends BaseApiResponse {
  message: string;
  confidence_threshold: number;
  fallback_intent: string;
  enabled_handlers: string[];
  loaded_donations: string[];
  handler_count: number;
}
