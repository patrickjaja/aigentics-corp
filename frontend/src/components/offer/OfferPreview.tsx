"use client";

import * as React from "react";
import { Download, Check, X, Clock, Euro } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Offer, WorkPackage } from "@/types/api";

interface OfferPreviewProps {
  offer: Offer;
  onDownload?: () => void;
  onAccept?: () => void;
  onReject?: () => void;
  showActions?: boolean;
  className?: string;
}

export function OfferPreview({
  offer,
  onDownload,
  onAccept,
  onReject,
  showActions = true,
  className,
}: OfferPreviewProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: offer.currency || "EUR",
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  const getStatusBadge = (status: Offer["status"]) => {
    const variants: Record<
      Offer["status"],
      { variant: "default" | "secondary" | "destructive" | "outline"; label: string }
    > = {
      draft: { variant: "secondary", label: "Entwurf" },
      pending_approval: { variant: "outline", label: "Genehmigung ausstehend" },
      approved: { variant: "default", label: "Genehmigt" },
      sent: { variant: "default", label: "Versendet" },
      accepted: { variant: "default", label: "Angenommen" },
      rejected: { variant: "destructive", label: "Abgelehnt" },
    };

    const { variant, label } = variants[status];
    return <Badge variant={variant}>{label}</Badge>;
  };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle>Angebot #{offer.id.slice(0, 8)}</CardTitle>
            <CardDescription>
              Erstellt am {formatDate(offer.createdAt)} • Version {offer.version}
            </CardDescription>
          </div>
          {getStatusBadge(offer.status)}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Summary Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
          <div className="space-y-1">
            <div className="flex items-center text-sm text-muted-foreground">
              <Clock className="h-4 w-4 mr-2" />
              Gesamtstunden
            </div>
            <p className="text-2xl font-bold">{offer.totalHours}h</p>
          </div>
          <div className="space-y-1">
            <div className="flex items-center text-sm text-muted-foreground">
              <Euro className="h-4 w-4 mr-2" />
              Gesamtpreis
            </div>
            <p className="text-2xl font-bold">{formatCurrency(offer.totalCost)}</p>
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Gültig bis</div>
            <p className="text-lg font-semibold">
              {formatDate(offer.validUntil)}
            </p>
          </div>
        </div>

        {/* Work Packages */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Arbeitspakete</h3>
          {offer.workPackages.map((pkg, index) => (
            <WorkPackageCard key={pkg.id} workPackage={pkg} index={index + 1} />
          ))}
        </div>

        {/* Terms & Conditions */}
        <div className="border-t pt-4 space-y-2">
          <h4 className="font-semibold">Wichtige Hinweise</h4>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>
              Die angegebenen Stunden sind Schätzungen basierend auf Ihren
              Anforderungen
            </li>
            <li>
              Änderungen am Projektumfang können die Gesamtkosten beeinflussen
            </li>
            <li>
              Dieses Angebot ist gültig bis zum{" "}
              {formatDate(offer.validUntil)}
            </li>
            <li>
              Alle Preise verstehen sich zzgl. der gesetzlichen Mehrwertsteuer
            </li>
          </ul>
        </div>
      </CardContent>

      {showActions && (
        <CardFooter className="flex gap-2 justify-end border-t pt-6">
          {onDownload && (
            <Button variant="outline" onClick={onDownload}>
              <Download className="h-4 w-4 mr-2" />
              PDF herunterladen
            </Button>
          )}
          {offer.status === "sent" && (
            <>
              {onReject && (
                <Button variant="destructive" onClick={onReject}>
                  <X className="h-4 w-4 mr-2" />
                  Ablehnen
                </Button>
              )}
              {onAccept && (
                <Button onClick={onAccept}>
                  <Check className="h-4 w-4 mr-2" />
                  Angebot annehmen
                </Button>
              )}
            </>
          )}
        </CardFooter>
      )}
    </Card>
  );
}

interface WorkPackageCardProps {
  workPackage: WorkPackage;
  index: number;
}

function WorkPackageCard({ workPackage, index }: WorkPackageCardProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: "EUR",
    }).format(amount);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">
              {index}. {workPackage.title}
            </CardTitle>
            <CardDescription>{workPackage.description}</CardDescription>
          </div>
          <Badge variant="outline">
            {workPackage.estimatedHours}h
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Technologies */}
        {workPackage.technologies.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Technologien</p>
            <div className="flex flex-wrap gap-2">
              {workPackage.technologies.map((tech) => (
                <Badge key={tech} variant="secondary">
                  {tech}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Deliverables */}
        {workPackage.deliverables.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Leistungen</p>
            <ul className="text-sm space-y-1">
              {workPackage.deliverables.map((deliverable, idx) => (
                <li key={idx} className="flex items-start">
                  <Check className="h-4 w-4 mr-2 mt-0.5 text-green-500 flex-shrink-0" />
                  <span>{deliverable}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Pricing */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="text-sm text-muted-foreground">
            {workPackage.estimatedHours}h × {formatCurrency(workPackage.hourlyRate)}
          </div>
          <div className="text-lg font-semibold">
            {formatCurrency(workPackage.totalCost)}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
