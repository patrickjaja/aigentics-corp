"use client";

import * as React from "react";
import { Shield, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Customer, GDPRConsent } from "@/types/api";

interface ConsentFormProps {
  onConsent?: (customer: Customer) => void;
  consentTextVersion?: string;
  className?: string;
}

const CONSENT_PURPOSES = [
  {
    id: "offer_generation",
    label: "Angebotserstellung",
    description:
      "Verarbeitung Ihrer Daten zur Erstellung eines maßgeschneiderten Angebots",
    required: true,
  },
  {
    id: "data_storage",
    label: "Datenspeicherung",
    description:
      "Speicherung Ihrer Daten für 10 Jahre gemäß gesetzlicher Aufbewahrungspflichten",
    required: true,
  },
  {
    id: "email_communication",
    label: "E-Mail-Kommunikation",
    description:
      "Kontaktaufnahme per E-Mail bezüglich Ihres Projekts und Angebots",
    required: true,
  },
  {
    id: "marketing",
    label: "Marketing (optional)",
    description:
      "Informationen über ähnliche Dienstleistungen und Angebote (kann jederzeit widerrufen werden)",
    required: false,
  },
];

export function ConsentForm({
  onConsent,
  consentTextVersion = "1.0",
  className,
}: ConsentFormProps) {
  const [formData, setFormData] = React.useState({
    companyName: "",
    contactPerson: "",
    email: "",
    phone: "",
  });

  const [consentedPurposes, setConsentedPurposes] = React.useState<string[]>([]);
  const [hasReadPrivacyPolicy, setHasReadPrivacyPolicy] = React.useState(false);
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  const handleInputChange = (field: keyof typeof formData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handlePurposeToggle = (purposeId: string, checked: boolean) => {
    setConsentedPurposes((prev) =>
      checked ? [...prev, purposeId] : prev.filter((id) => id !== purposeId)
    );
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.companyName.trim()) {
      newErrors.companyName = "Firmenname ist erforderlich";
    }

    if (!formData.contactPerson.trim()) {
      newErrors.contactPerson = "Ansprechpartner ist erforderlich";
    }

    if (!formData.email.trim()) {
      newErrors.email = "E-Mail-Adresse ist erforderlich";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Ungültige E-Mail-Adresse";
    }

    // Check required purposes
    const requiredPurposes = CONSENT_PURPOSES.filter((p) => p.required).map(
      (p) => p.id
    );
    const missingPurposes = requiredPurposes.filter(
      (id) => !consentedPurposes.includes(id)
    );

    if (missingPurposes.length > 0) {
      newErrors.consent =
        "Bitte stimmen Sie allen erforderlichen Verarbeitungszwecken zu";
    }

    if (!hasReadPrivacyPolicy) {
      newErrors.privacy =
        "Bitte bestätigen Sie, dass Sie die Datenschutzerklärung gelesen haben";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const gdprConsent: GDPRConsent = {
      given: true,
      purposes: consentedPurposes,
      consentTextVersion,
      timestamp: new Date().toISOString(),
    };

    const customer: Customer = {
      companyName: formData.companyName,
      contactPerson: formData.contactPerson,
      email: formData.email,
      phone: formData.phone || undefined,
      gdprConsent,
    };

    onConsent?.(customer);
  };

  const allRequiredPurposes = CONSENT_PURPOSES.filter((p) => p.required).every(
    (p) => consentedPurposes.includes(p.id)
  );

  return (
    <Card className={cn("w-full max-w-2xl", className)}>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <CardTitle>Datenschutz & Einwilligung</CardTitle>
        </div>
        <CardDescription>
          Gemäß DSGVO benötigen wir Ihre Einwilligung zur Verarbeitung Ihrer
          personenbezogenen Daten
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-6">
          {/* Company Information */}
          <div className="space-y-4">
            <h3 className="font-semibold text-sm">Kontaktinformationen</h3>

            <div className="space-y-2">
              <Label htmlFor="companyName">
                Firmenname <span className="text-destructive">*</span>
              </Label>
              <Input
                id="companyName"
                value={formData.companyName}
                onChange={(e) =>
                  handleInputChange("companyName", e.target.value)
                }
                placeholder="Ihre Firma GmbH"
              />
              {errors.companyName && (
                <p className="text-sm text-destructive">{errors.companyName}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="contactPerson">
                Ansprechpartner <span className="text-destructive">*</span>
              </Label>
              <Input
                id="contactPerson"
                value={formData.contactPerson}
                onChange={(e) =>
                  handleInputChange("contactPerson", e.target.value)
                }
                placeholder="Max Mustermann"
              />
              {errors.contactPerson && (
                <p className="text-sm text-destructive">
                  {errors.contactPerson}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">
                E-Mail-Adresse <span className="text-destructive">*</span>
              </Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange("email", e.target.value)}
                placeholder="m.mustermann@firma.de"
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Telefonnummer (optional)</Label>
              <Input
                id="phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => handleInputChange("phone", e.target.value)}
                placeholder="+49 123 456789"
              />
            </div>
          </div>

          {/* GDPR Consent Purposes */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="font-semibold text-sm">
              Einwilligung zur Datenverarbeitung
            </h3>

            {CONSENT_PURPOSES.map((purpose) => (
              <div key={purpose.id} className="flex items-start space-x-3">
                <Checkbox
                  id={purpose.id}
                  checked={consentedPurposes.includes(purpose.id)}
                  onCheckedChange={(checked) =>
                    handlePurposeToggle(purpose.id, checked === true)
                  }
                />
                <div className="flex-1 space-y-1">
                  <Label
                    htmlFor={purpose.id}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    {purpose.label}
                    {purpose.required && (
                      <span className="text-destructive ml-1">*</span>
                    )}
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    {purpose.description}
                  </p>
                </div>
              </div>
            ))}

            {errors.consent && (
              <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
                <p className="text-sm text-destructive">{errors.consent}</p>
              </div>
            )}
          </div>

          {/* Privacy Policy Acknowledgment */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-start space-x-3">
              <Checkbox
                id="privacy-policy"
                checked={hasReadPrivacyPolicy}
                onCheckedChange={(checked) =>
                  setHasReadPrivacyPolicy(checked === true)
                }
              />
              <div className="flex-1 space-y-1">
                <Label
                  htmlFor="privacy-policy"
                  className="text-sm font-medium leading-none"
                >
                  Ich habe die{" "}
                  <a
                    href="/datenschutz"
                    target="_blank"
                    className="text-primary hover:underline"
                  >
                    Datenschutzerklärung
                  </a>{" "}
                  gelesen und verstanden{" "}
                  <span className="text-destructive">*</span>
                </Label>
              </div>
            </div>
            {errors.privacy && (
              <p className="text-sm text-destructive">{errors.privacy}</p>
            )}
          </div>

          {/* Information Box */}
          <div className="flex items-start gap-2 p-4 bg-muted rounded-lg">
            <FileText className="h-5 w-5 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div className="text-sm text-muted-foreground space-y-1">
              <p className="font-medium">Ihre Rechte:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Recht auf Auskunft über Ihre gespeicherten Daten</li>
                <li>Recht auf Berichtigung unrichtiger Daten</li>
                <li>Recht auf Löschung ("Recht auf Vergessenwerden")</li>
                <li>Recht auf Widerruf Ihrer Einwilligung jederzeit</li>
              </ul>
              <p className="pt-2">
                Kontakt:{" "}
                <a
                  href="mailto:datenschutz@aigentics.de"
                  className="text-primary hover:underline"
                >
                  datenschutz@aigentics.de
                </a>
              </p>
            </div>
          </div>
        </CardContent>

        <CardFooter className="border-t">
          <Button
            type="submit"
            className="w-full"
            disabled={!allRequiredPurposes || !hasReadPrivacyPolicy}
          >
            Einwilligung erteilen und fortfahren
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
