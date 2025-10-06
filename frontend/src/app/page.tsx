'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/services/api';
import { Conversation } from '@/types/api';

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; timestamp: string }>>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [questions, setQuestions] = useState<string[]>([]);
  const [completionPercentage, setCompletionPercentage] = useState(0);
  const [language, setLanguage] = useState<string>('en');
  const [conversationStatus, setConversationStatus] = useState<string>('active');

  const startNewConversation = async (selectedLanguage: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.startConversation(selectedLanguage);
      setConversationId(response.conversationId);
      setQuestions(response.initialQuestions);
      setLanguage(selectedLanguage);
      setMessages([
        {
          role: 'assistant',
          content: response.initialQuestions.join('\n'),
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err: any) {
      setError(err.message || 'Failed to start conversation');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!currentMessage.trim() || !conversationId) return;

    const userMessage = currentMessage.trim();
    setCurrentMessage('');
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: new Date().toISOString() },
    ]);

    setLoading(true);
    try {
      const response = await apiClient.sendMessage(conversationId, userMessage);

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.aiResponse,
          timestamp: new Date().toISOString(),
        },
      ]);

      if (response.nextQuestions && response.nextQuestions.length > 0) {
        setQuestions(response.nextQuestions);
      }

      setCompletionPercentage(response.completionPercentage);
      setConversationStatus(response.status);

      if (response.status === 'completed') {
        // Conversation completed, generate offer
        await handleGenerateOffer();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateOffer = async () => {
    if (!conversationId) return;

    setLoading(true);
    try {
      const completedResponse = await apiClient.completeConversation(conversationId);
      const offerResponse = await apiClient.generateOffer(
        completedResponse.projectId,
        conversationId
      );

      // Navigate to offer review page
      router.push(`/offer/${offerResponse.offerId}`);
    } catch (err: any) {
      setError(err.message || 'Failed to generate offer');
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  useEffect(() => {
    // Auto-start conversation with default language
    startNewConversation('en');
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            AI Offer Agent
          </h1>
          <p className="text-gray-600">
            Generieren Sie professionelle IT-Consulting Angebote durch ein intelligentes Gespräch
          </p>

          {/* Language Selector */}
          <div className="mt-4 flex items-center gap-4">
            <label htmlFor="language" className="text-sm font-medium text-gray-700">
              Sprache:
            </label>
            <select
              id="language"
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value);
                startNewConversation(e.target.value);
              }}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            >
              <option value="de">Deutsch</option>
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="es">Español</option>
              <option value="it">Italiano</option>
            </select>

            {/* Progress Indicator */}
            {conversationId && (
              <div className="ml-auto flex items-center gap-2">
                <span className="text-sm text-gray-600">Fortschritt:</span>
                <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 transition-all duration-300"
                    style={{ width: `${completionPercentage}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {completionPercentage}%
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Chat Interface */}
        {conversationId && (
          <div className="bg-white rounded-lg shadow-sm">
            {/* Messages */}
            <div className="h-[500px] overflow-y-auto p-6 space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <span className="text-xs opacity-70 mt-1 block">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-4 py-2">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-200 p-4">
              {questions.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Vorgeschlagene Fragen:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {questions.slice(0, 5).map((question, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setCurrentMessage(question);
                        }}
                        className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors"
                      >
                        {question.length > 50 ? question.slice(0, 50) + '...' : question}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <textarea
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Beschreiben Sie Ihr Projekt..."
                  disabled={loading || conversationStatus === 'completed'}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  rows={3}
                />
                <button
                  onClick={sendMessage}
                  disabled={loading || !currentMessage.trim() || conversationStatus === 'completed'}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  Senden
                </button>
              </div>

              {conversationStatus === 'completed' && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-green-800 font-medium">
                    Gespräch abgeschlossen! Ihr Angebot wird generiert...
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Loading State */}
        {!conversationId && loading && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Starte Gespräch...</p>
          </div>
        )}
      </div>
    </div>
  );
}
