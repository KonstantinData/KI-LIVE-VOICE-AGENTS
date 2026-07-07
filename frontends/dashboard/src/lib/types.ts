export interface Studio {
  id: string;
  name: string;
  slug: string;
  config?: Record<string, unknown> | null;
  is_active: boolean;
}

export interface Lead {
  id: string;
  visitor_id: string;
  status: string;
  score: number;
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  profile?: Record<string, unknown> | null;
  summary?: string | null;
  source_channel?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  lead_id?: string | null;
  visitor_id: string;
  channel: string;
  status: string;
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | string;
  content: string;
  tool_calls?: unknown[] | null;
  created_at: string;
}

export interface Appointment {
  id: string;
  lead_id: string;
  berater_id: string;
  datetime_: string;
  duration_minutes: number;
  status: string;
  notes?: string | null;
  created_at: string;
}

export interface FollowUp {
  id: string;
  lead_id: string;
  type: string;
  channel: string;
  scheduled_at: string;
  content?: string | null;
  status: string;
  autonomy_level: string;
  sent_at?: string | null;
}

export interface KnowledgeChunk {
  id: string;
  category: string;
  title: string;
  content: string;
  metadata_?: Record<string, unknown> | null;
  updated_at: string;
}

export interface Feedback {
  id: string;
  message_id: string;
  rating?: number | null;
  correction?: string | null;
  created_at: string;
}

export interface DashboardStats {
  studio: { id: string; name: string; slug: string };
  leads_total: number;
  leads_qualified: number;
  active_conversations: number;
  appointments_total: number;
  pending_followups: number;
  feedback_total: number;
  average_lead_score: number;
}

export interface CostSummary {
  event_count: number;
  conversation_count: number;
  total_tokens: number;
  input_audio_tokens: number;
  output_audio_tokens: number;
  input_image_tokens: number;
  estimated_cost_usd: number;
}

export interface CostBreakdownRow {
  name: string;
  event_count: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface DailyCostRow {
  date: string;
  event_count: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface ConversationCostRow {
  conversation_id: string;
  visitor_id: string;
  channel: string;
  event_count: number;
  total_tokens: number;
  estimated_cost_usd: number;
  last_event_at?: string | null;
}

export interface CostReport {
  studio: { id: string; name: string; slug: string };
  period_days: number;
  summary: CostSummary;
  daily: DailyCostRow[];
  by_component: CostBreakdownRow[];
  by_model: CostBreakdownRow[];
  by_channel: CostBreakdownRow[];
  top_conversations: ConversationCostRow[];
}
