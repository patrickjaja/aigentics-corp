'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiClient } from '@/services/api';
import { Offer, GDPRConsent } from '@/types/api';

export default function OfferReviewPage() {
  const params = useParams();
  const router = useRouter();
  const offerId = params.id as string;

  const [offer, setOffer] = useState<Offer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDownloadForm, setShowDownloadForm] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Customer form state
  const [customerData, setCustomerData] = useState({
    companyName: '',
    contactPerson: '',
    email: '',
    phone: '',
    gdprConsent: false,
  });

  useEffect(() => {
    loadOffer();
  }, [offerId]);

  const loadOffer = async () => {
    setLoading(true);
    setError(null);

    try {
      const offerData = await apiClient.getOffer(offerId);
      setOffer(offerData);
    } catch (err: any) {
      setError(err.message || 'Failed to load offer');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!customerData.gdprConsent) {
      setError('Sie müssen der Datenschutzerklärung zustimmen');
      return;
    }

    if (!customerData.companyName || !customerData.contactPerson || !customerData.email) {
      setError('Bitte füllen Sie alle Pflichtfelder aus');
      return;
    }

    setDownloading(true);
    setError(null);

    try {
      const consent: GDPRConsent = {
        given: true,
        purposes: ['offer_generation'],
        consentTextVersion: '1.0',
      };

      const blob = await apiClient.downloadOffer(offerId, {
        companyName: customerData.companyName,
        contactPerson: customerData.contactPerson,
        email: customerData.email,
        phone: customerData.phone,
        gdprConsent: consent,
      });

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Angebot_${offer?.offerNumber || offerId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setShowDownloadForm(false);
    } catch (err: any) {
      setError(err.message || 'Failed to download offer');
    } finally {
      setDownloading(false);
    }
  };

  const formatCurrency = (amount: string | number, currency: string) => {
    const num = typeof amount === "number" ? amount : parseFloat(amount);
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: currency,
    }).format(num);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Lade Angebot...</p>
        </div>
      </div>
    );
  }

  if (error && !offer) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-xl font-bold text-red-800 mb-2">Fehler</h2>
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Zurück zur Startseite
          </button>
        </div>
      </div>
    );
  }

  if (!offer) return null;

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Angebot {offer.offerNumber}
              </h1>
              <p className="text-gray-600">Version {offer.version}</p>
            </div>
            <div className="text-right">
              <div
                className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                  offer.status === 'approved'
                    ? 'bg-green-100 text-green-800'
                    : offer.status === 'pending_approval'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {offer.status === 'draft' && 'Entwurf'}
                {offer.status === 'pending_approval' && 'Genehmigung ausstehend'}
                {offer.status === 'approved' && 'Genehmigt'}
                {offer.status === 'sent' && 'Versendet'}
                {offer.status === 'viewed' && 'Angesehen'}
                {offer.status === 'accepted' && 'Akzeptiert'}
                {offer.status === 'rejected' && 'Abgelehnt'}
                {offer.status === 'expired' && 'Abgelaufen'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Erstellt am:</span>
              <span className="ml-2 font-medium">{formatDate(offer.createdAt)}</span>
            </div>
            <div>
              <span className="text-gray-600">Gültig bis:</span>
              <span className="ml-2 font-medium">{formatDate(offer.validUntil)}</span>
            </div>
          </div>

          {offer.approvalRequired && (
            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-yellow-800 text-sm">
                Dieses Angebot erfordert eine Genehmigung durch einen Manager (Wert über EUR 100.000)
              </p>
            </div>
          )}
        </div>

        {/* Total Value */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="text-center">
            <p className="text-gray-600 text-sm mb-2">Gesamtwert</p>
            <p className="text-4xl font-bold text-gray-900">
              {formatCurrency(offer.totalCost, offer.currency)}
            </p>
          </div>
        </div>

        {/* Work Packages */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Arbeitspakete</h2>
          <div className="space-y-4">
            {offer.workPackages.map((wp, idx) => (
              <div key={wp.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {idx + 1}. {wp.title}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">{wp.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-gray-900">
                      {formatCurrency(wp.totalCost, offer.currency)}
                    </p>
                  </div>
                </div>

                {/* Deliverables */}
                {wp.deliverables.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">Liefergegenstände:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {wp.deliverables.map((deliverable, didx) => (
                        <li key={didx} className="text-sm text-gray-600">
                          {deliverable.name}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Estimation */}
                <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Geschätzte Stunden:</span>
                    <span className="ml-2 font-medium">{wp.estimatedHours}h</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Stundensatz:</span>
                    <span className="ml-2 font-medium">
                      {formatCurrency(wp.hourlyRate, offer.currency)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Konfidenz:</span>
                    <span className="ml-2 font-medium">
                      {(1 * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Terms and Conditions */}
        {offer.terms_and_conditions && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Allgemeine Geschäftsbedingungen
            </h2>
            <div className="prose prose-sm max-w-none text-gray-600">
              <p className="whitespace-pre-wrap">{offer.terms_and_conditions}</p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {!showDownloadForm ? (
            <div className="flex gap-4">
              <button
                onClick={() => setShowDownloadForm(true)}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors"
              >
                Als PDF herunterladen
              </button>
              <button
                onClick={() => router.push('/')}
                className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
              >
                Zurück
              </button>
            </div>
          ) : (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Kundendaten für Download
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Firma *
                  </label>
                  <input
                    type="text"
                    value={customerData.companyName}
                    onChange={(e) =>
                      setCustomerData({ ...customerData, companyName: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ansprechpartner *
                  </label>
                  <input
                    type="text"
                    value={customerData.contactPerson}
                    onChange={(e) =>
                      setCustomerData({ ...customerData, contactPerson: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    E-Mail *
                  </label>
                  <input
                    type="email"
                    value={customerData.email}
                    onChange={(e) =>
                      setCustomerData({ ...customerData, email: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Telefon
                  </label>
                  <input
                    type="tel"
                    value={customerData.phone}
                    onChange={(e) =>
                      setCustomerData({ ...customerData, phone: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="gdpr-consent"
                    checked={customerData.gdprConsent}
                    onChange={(e) =>
                      setCustomerData({ ...customerData, gdprConsent: e.target.checked })
                    }
                    className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="gdpr-consent" className="text-sm text-gray-700">
                    Ich stimme der Verarbeitung meiner Daten gemäß der Datenschutzerklärung zu.
                    Die Daten werden ausschließlich zur Erstellung und Versendung des Angebots
                    verwendet und nach den gesetzlichen Aufbewahrungsfristen gelöscht.
                  </label>
                </div>

                <div className="flex gap-4 pt-4">
                  <button
                    onClick={handleDownload}
                    disabled={downloading || !customerData.gdprConsent}
                    className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    {downloading ? 'Wird heruntergeladen...' : 'Jetzt herunterladen'}
                  </button>
                  <button
                    onClick={() => setShowDownloadForm(false)}
                    className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
                  >
                    Abbrechen
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
