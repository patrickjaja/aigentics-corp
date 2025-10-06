/**
 * Conversion Funnel Visualization Component (T096)
 *
 * Displays the customer journey from conversation to accepted offer
 * with conversion rates between each stage. Uses Recharts for visualization.
 */

'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, FunnelChart, Funnel, LabelList } from 'recharts';
import { TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';

interface ConversionFunnelData {
  conversations_started: number;
  conversations_completed: number;
  offers_generated: number;
  offers_sent: number;
  offers_viewed: number;
  offers_accepted: number;
  offers_rejected: number;
  completion_rate: number;
  generation_rate: number;
  acceptance_rate: number;
  overall_conversion: number;
}

interface ConversionFunnelProps {
  data: ConversionFunnelData;
}

export function ConversionFunnel({ data }: ConversionFunnelProps) {
  // Prepare funnel data for visualization
  const funnelData = [
    {
      stage: 'Conversations Started',
      value: data.conversations_started,
      fill: '#3b82f6',
      dropoff: 0
    },
    {
      stage: 'Conversations Completed',
      value: data.conversations_completed,
      fill: '#8b5cf6',
      dropoff: data.conversations_started - data.conversations_completed
    },
    {
      stage: 'Offers Generated',
      value: data.offers_generated,
      fill: '#ec4899',
      dropoff: data.conversations_completed - data.offers_generated
    },
    {
      stage: 'Offers Sent',
      value: data.offers_sent,
      fill: '#f59e0b',
      dropoff: data.offers_generated - data.offers_sent
    },
    {
      stage: 'Offers Viewed',
      value: data.offers_viewed,
      fill: '#10b981',
      dropoff: data.offers_sent - data.offers_viewed
    },
    {
      stage: 'Offers Accepted',
      value: data.offers_accepted,
      fill: '#059669',
      dropoff: data.offers_viewed - data.offers_accepted
    }
  ];

  // Calculate conversion rates between stages
  const conversionRates = [
    {
      from: 'Started',
      to: 'Completed',
      rate: data.completion_rate,
      status: data.completion_rate >= 0.7 ? 'good' : data.completion_rate >= 0.5 ? 'warning' : 'critical'
    },
    {
      from: 'Completed',
      to: 'Generated',
      rate: data.generation_rate,
      status: data.generation_rate >= 0.8 ? 'good' : data.generation_rate >= 0.6 ? 'warning' : 'critical'
    },
    {
      from: 'Sent',
      to: 'Accepted',
      rate: data.acceptance_rate,
      status: data.acceptance_rate >= 0.5 ? 'good' : data.acceptance_rate >= 0.3 ? 'warning' : 'critical'
    }
  ];

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return 'text-green-600 bg-green-50';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50';
      case 'critical':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'good':
        return <TrendingUp className="h-4 w-4" />;
      case 'warning':
      case 'critical':
        return <TrendingDown className="h-4 w-4" />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Overall Conversion</CardDescription>
            <CardTitle className="text-3xl">
              {formatPercentage(data.overall_conversion)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500">
              {data.offers_accepted} of {data.conversations_started} conversations resulted in accepted offers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Completion Rate</CardDescription>
            <CardTitle className="text-3xl">
              {formatPercentage(data.completion_rate)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500">
              {data.conversations_completed} of {data.conversations_started} conversations completed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Acceptance Rate</CardDescription>
            <CardTitle className="text-3xl">
              {formatPercentage(data.acceptance_rate)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500">
              {data.offers_accepted} of {data.offers_sent} offers accepted
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Funnel Visualization */}
      <Card>
        <CardHeader>
          <CardTitle>Conversion Funnel</CardTitle>
          <CardDescription>Customer journey from conversation to acceptance</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={funnelData}
              layout="vertical"
              margin={{ left: 150, right: 50 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="stage" type="category" width={140} />
              <Tooltip
                formatter={(value: number, name: string, props: any) => {
                  const total = funnelData[0].value;
                  const percentage = ((value / total) * 100).toFixed(1);
                  return [`${value} (${percentage}%)`, 'Count'];
                }}
              />
              <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                {funnelData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
                <LabelList
                  dataKey="value"
                  position="right"
                  formatter={(value: number) => value.toLocaleString()}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Stage-by-Stage Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Stage-by-Stage Analysis</CardTitle>
          <CardDescription>Detailed breakdown of each funnel stage</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {funnelData.map((stage, index) => {
              const previousValue = index > 0 ? funnelData[index - 1].value : stage.value;
              const conversionRate = previousValue > 0 ? (stage.value / previousValue) : 1;
              const dropoffRate = previousValue > 0 ? (stage.dropoff / previousValue) : 0;

              return (
                <div key={stage.stage} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: stage.fill }}
                      />
                      <span className="font-medium">{stage.stage}</span>
                    </div>
                    <span className="text-2xl font-bold">{stage.value.toLocaleString()}</span>
                  </div>

                  {index > 0 && (
                    <div className="ml-7 space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Conversion from previous:</span>
                        <span className={conversionRate >= 0.7 ? 'text-green-600' : 'text-yellow-600'}>
                          {formatPercentage(conversionRate)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Drop-off:</span>
                        <span className="text-red-600">
                          {stage.dropoff.toLocaleString()} ({formatPercentage(dropoffRate)})
                        </span>
                      </div>

                      {/* Progress bar */}
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${conversionRate * 100}%`,
                            backgroundColor: stage.fill
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Conversion Rate Health */}
      <Card>
        <CardHeader>
          <CardTitle>Conversion Rate Health</CardTitle>
          <CardDescription>Key conversion metrics and their status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {conversionRates.map((rate, index) => (
              <div
                key={index}
                className={`flex items-center justify-between p-3 rounded-lg ${getStatusColor(rate.status)}`}
              >
                <div className="flex items-center gap-2">
                  {getStatusIcon(rate.status)}
                  <span className="font-medium">
                    {rate.from} → {rate.to}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xl font-bold">{formatPercentage(rate.rate)}</span>
                  {rate.status === 'critical' && (
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Insights & Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Insights & Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {data.completion_rate < 0.7 && (
              <li className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
                <div>
                  <p className="font-medium">Low Completion Rate</p>
                  <p className="text-sm text-gray-500">
                    Only {formatPercentage(data.completion_rate)} of conversations are being completed.
                    Consider simplifying questions or reducing conversation length.
                  </p>
                </div>
              </li>
            )}

            {data.acceptance_rate < 0.4 && (
              <li className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
                <div>
                  <p className="font-medium">Critical Acceptance Rate</p>
                  <p className="text-sm text-gray-500">
                    Acceptance rate of {formatPercentage(data.acceptance_rate)} is below target.
                    Review pricing strategy and offer competitiveness.
                  </p>
                </div>
              </li>
            )}

            {data.offers_viewed < data.offers_sent * 0.8 && (
              <li className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
                <div>
                  <p className="font-medium">Low View Rate</p>
                  <p className="text-sm text-gray-500">
                    Many sent offers are not being viewed. Improve email delivery and follow-up.
                  </p>
                </div>
              </li>
            )}

            {data.overall_conversion >= 0.3 && (
              <li className="flex items-start gap-2">
                <TrendingUp className="h-5 w-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium">Strong Overall Performance</p>
                  <p className="text-sm text-gray-500">
                    Overall conversion of {formatPercentage(data.overall_conversion)} is above industry average.
                  </p>
                </div>
              </li>
            )}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
