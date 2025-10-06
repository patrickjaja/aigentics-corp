"use client";

import * as React from "react";
import {
  Check,
  X,
  Clock,
  AlertCircle,
  Euro,
  Filter,
  Search,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { Approval } from "@/types/api";

interface ApprovalDashboardProps {
  onApprove?: (approvalId: string, comments?: string) => Promise<void>;
  onReject?: (approvalId: string, comments: string) => Promise<void>;
  onView?: (approvalId: string) => void;
  className?: string;
}

export function ApprovalDashboard({
  onApprove,
  onReject,
  onView,
  className,
}: ApprovalDashboardProps) {
  const [approvals, setApprovals] = React.useState<Approval[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [filter, setFilter] = React.useState<"all" | "pending" | "approved" | "rejected">("pending");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedApproval, setSelectedApproval] = React.useState<Approval | null>(null);

  React.useEffect(() => {
    loadApprovals();
  }, [filter]);

  const loadApprovals = async () => {
    setIsLoading(true);
    try {
      const endpoint =
        filter === "all"
          ? "/api/v1/admin/approvals"
          : `/api/v1/admin/approvals?status=${filter}`;

      const response = await fetch(endpoint);
      if (!response.ok) throw new Error("Failed to load approvals");

      const data = await response.json();
      setApprovals(data.approvals || []);
    } catch (error) {
      console.error("Failed to load approvals:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredApprovals = approvals.filter((approval) =>
    approval.offerId.toLowerCase().includes(searchQuery.toLowerCase()) ||
    approval.requestedBy.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const stats = {
    pending: approvals.filter((a) => a.status === "pending").length,
    approved: approvals.filter((a) => a.status === "approved").length,
    rejected: approvals.filter((a) => a.status === "rejected").length,
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardDescription>Ausstehend</CardDescription>
              <Clock className="h-4 w-4 text-orange-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.pending}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardDescription>Genehmigt</CardDescription>
              <Check className="h-4 w-4 text-green-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.approved}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardDescription>Abgelehnt</CardDescription>
              <X className="h-4 w-4 text-red-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.rejected}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Suche nach Angebots-ID oder Ersteller..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="w-full sm:w-[200px]">
              <Select
                value={filter}
                onValueChange={(value: typeof filter) => setFilter(value)}
              >
                <SelectTrigger>
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4" />
                    <SelectValue />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle</SelectItem>
                  <SelectItem value="pending">Ausstehend</SelectItem>
                  <SelectItem value="approved">Genehmigt</SelectItem>
                  <SelectItem value="rejected">Abgelehnt</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Approvals List */}
      <div className="space-y-4">
        {isLoading ? (
          <Card>
            <CardContent className="p-6">
              <p className="text-center text-muted-foreground">Lade Genehmigungen...</p>
            </CardContent>
          </Card>
        ) : filteredApprovals.length === 0 ? (
          <Card>
            <CardContent className="p-6">
              <p className="text-center text-muted-foreground">
                Keine Genehmigungen gefunden
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredApprovals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={onApprove}
              onReject={onReject}
              onView={onView}
              isSelected={selectedApproval?.id === approval.id}
              onSelect={() => setSelectedApproval(approval)}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface ApprovalCardProps {
  approval: Approval;
  onApprove?: (approvalId: string, comments?: string) => Promise<void>;
  onReject?: (approvalId: string, comments: string) => Promise<void>;
  onView?: (approvalId: string) => void;
  isSelected?: boolean;
  onSelect?: () => void;
}

function ApprovalCard({
  approval,
  onApprove,
  onReject,
  onView,
  isSelected,
  onSelect,
}: ApprovalCardProps) {
  const [showReviewForm, setShowReviewForm] = React.useState(false);
  const [reviewComments, setReviewComments] = React.useState("");
  const [isProcessing, setIsProcessing] = React.useState(false);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: "EUR",
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (status: Approval["status"]) => {
    const variants = {
      pending: { variant: "outline" as const, label: "Ausstehend", icon: Clock },
      approved: { variant: "default" as const, label: "Genehmigt", icon: Check },
      rejected: { variant: "destructive" as const, label: "Abgelehnt", icon: X },
    };

    const { variant, label, icon: Icon } = variants[status];
    return (
      <Badge variant={variant} className="flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {label}
      </Badge>
    );
  };

  const handleApprove = async () => {
    if (!onApprove) return;
    setIsProcessing(true);
    try {
      await onApprove(approval.id, reviewComments || undefined);
      setShowReviewForm(false);
      setReviewComments("");
    } catch (error) {
      console.error("Failed to approve:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!onReject || !reviewComments.trim()) {
      alert("Bitte geben Sie einen Ablehnungsgrund an.");
      return;
    }
    setIsProcessing(true);
    try {
      await onReject(approval.id, reviewComments);
      setShowReviewForm(false);
      setReviewComments("");
    } catch (error) {
      console.error("Failed to reject:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // High-value indicator (EUR 100k+ requires approval)
  const isHighValue = approval.totalCost >= 100000;

  return (
    <Card className={cn(isSelected && "ring-2 ring-primary")}>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">
                Angebot #{approval.offerId.slice(0, 8)}
              </CardTitle>
              {isHighValue && (
                <AlertCircle className="h-4 w-4 text-orange-500" title="Hoher Wert (≥ EUR 100.000)" />
              )}
            </div>
            <CardDescription>
              Erstellt von {approval.requestedBy} am {formatDate(approval.requestedAt)}
            </CardDescription>
          </div>
          {getStatusBadge(approval.status)}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Amount */}
        <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Euro className="h-4 w-4" />
            <span className="text-sm">Gesamtwert</span>
          </div>
          <span className="text-2xl font-bold">
            {formatCurrency(approval.totalCost)}
          </span>
        </div>

        {/* Review Information (if reviewed) */}
        {approval.reviewedBy && (
          <div className="border-t pt-4 space-y-2">
            <p className="text-sm text-muted-foreground">
              Geprüft von {approval.reviewedBy} am {formatDate(approval.reviewedAt!)}
            </p>
            {approval.comments && (
              <div className="p-3 bg-muted rounded-md">
                <p className="text-sm">{approval.comments}</p>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        {approval.status === "pending" && (
          <div className="space-y-4 border-t pt-4">
            {!showReviewForm ? (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => onView?.(approval.offerId)}
                  className="flex-1"
                >
                  <Eye className="h-4 w-4 mr-2" />
                  Angebot ansehen
                </Button>
                <Button
                  onClick={() => setShowReviewForm(true)}
                  className="flex-1"
                >
                  Prüfen
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor={`comments-${approval.id}`}>
                    Kommentare (optional für Genehmigung, erforderlich für Ablehnung)
                  </Label>
                  <Textarea
                    id={`comments-${approval.id}`}
                    value={reviewComments}
                    onChange={(e) => setReviewComments(e.target.value)}
                    placeholder="Ihre Anmerkungen zur Entscheidung..."
                    rows={3}
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowReviewForm(false);
                      setReviewComments("");
                    }}
                    disabled={isProcessing}
                  >
                    Abbrechen
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleReject}
                    disabled={isProcessing}
                  >
                    <X className="h-4 w-4 mr-2" />
                    Ablehnen
                  </Button>
                  <Button onClick={handleApprove} disabled={isProcessing}>
                    <Check className="h-4 w-4 mr-2" />
                    Genehmigen
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
