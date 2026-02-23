// ============================================
// VOLO — Shared Types
// Used by both frontend (Next.js) and backend (FastAPI)
// ============================================

// ---- User & Tenant ----

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  branding: TenantBranding;
  plan: 'free' | 'pro' | 'enterprise';
  createdAt: string;
}

export interface TenantBranding {
  appName: string;
  logoUrl?: string;
  primaryColor: string;
  accentColor: string;
  fontFamily?: string;
  customDomain?: string;
  agentName: string;
  agentAvatar?: string;
}

export interface User {
  id: string;
  tenantId: string;
  email: string;
  name: string;
  avatarUrl?: string;
  role: 'owner' | 'admin' | 'member';
  preferences: UserPreferences;
  onboardingCompleted: boolean;
  createdAt: string;
}

export interface UserPreferences {
  theme: 'dark' | 'light' | 'system';
  language: string;
  timezone: string;
  agentPersonality: 'professional' | 'warm' | 'blunt' | 'playful' | 'custom';
  customPersonality?: string;
  complexityLevel: 'simple' | 'balanced' | 'power';
  voiceEnabled: boolean;
  notificationLevel: 'all' | 'important' | 'urgent-only' | 'none';
}

// ---- Conversations & Messages ----

export interface Conversation {
  id: string;
  userId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  pinned: boolean;
}

export interface ChatMessage {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  toolCalls?: ToolCallRecord[];
  metadata?: Record<string, unknown>;
  createdAt: string;
}

export interface ToolCallRecord {
  id: string;
  toolName: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  status: 'running' | 'completed' | 'failed';
  durationMs?: number;
}

// ---- Integrations ----

export type IntegrationCategory = 'code' | 'communication' | 'finance' | 'social' | 'machine' | 'web3';

export interface Integration {
  id: string;
  userId: string;
  type: IntegrationType;
  category: IntegrationCategory;
  name: string;
  status: 'connected' | 'disconnected' | 'error' | 'pending';
  config: Record<string, unknown>;
  lastSyncAt?: string;
  createdAt: string;
}

export type IntegrationType =
  // Code
  | 'github' | 'gitlab' | 'bitbucket'
  // Communication
  | 'gmail' | 'outlook' | 'slack' | 'discord' | 'teams'
  // Calendar
  | 'google_calendar' | 'outlook_calendar'
  // Finance
  | 'alpaca' | 'interactive_brokers' | 'coinbase' | 'binance' | 'plaid'
  // Social
  | 'twitter' | 'linkedin' | 'instagram'
  // Machine
  | 'remote_machine'
  // Web3
  | 'ethereum_wallet' | 'solana_wallet' | 'defi_monitor';

// ---- Memory ----

export interface MemoryEntry {
  id: string;
  userId: string;
  category: 'fact' | 'preference' | 'relationship' | 'project' | 'decision' | 'goal';
  content: string;
  source: string; // which conversation/integration it came from
  confidence: number; // 0-1
  createdAt: string;
  lastAccessedAt: string;
}

// ---- Projects (Cross-Project Intelligence) ----

export interface Project {
  id: string;
  userId: string;
  integrationId: string; // which GitHub/GitLab integration
  name: string;
  fullName: string; // e.g., "user/repo"
  description?: string;
  language?: string;
  techStack: string[];
  modules: ProjectModule[];
  lastAnalyzedAt?: string;
  healthScore?: number; // 0-100
}

export interface ProjectModule {
  id: string;
  projectId: string;
  name: string;
  path: string;
  type: 'auth' | 'api' | 'database' | 'ui' | 'billing' | 'notification' | 'util' | 'other';
  description: string;
  dependencies: string[];
  sharedWith: string[]; // project IDs that share similar modules
}

// ---- Standing Orders ----

export interface StandingOrder {
  id: string;
  userId: string;
  name: string;
  description: string;
  trigger: StandingOrderTrigger;
  actions: StandingOrderAction[];
  enabled: boolean;
  lastRunAt?: string;
  nextRunAt?: string;
  createdAt: string;
}

export interface StandingOrderTrigger {
  type: 'cron' | 'event' | 'condition';
  cronExpression?: string; // e.g., "0 7 * * *" for 7am daily
  eventType?: string; // e.g., "new_pr", "email_received"
  condition?: string; // natural language condition
}

export interface StandingOrderAction {
  type: 'summarize' | 'notify' | 'execute' | 'draft' | 'analyze';
  description: string;
  toolName?: string;
  parameters?: Record<string, unknown>;
}

// ---- Approval System ----

export type ApprovalTier = 'auto' | 'notify' | 'approve' | 'approve_2fa';

export interface ApprovalRequest {
  id: string;
  userId: string;
  tier: ApprovalTier;
  action: string;
  description: string;
  toolName: string;
  parameters: Record<string, unknown>;
  status: 'pending' | 'approved' | 'denied' | 'expired';
  createdAt: string;
  resolvedAt?: string;
}

// ---- API Request/Response ----

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  messages?: { role: string; content: string }[];
}

export interface StreamChunk {
  content?: string;
  tool_call?: ToolCallRecord;
  conversation_id?: string;
  done?: boolean;
}

// ---- White Label ----

export interface WhiteLabelConfig {
  tenant: Tenant;
  branding: TenantBranding;
  features: FeatureFlags;
}

export interface FeatureFlags {
  voiceEnabled: boolean;
  tradingEnabled: boolean;
  web3Enabled: boolean;
  machineControlEnabled: boolean;
  socialEnabled: boolean;
  standingOrdersEnabled: boolean;
  pluginMarketplaceEnabled: boolean;
  maxIntegrations: number;
  maxConversations: number;
  maxMemoryEntries: number;
}
