// TypeScript mirrors of the backend Pydantic schemas.

export type UserRole = "commercial" | "manager" | "direction";
export type AgentType = "collector" | "trainer";
export type ConversationStatus = "active" | "completed" | "abandoned";
export type MessageSender = "user" | "agent";
export type ReportPeriodType = "daily" | "weekly" | "monthly";
export type DirectivePriority = "low" | "medium" | "high";
export type DirectiveStatus = "active" | "archived";

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  role: UserRole;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  phone: string | null;
  is_active: boolean;
  manager_id: string | null;
}

export interface CompetitorMention {
  name: string;
  price_mentioned: boolean | null;
  price_detail: string | null;
}

export interface ExtractedData {
  sentiment?: string | null;
  client_name?: string | null;
  order_result?: string | null;
  order_trend?: string | null;
  objections?: string[];
  competitors?: CompetitorMention[];
  product_knowledge_gap?: boolean | null;
  knowledge_gap_detail?: string | null;
  follow_up_needed?: boolean | null;
  follow_up_date?: string | null;
  follow_up_note?: string | null;
  error?: string;
}

export interface Message {
  id: string;
  sender: MessageSender;
  content: string;
  token_count: number;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  agent_type: AgentType;
  status: ConversationStatus;
  extracted_data: ExtractedData | null;
  total_tokens: number;
  started_at: string;
  ended_at: string | null;
}

export interface ConversationStart extends Conversation {
  first_message: Message | null;
}

export interface Directive {
  id: string;
  content: string;
  priority: DirectivePriority;
  status: DirectiveStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ReportInsights {
  trends?: string[];
  recurring_objections?: string[];
  competitor_alerts?: string[];
  training_needs?: string[];
  error?: string;
}

export interface ReportMetrics {
  conversation_count?: number;
  sentiments?: Record<string, number>;
  top_objections?: string[];
  competitors_mentioned?: Record<string, number>;
  knowledge_gap_count?: number;
}

export interface Report {
  id: string;
  period_type: ReportPeriodType;
  period_start: string;
  period_end: string;
  summary: string | null;
  insights: ReportInsights;
  metrics: ReportMetrics;
  generated_at: string;
}

export interface TrainingContent {
  id: string;
  title: string;
  raw_content: string;
  content_type: string;
  is_embedded: boolean;
  chunk_metadata: { chunk_count?: number };
  created_at: string;
}
