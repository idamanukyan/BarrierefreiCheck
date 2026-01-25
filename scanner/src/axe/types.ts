/**
 * Type definitions for axe-core results and our custom structures
 */

// axe-core result types
export interface AxeNodeResult {
  html: string;
  target: string[];
  failureSummary?: string;
  any: AxeCheckResult[];
  all: AxeCheckResult[];
  none: AxeCheckResult[];
}

export interface AxeCheckResult {
  id: string;
  data: unknown;
  relatedNodes: AxeRelatedNode[];
  impact?: ImpactLevel;
  message: string;
}

export interface AxeRelatedNode {
  html: string;
  target: string[];
}

export interface AxeRuleResult {
  id: string;
  impact?: ImpactLevel;
  tags: string[];
  description: string;
  help: string;
  helpUrl: string;
  nodes: AxeNodeResult[];
}

export interface AxeResults {
  inapplicable: AxeRuleResult[];
  incomplete: AxeRuleResult[];
  passes: AxeRuleResult[];
  violations: AxeRuleResult[];
  timestamp: string;
  url: string;
  toolOptions?: {
    runOnly?: {
      type: string;
      values: string[];
    };
  };
}

// Impact levels
export type ImpactLevel = 'minor' | 'moderate' | 'serious' | 'critical';

// Our custom types for processed results
export interface AccessibilityIssue {
  id: string;
  ruleId: string;
  impact: ImpactLevel;
  wcagCriteria: string[];
  wcagLevel: 'A' | 'AA' | 'AAA';
  bfsgReference?: string;
  titleDe: string;
  descriptionDe: string;
  fixSuggestionDe: string;
  helpUrl: string;
  element: {
    selector: string;
    html: string;
    xpath?: string;
  };
  pageUrl: string;
  screenshotPath?: string;
  createdAt: Date;
}

export interface PageScanResult {
  url: string;
  title: string;
  scanTime: number;
  score: number;
  issues: AccessibilityIssue[];
  passedRules: number;
  failedRules: number;
  incompleteRules: number;
  inapplicableRules: number;
  timestamp: Date;
  error?: string;
}

export interface ScanSummary {
  scanId: string;
  baseUrl: string;
  totalPages: number;
  totalIssues: number;
  issuesByImpact: {
    critical: number;
    serious: number;
    moderate: number;
    minor: number;
  };
  issuesByWcagLevel: {
    A: number;
    AA: number;
    AAA: number;
  };
  overallScore: number;
  scanDuration: number;
  completedAt: Date;
}

// WCAG tag to criteria mapping
export interface WcagMapping {
  tag: string;
  criterion: string;
  level: 'A' | 'AA' | 'AAA';
  title: string;
}

// German translation for a rule
export interface RuleTranslation {
  ruleId: string;
  wcagCriteria: string[];
  wcagLevel: 'A' | 'AA' | 'AAA';
  bfsgReference: string;
  titleDe: string;
  descriptionDe: string;
  impactDe: string;
  fixDe: string;
  codeExample?: string;
}
