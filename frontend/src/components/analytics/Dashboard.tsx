/**
 * Analytics Dashboard Component (T095)
 *
 * Displays comprehensive analytics for offer generation, conversion rates,
 * and system performance. Uses Recharts for data visualization.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Download, RefreshCw, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { ConversionFunnel } from './ConversionFunnel';
import { format } from 'date-fns';

interface AnalyticsDashboardProps {
  startDate?: Date;
  endDate?: Date;
}

interface DashboardData {
  conversion_funnel: {
    conversations_started: number;
    conversations_completed: number;
    offers_generated: number;
    offers_sent: number;
    offers_viewed: number;
    offers_accepted: number;
    completion_rate: number;
    acceptance_rate: number;
    overall_conversion: number;
  };
  offer_metrics: {
    total_offers: number;
    total_accepted: number;
    avg_value: number;
    total_value: number;
    avg_generation_time_ms: number;
  };
  performance_metrics: {
    avg_response_time_ms: number;
    error_rate: number;
    sla_compliance_rate: number;
  };
  time_series: Array<{
    metric_name: string;
    data_points: Array<{
      timestamp: string;
      value: number;
      count: number;
    }>;
  }>;
  insights: string[];
}

export function AnalyticsDashboard({ startDate, endDate }: AnalyticsDashboardProps) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({
    start: startDate || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    end: endDate || new Date()
  });

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/analytics/dashboard?start_date=${format(dateRange.start, 'yyyy-MM-dd')}&end_date=${format(dateRange.end, 'yyyy-MM-dd')}`,
        {
          headers: {
            'X-Admin-Key': localStorage.getItem('admin_key') || ''
          }
        }
      );

      if (response.ok) {
        const result = await response.json();
        setData(result);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [dateRange]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR'
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const exportData = async (format: 'json' | 'csv') => {
    const response = await fetch(
      `/api/analytics/export?start_date=${format(dateRange.start, 'yyyy-MM-dd')}&end_date=${format(dateRange.end, 'yyyy-MM-dd')}&format=${format}`,
      {
        headers: {
          'X-Admin-Key': localStorage.getItem('admin_key') || ''
        }
      }
    );

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics-${format(dateRange.start, 'yyyy-MM-dd')}-${format(dateRange.end, 'yyyy-MM-dd')}.${format}`;
      a.click();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="animate-spin h-8 w-8 text-gray-500" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  const offersTimeSeriesData = data.time_series.find(ts => ts.metric_name === 'offers_generated')?.data_points.map(dp => ({
    date: format(new Date(dp.timestamp), 'MMM dd'),
    offers: dp.count,
    value: dp.value
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
          <p className="text-gray-500">
            {format(dateRange.start, 'MMM dd, yyyy')} - {format(dateRange.end, 'MMM dd, yyyy')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => exportData('csv')}>
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
          <Button variant="outline" onClick={() => exportData('json')}>
            <Download className="mr-2 h-4 w-4" />
            Export JSON
          </Button>
          <Button onClick={fetchAnalytics}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Key Insights */}
      {data.insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Key Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.insights.map((insight, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Offers</CardDescription>
            <CardTitle className="text-3xl">{data.offer_metrics.total_offers}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-green-600">
              <TrendingUp className="mr-1 h-4 w-4" />
              +12% from last period
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Acceptance Rate</CardDescription>
            <CardTitle className="text-3xl">
              {formatPercentage(data.conversion_funnel.acceptance_rate)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-gray-500">
              Target: 50%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Average Offer Value</CardDescription>
            <CardTitle className="text-3xl">
              {formatCurrency(data.offer_metrics.avg_value)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-green-600">
              <TrendingUp className="mr-1 h-4 w-4" />
              +5% from last period
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Generation Time</CardDescription>
            <CardTitle className="text-3xl">
              {(data.offer_metrics.avg_generation_time_ms / 1000).toFixed(1)}s
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-gray-500">
              Target: &lt;30s
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="funnel">Conversion Funnel</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Offers Timeline */}
          <Card>
            <CardHeader>
              <CardTitle>Offers Generated Over Time</CardTitle>
              <CardDescription>Daily offer generation volume</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={offersTimeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="offers"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.3}
                    name="Offers Generated"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Metrics Grid */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Financial Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-2">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Total Pipeline Value</dt>
                    <dd className="font-semibold">{formatCurrency(data.offer_metrics.total_value)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Accepted Offers</dt>
                    <dd className="font-semibold">{data.offer_metrics.total_accepted}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Average Deal Size</dt>
                    <dd className="font-semibold">{formatCurrency(data.offer_metrics.avg_value)}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>System Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-2">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Avg Response Time</dt>
                    <dd className="font-semibold">{data.performance_metrics.avg_response_time_ms}ms</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Error Rate</dt>
                    <dd className="font-semibold">{formatPercentage(data.performance_metrics.error_rate)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">SLA Compliance</dt>
                    <dd className="font-semibold">{formatPercentage(data.performance_metrics.sla_compliance_rate)}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="funnel">
          <ConversionFunnel data={data.conversion_funnel} />
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API Performance</CardTitle>
              <CardDescription>Response times and error rates</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[
                  { name: 'Avg', value: data.performance_metrics.avg_response_time_ms },
                  { name: 'Target', value: 1000 }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis label={{ value: 'ms', angle: -90, position: 'insideLeft' }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Offer Value Trend</CardTitle>
              <CardDescription>Average offer value over time</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={offersTimeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#10b981"
                    strokeWidth={2}
                    name="Avg Value"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
