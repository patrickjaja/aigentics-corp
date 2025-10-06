"use client";

import * as React from "react";
import { Plus, Trash2, GripVertical, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { WorkPackage } from "@/types/api";

interface WorkPackageEditorProps {
  workPackages: WorkPackage[];
  onChange?: (workPackages: WorkPackage[]) => void;
  onSave?: (workPackages: WorkPackage[]) => Promise<void>;
  readonly?: boolean;
  className?: string;
}

export function WorkPackageEditor({
  workPackages: initialWorkPackages,
  onChange,
  onSave,
  readonly = false,
  className,
}: WorkPackageEditorProps) {
  const [workPackages, setWorkPackages] = React.useState<WorkPackage[]>(
    initialWorkPackages
  );
  const [isSaving, setIsSaving] = React.useState(false);
  const [hasChanges, setHasChanges] = React.useState(false);

  React.useEffect(() => {
    setWorkPackages(initialWorkPackages);
  }, [initialWorkPackages]);

  const handleWorkPackageChange = (
    index: number,
    field: keyof WorkPackage,
    value: unknown
  ) => {
    const updated = [...workPackages];
    updated[index] = { ...updated[index], [field]: value };

    // Recalculate total cost if hours or rate changed
    if (field === "estimatedHours" || field === "hourlyRate") {
      updated[index].totalCost =
        updated[index].estimatedHours * updated[index].hourlyRate;
    }

    setWorkPackages(updated);
    setHasChanges(true);
    onChange?.(updated);
  };

  const handleAddWorkPackage = () => {
    const newWorkPackage: WorkPackage = {
      id: `pkg-${Date.now()}`,
      title: "Neues Arbeitspaket",
      description: "",
      estimatedHours: 0,
      hourlyRate: 100,
      totalCost: 0,
      deliverables: [],
      technologies: [],
    };

    const updated = [...workPackages, newWorkPackage];
    setWorkPackages(updated);
    setHasChanges(true);
    onChange?.(updated);
  };

  const handleRemoveWorkPackage = (index: number) => {
    const updated = workPackages.filter((_, i) => i !== index);
    setWorkPackages(updated);
    setHasChanges(true);
    onChange?.(updated);
  };

  const handleAddDeliverable = (packageIndex: number, deliverable: string) => {
    if (!deliverable.trim()) return;

    const updated = [...workPackages];
    updated[packageIndex].deliverables = [
      ...updated[packageIndex].deliverables,
      deliverable.trim(),
    ];

    setWorkPackages(updated);
    setHasChanges(true);
    onChange?.(updated);
  };

  const handleRemoveDeliverable = (packageIndex: number, deliverableIndex: number) => {
    const updated = [...workPackages];
    updated[packageIndex].deliverables = updated[
      packageIndex
    ].deliverables.filter((_, i) => i !== deliverableIndex);

    setWorkPackages(updated);
    setHasChanges(true);
    onChange?.(updated);
  };

  const handleAddTechnology = (packageIndex: number, technology: string) => {
    if (!technology.trim()) return;

    const updated = [...workPackages];
    updated[packageIndex].technologies = [
      ...updated[packageIndex].technologies,
      technology.trim(),
    ];

    setWorkPackages(updated);
    setHasChanges(true);
    onChange?.(updated);
  };

  const handleRemoveTechnology = (packageIndex: number, technologyIndex: number) => {
    const updated = [...workPackages];
    updated[packageIndex].technologies = updated[
      packageIndex
    ].technologies.filter((_, i) => i !== technologyIndex);

    setWorkPackages(updated);
    setHasChanges(true);
    onChange?.(updated);
  };

  const handleSave = async () => {
    if (!onSave) return;

    setIsSaving(true);
    try {
      await onSave(workPackages);
      setHasChanges(false);
    } catch (error) {
      console.error("Failed to save work packages:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const totalHours = workPackages.reduce(
    (sum, pkg) => sum + pkg.estimatedHours,
    0
  );
  const totalCost = workPackages.reduce((sum, pkg) => sum + pkg.totalCost, 0);

  return (
    <div className={cn("space-y-6", className)}>
      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Arbeitspakete Übersicht</CardTitle>
          <CardDescription>
            {workPackages.length} Arbeitspaket(e) • {totalHours}h gesamt •{" "}
            {new Intl.NumberFormat("de-DE", {
              style: "currency",
              currency: "EUR",
            }).format(totalCost)}
          </CardDescription>
        </CardHeader>
        {!readonly && (
          <CardContent>
            <div className="flex gap-2">
              <Button onClick={handleAddWorkPackage} variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Arbeitspaket hinzufügen
              </Button>
              {hasChanges && (
                <Button onClick={handleSave} disabled={isSaving}>
                  {isSaving ? "Speichert..." : "Änderungen speichern"}
                </Button>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Work Packages */}
      <div className="space-y-4">
        {workPackages.map((pkg, index) => (
          <WorkPackageCard
            key={pkg.id}
            workPackage={pkg}
            index={index}
            readonly={readonly}
            onChange={(field, value) =>
              handleWorkPackageChange(index, field, value)
            }
            onRemove={() => handleRemoveWorkPackage(index)}
            onAddDeliverable={(deliverable) =>
              handleAddDeliverable(index, deliverable)
            }
            onRemoveDeliverable={(deliverableIndex) =>
              handleRemoveDeliverable(index, deliverableIndex)
            }
            onAddTechnology={(technology) =>
              handleAddTechnology(index, technology)
            }
            onRemoveTechnology={(technologyIndex) =>
              handleRemoveTechnology(index, technologyIndex)
            }
          />
        ))}
      </div>
    </div>
  );
}

interface WorkPackageCardProps {
  workPackage: WorkPackage;
  index: number;
  readonly?: boolean;
  onChange?: (field: keyof WorkPackage, value: unknown) => void;
  onRemove?: () => void;
  onAddDeliverable?: (deliverable: string) => void;
  onRemoveDeliverable?: (index: number) => void;
  onAddTechnology?: (technology: string) => void;
  onRemoveTechnology?: (index: number) => void;
}

function WorkPackageCard({
  workPackage,
  index,
  readonly = false,
  onChange,
  onRemove,
  onAddDeliverable,
  onRemoveDeliverable,
  onAddTechnology,
  onRemoveTechnology,
}: WorkPackageCardProps) {
  const [newDeliverable, setNewDeliverable] = React.useState("");
  const [newTechnology, setNewTechnology] = React.useState("");

  const handleAddDeliverable = () => {
    if (newDeliverable.trim() && onAddDeliverable) {
      onAddDeliverable(newDeliverable);
      setNewDeliverable("");
    }
  };

  const handleAddTechnology = () => {
    if (newTechnology.trim() && onAddTechnology) {
      onAddTechnology(newTechnology);
      setNewTechnology("");
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start gap-3">
          {!readonly && (
            <GripVertical className="h-5 w-5 text-muted-foreground mt-1 cursor-grab" />
          )}
          <div className="flex-1 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-2">
                <Label htmlFor={`title-${index}`}>
                  Arbeitspaket {index + 1} - Titel
                </Label>
                <Input
                  id={`title-${index}`}
                  value={workPackage.title}
                  onChange={(e) => onChange?.("title", e.target.value)}
                  disabled={readonly}
                  className="font-semibold"
                />
              </div>
              {!readonly && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onRemove}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor={`description-${index}`}>Beschreibung</Label>
              <Textarea
                id={`description-${index}`}
                value={workPackage.description}
                onChange={(e) => onChange?.("description", e.target.value)}
                disabled={readonly}
                rows={3}
              />
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Hours and Rate */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor={`hours-${index}`}>Geschätzte Stunden</Label>
            <Input
              id={`hours-${index}`}
              type="number"
              min="0"
              step="0.5"
              value={workPackage.estimatedHours}
              onChange={(e) =>
                onChange?.("estimatedHours", parseFloat(e.target.value) || 0)
              }
              disabled={readonly}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor={`rate-${index}`}>Stundensatz (EUR)</Label>
            <Input
              id={`rate-${index}`}
              type="number"
              min="0"
              step="5"
              value={workPackage.hourlyRate}
              onChange={(e) =>
                onChange?.("hourlyRate", parseFloat(e.target.value) || 0)
              }
              disabled={readonly}
            />
          </div>

          <div className="space-y-2">
            <Label>Gesamtkosten</Label>
            <div className="h-10 px-3 py-2 bg-muted rounded-md flex items-center justify-end font-semibold">
              {new Intl.NumberFormat("de-DE", {
                style: "currency",
                currency: "EUR",
              }).format(workPackage.totalCost)}
            </div>
          </div>
        </div>

        {/* Technologies */}
        <div className="space-y-2">
          <Label>Technologien</Label>
          <div className="flex flex-wrap gap-2 mb-2">
            {workPackage.technologies.map((tech, techIndex) => (
              <Badge key={techIndex} variant="secondary">
                {tech}
                {!readonly && (
                  <button
                    onClick={() => onRemoveTechnology?.(techIndex)}
                    className="ml-2 hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </Badge>
            ))}
          </div>
          {!readonly && (
            <div className="flex gap-2">
              <Input
                value={newTechnology}
                onChange={(e) => setNewTechnology(e.target.value)}
                placeholder="Neue Technologie..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddTechnology();
                  }
                }}
              />
              <Button
                onClick={handleAddTechnology}
                variant="outline"
                size="icon"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Deliverables */}
        <div className="space-y-2">
          <Label>Leistungen</Label>
          <ul className="space-y-2">
            {workPackage.deliverables.map((deliverable, deliverableIndex) => (
              <li
                key={deliverableIndex}
                className="flex items-start gap-2 text-sm"
              >
                <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="flex-1">{deliverable}</span>
                {!readonly && (
                  <button
                    onClick={() => onRemoveDeliverable?.(deliverableIndex)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </li>
            ))}
          </ul>
          {!readonly && (
            <div className="flex gap-2">
              <Input
                value={newDeliverable}
                onChange={(e) => setNewDeliverable(e.target.value)}
                placeholder="Neue Leistung..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddDeliverable();
                  }
                }}
              />
              <Button
                onClick={handleAddDeliverable}
                variant="outline"
                size="icon"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
