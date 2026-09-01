/**
 * TypeScript contract interfaces for Golden Evidence and Manifests.
 * Aligned with specs/golden-evidence.schema.json.
 */

export type EvidenceLevel = "G0" | "G1" | "G2" | "G3" | "G4" | "G5" | "G6" | "G7";

export type ComparatorKind =
  | "exact"
  | "absolute"
  | "relative"
  | "absolute_relative"
  | "set_equivalent"
  | "sign_indeterminate"
  | "expected_failure";

export interface ComparisonRule {
  path: string;
  comparator?: ComparatorKind;
  absTolerance?: number;
  relTolerance?: number;
  required?: boolean;
}

export interface DatasetEntry {
  path: string;
  sha256: string;
  rowCount?: number | null;
  columnCount?: number | null;
}

export interface ReferenceEngine {
  engine: string;
  version?: string;
  command?: string | null;
  containerDigest?: string | null;
  normalizedOutput: string;
}

export interface CaseIdentity {
  goldenCaseId: string;
  capabilityId: string;
  caseVersion?: string;
  status?: "draft" | "frozen" | "quarantined";
}

export interface CaseManifest {
  schemaVersion: number;
  identity: CaseIdentity;
  dataset: DatasetEntry[];
  specPath: string;
  estimandPath?: string | null;
  primaryReference: ReferenceEngine;
  secondaryReference?: ReferenceEngine | null;
  comparisonRules?: ComparisonRule[];
  expectedOutputPath: string;
  evidenceLevels?: EvidenceLevel[];
}

export interface CapabilityBundle {
  schemaVersion: number;
  capabilityId: string;
  methodFamily: string;
  cases: string[];
}
