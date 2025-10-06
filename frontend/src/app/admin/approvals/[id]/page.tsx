'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiClient } from '@/services/api';

interface ApprovalDetails {
  id: string;
  offerId: string;
  status: string;
  requestedBy: string;
  requestedAt: string;
  approver: string;
  offer: {
    id: string;
    offerNumber: string;
    version: number;
    totalHours: number;
    totalCost: number;
    currency: string;
    workPackages: Array<{
      id: string;
      title: string;
      description: string;
      estimatedHours: number;
      hourlyRate: number;
      totalCost: number;
      deliverables: string[];
    }>;
  };
  comments: Array<{
    id: string;
    authorName: string;
    timestamp: string;
    content: string;
  }>;
}

export default function ApprovalDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const approvalId = params.id as string;

  const [approval, setApproval] = useState<ApprovalDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  // Review form state
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<'approved' | 'rejected' | 'revision_requested'>('approved');
  const [reviewReason, setReviewReason] = useState('');
  const [reviewConditions, setReviewConditions] = useState<string>('');

  // Comment form state
  const [newComment, setNewComment] = useState('');
  const [addingComment, setAddingComment] = useState(false);

  useEffect(() => {
    loadApproval();
  }, [approvalId]);

  const loadApproval = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.getApproval(approvalId);
      setApproval(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load approval details');
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async () => {
    if (!reviewReason.trim()) {
      setError('Bitte geben Sie einen Grund für Ihre Entscheidung an');
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const conditions = reviewConditions
        .split('\n')
        .map((c) => c.trim())
        .filter((c) => c.length > 0);

      await apiClient.reviewApproval(
        approvalId,
        reviewDecision,
        reviewReason,
        conditions.length > 0 ? conditions : undefined
      );

      // Reload approval
      await loadApproval();
      setShowReviewForm(false);
      setReviewReason('');
      setReviewConditions('');
    } catch (err: any) {
      setError(err.message || 'Failed to submit review');
    } finally {
      setProcessing(false);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;

    setAddingComment(true);
    setError(null);

    try {
      await apiClient.addComment(approvalId, newComment);
      setNewComment('');
      await loadApproval();
    } catch (err: any) {
      setError(err.message || 'Failed to add comment');
    } finally {
      setAddingComment(false);
    }
  };

  const formatCurrency = (amount: number, currency: string = 'EUR') => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'revision_requested':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Ausstehend';
      case 'approved':
        return 'Genehmigt';
      case 'rejected':
        return 'Abgelehnt';
      case 'revision_requested':
        return 'Überarbeitung erforderlich';
      default:
        return status;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Lade Genehmigungsdetails...</p>
        </div>
      </div>
    );
  }

  if (error && !approval) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-xl font-bold text-red-800 mb-2">Fehler</h2>
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => router.push('/admin')}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Zurück zum Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!approval) return null;

  const isPending = approval.status === 'pending';

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Genehmigung Details
              </h1>
              <p className="text-gray-600">Angebot {approval.offer.offerNumber}</p>
            </div>
            <div>
              <span
                className={`inline-block px-4 py-2 rounded-full text-sm font-medium ${getStatusBadgeClass(
                  approval.status
                )}`}
              >
                {getStatusLabel(approval.status)}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Angefragt von:</span>
              <span className="ml-2 font-medium">{approval.requestedBy}</span>
            </div>
            <div>
              <span className="text-gray-600">Angefragt am:</span>
              <span className="ml-2 font-medium">{formatDate(approval.requestedAt)}</span>
            </div>
            <div>
              <span className="text-gray-600">Genehmiger:</span>
              <span className="ml-2 font-medium">{approval.approver}</span>
            </div>
            <div>
              <span className="text-gray-600">Angebots-ID:</span>
              <span className="ml-2 font-medium font-mono text-xs">{approval.offerId}</span>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Offer Summary */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Angebots-Übersicht</h2>

          <div className="grid grid-cols-3 gap-6 mb-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Gesamtstunden</p>
              <p className="text-2xl font-bold text-gray-900">{approval.offer.totalHours}h</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Arbeitspakete</p>
              <p className="text-2xl font-bold text-gray-900">
                {approval.offer.workPackages.length}
              </p>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-700 mb-1">Gesamtwert</p>
              <p className="text-2xl font-bold text-blue-900">
                {formatCurrency(approval.offer.totalCost, approval.offer.currency)}
              </p>
            </div>
          </div>

          {/* Work Packages */}
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Arbeitspakete</h3>
          <div className="space-y-3">
            {approval.offer.workPackages.map((wp, idx) => (
              <div key={wp.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="font-semibold text-gray-900">
                      {idx + 1}. {wp.title}
                    </h4>
                    <p className="text-sm text-gray-600 mt-1">{wp.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-gray-900">
                      {formatCurrency(wp.totalCost, approval.offer.currency)}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 text-sm mt-3">
                  <div>
                    <span className="text-gray-600">Stunden:</span>
                    <span className="ml-2 font-medium">{wp.estimatedHours}h</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Stundensatz:</span>
                    <span className="ml-2 font-medium">
                      {formatCurrency(wp.hourlyRate, approval.offer.currency)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Liefergegenstände:</span>
                    <span className="ml-2 font-medium">{wp.deliverables.length}</span>
                  </div>
                </div>

                {wp.deliverables.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-gray-700 mb-1">
                      Liefergegenstände:
                    </p>
                    <ul className="list-disc list-inside space-y-1">
                      {wp.deliverables.map((deliverable, didx) => (
                        <li key={didx} className="text-sm text-gray-600">
                          {deliverable}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Comments */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Kommentare</h2>

          {approval.comments.length === 0 ? (
            <p className="text-gray-600 text-sm">Noch keine Kommentare</p>
          ) : (
            <div className="space-y-4 mb-6">
              {approval.comments.map((comment) => (
                <div key={comment.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <p className="font-medium text-gray-900">{comment.authorName}</p>
                    <p className="text-sm text-gray-500">{formatDate(comment.timestamp)}</p>
                  </div>
                  <p className="text-gray-700">{comment.content}</p>
                </div>
              ))}
            </div>
          )}

          {/* Add Comment Form */}
          <div className="border-t border-gray-200 pt-4">
            <textarea
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Kommentar hinzufügen..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
            />
            <div className="mt-2 flex justify-end">
              <button
                onClick={handleAddComment}
                disabled={addingComment || !newComment.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {addingComment ? 'Wird hinzugefügt...' : 'Kommentar hinzufügen'}
              </button>
            </div>
          </div>
        </div>

        {/* Review Actions */}
        {isPending && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Genehmigung prüfen</h2>

            {!showReviewForm ? (
              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setReviewDecision('approved');
                    setShowReviewForm(true);
                  }}
                  className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  Genehmigen
                </button>
                <button
                  onClick={() => {
                    setReviewDecision('revision_requested');
                    setShowReviewForm(true);
                  }}
                  className="flex-1 px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-medium"
                >
                  Überarbeitung anfordern
                </button>
                <button
                  onClick={() => {
                    setReviewDecision('rejected');
                    setShowReviewForm(true);
                  }}
                  className="flex-1 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                >
                  Ablehnen
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Entscheidung
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setReviewDecision('approved')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        reviewDecision === 'approved'
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Genehmigen
                    </button>
                    <button
                      onClick={() => setReviewDecision('revision_requested')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        reviewDecision === 'revision_requested'
                          ? 'bg-orange-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Überarbeitung
                    </button>
                    <button
                      onClick={() => setReviewDecision('rejected')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        reviewDecision === 'rejected'
                          ? 'bg-red-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Ablehnen
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Begründung *
                  </label>
                  <textarea
                    value={reviewReason}
                    onChange={(e) => setReviewReason(e.target.value)}
                    placeholder="Geben Sie eine Begründung für Ihre Entscheidung an..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    rows={4}
                    required
                  />
                </div>

                {reviewDecision === 'approved' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Bedingungen (optional, eine pro Zeile)
                    </label>
                    <textarea
                      value={reviewConditions}
                      onChange={(e) => setReviewConditions(e.target.value)}
                      placeholder="z.B. Zahlungsziel 30 Tage&#10;Abnahme nach Projektabschluss"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      rows={3}
                    />
                  </div>
                )}

                <div className="flex gap-4 pt-4">
                  <button
                    onClick={handleReview}
                    disabled={processing || !reviewReason.trim()}
                    className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
                  >
                    {processing ? 'Wird verarbeitet...' : 'Entscheidung bestätigen'}
                  </button>
                  <button
                    onClick={() => {
                      setShowReviewForm(false);
                      setReviewReason('');
                      setReviewConditions('');
                    }}
                    className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                  >
                    Abbrechen
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="flex gap-4">
          <button
            onClick={() => router.push('/admin')}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Zurück zum Dashboard
          </button>
          <button
            onClick={() => router.push(`/offer/${approval.offerId}`)}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Angebot anzeigen
          </button>
        </div>
      </div>
    </div>
  );
}
