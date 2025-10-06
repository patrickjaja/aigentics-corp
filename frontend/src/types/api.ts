// API Types for AI Offer Agent

export interface Conversation {
  id: string;
  language: string;
  status: "active" | "completed" | "abandoned";
  createdAt: string;
  updatedAt: string;
}

export interface Message {
  id: string;
  conversationId: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface Question {
  id: string;
  text: string;
  type: "text" | "select" | "multiselect" | "number";
  options?: string[];
  required: boolean;
  answered?: boolean;
  answer?: string | string[] | number;
}

export interface WorkPackage {
  id: string;
  title: string;
  description: string;
  estimatedHours: number;
  hourlyRate: number;
  totalCost: number;
  deliverables: string[];
  technologies: string[];
}

export interface Offer {
  id: string;
  offerNumber: string;
  projectId: string;
  conversationId: string;
  status: "draft" | "pending_approval" | "approved" | "sent" | "viewed" | "accepted" | "rejected" | "expired";
  version: number;
  totalHours: number;
  totalCost: number;
  currency: string;
  workPackages: WorkPackage[];
  validUntil: string;
  approvalRequired?: boolean;
  approvalWorkflowId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Customer {
  id?: string;
  companyName: string;
  contactPerson: string;
  email: string;
  phone?: string;
  gdprConsent: GDPRConsent;
}

export interface GDPRConsent {
  given: boolean;
  purposes: string[];
  consentTextVersion: string;
  timestamp?: string;
  ip?: string;
}

export interface Approval {
  id: string;
  offerId: string;
  status: "pending" | "approved" | "rejected";
  totalCost: number;
  requestedBy: string;
  requestedAt: string;
  reviewedBy?: string;
  reviewedAt?: string;
  comments?: string;
}

export interface ApiError {
  message: string;
  code: string;
  details?: Record<string, unknown>;
}
