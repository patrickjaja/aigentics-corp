// API Service for AI Offer Agent
// Handles all backend communication with type safety

import {
  Conversation,
  Message,
  Offer,
  Customer,
  Approval,
  ApiError,
  GDPRConsent,
} from '../types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/v1';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const error: ApiError = await response.json().catch(() => ({
          message: response.statusText,
          code: `HTTP_${response.status}`,
        }));
        throw error;
      }

      return await response.json();
    } catch (error) {
      if ((error as ApiError).code) {
        throw error;
      }
      throw {
        message: 'Network error or server unavailable',
        code: 'NETWORK_ERROR',
      } as ApiError;
    }
  }

  // Conversation API
  async startConversation(language: string, sessionId?: string): Promise<{
    conversationId: string;
    initialQuestions: string[];
  }> {
    return this.request('/conversations', {
      method: 'POST',
      body: JSON.stringify({ language, session_id: sessionId }),
    });
  }

  async getConversation(conversationId: string): Promise<Conversation> {
    return this.request(`/conversations/${conversationId}`);
  }

  async sendMessage(
    conversationId: string,
    message: string,
    context?: Record<string, any>
  ): Promise<{
    aiResponse: string;
    nextQuestions?: string[];
    completionPercentage: number;
    status: string;
  }> {
    return this.request(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    });
  }

  async completeConversation(conversationId: string): Promise<{
    projectId: string;
    completionPercentage: number;
  }> {
    return this.request(`/conversations/${conversationId}/complete`, {
      method: 'POST',
    });
  }

  // Offer API
  async generateOffer(
    projectId: string,
    conversationId: string,
    customerId?: string
  ): Promise<{
    offerId: string;
    offerNumber: string;
    status: string;
    totalValue: { amount: string; currency: string };
    requiresApproval: boolean;
    previewUrl: string;
  }> {
    return this.request('/offers', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        conversation_id: conversationId,
        customer_id: customerId,
      }),
    });
  }

  async getOffer(offerId: string): Promise<Offer> {
    return this.request(`/offers/${offerId}`);
  }

  async previewOffer(offerId: string, language?: string): Promise<{
    preview: string;
    workPackages: any[];
    totalValue: { amount: string; currency: string };
  }> {
    const query = language ? `?language=${language}` : '';
    return this.request(`/offers/${offerId}/preview${query}`);
  }

  async downloadOffer(
    offerId: string,
    customerData: {
      companyName: string;
      contactPerson: string;
      email: string;
      phone?: string;
      gdprConsent: GDPRConsent;
    }
  ): Promise<Blob> {
    const url = `${this.baseUrl}/offers/${offerId}/download`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer_data: {
          company_name: customerData.companyName,
          contact_person: customerData.contactPerson,
          email: customerData.email,
          phone: customerData.phone,
          gdpr_consent: customerData.gdprConsent,
        },
      }),
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw error;
    }

    return await response.blob();
  }

  // Customer API
  async createCustomer(customer: Customer): Promise<{ customerId: string }> {
    return this.request('/customers', {
      method: 'POST',
      body: JSON.stringify({
        company_name: customer.companyName,
        contact_person: customer.contactPerson,
        email: customer.email,
        phone: customer.phone,
        gdpr_consent: customer.gdprConsent,
      }),
    });
  }

  async deleteCustomer(customerId: string): Promise<{ message: string }> {
    return this.request(`/customers/${customerId}`, {
      method: 'DELETE',
    });
  }

  // Admin API
  async getPendingApprovals(): Promise<Approval[]> {
    return this.request('/approvals/pending');
  }

  async getApproval(approvalId: string): Promise<{
    id: string;
    offerId: string;
    status: string;
    requestedBy: string;
    requestedAt: string;
    approver: string;
    offer: Offer;
    comments: Array<{
      id: string;
      authorName: string;
      timestamp: string;
      content: string;
    }>;
  }> {
    return this.request(`/approvals/${approvalId}`);
  }

  async reviewApproval(
    approvalId: string,
    decision: 'approved' | 'rejected' | 'revision_requested',
    reason: string,
    conditions?: string[]
  ): Promise<{
    approvalId: string;
    status: string;
    decidedAt: string;
  }> {
    return this.request(`/approvals/${approvalId}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, reason, conditions }),
    });
  }

  async addComment(
    approvalId: string,
    content: string
  ): Promise<{
    commentId: string;
    timestamp: string;
  }> {
    return this.request(`/approvals/${approvalId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }

  // Health Check
  async healthCheck(): Promise<{
    status: string;
    services: Record<string, string>;
  }> {
    return this.request('/health');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export for testing/custom instances
export { ApiClient };
