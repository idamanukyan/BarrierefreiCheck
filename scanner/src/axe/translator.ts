/**
 * Rule Translator
 *
 * Provides German translations for axe-core rules and maps them to BFSG references.
 */

import { createRequire } from 'module';
import { RuleTranslation } from './types.js';
import { logger } from '../utils/logger.js';

const require = createRequire(import.meta.url);

// Cache for translations
let translationsCache: Map<string, RuleTranslation> | null = null;

/**
 * Load translations from JSON file
 */
function loadTranslations(): Map<string, RuleTranslation> {
  if (translationsCache) {
    return translationsCache;
  }

  translationsCache = new Map();

  try {
    // Load translations file
    const translationsPath = new URL(
      '../../shared/translations/rules-de.json',
      import.meta.url
    ).pathname;
    const translationsData = require(translationsPath);

    if (translationsData.rules) {
      for (const [ruleId, rule] of Object.entries(translationsData.rules)) {
        const ruleData = rule as {
          rule_id: string;
          wcag_criteria: string[];
          wcag_level: 'A' | 'AA' | 'AAA';
          bfsg_reference: string;
          title_de: string;
          description_de: string;
          impact_de?: string;
          fix_de: string;
          code_example?: string;
        };

        translationsCache.set(ruleId, {
          ruleId: ruleData.rule_id,
          wcagCriteria: ruleData.wcag_criteria,
          wcagLevel: ruleData.wcag_level,
          bfsgReference: ruleData.bfsg_reference,
          titleDe: ruleData.title_de,
          descriptionDe: ruleData.description_de,
          impactDe: ruleData.impact_de || '',
          fixDe: ruleData.fix_de,
          codeExample: ruleData.code_example,
        });
      }
    }

    logger.info(`Loaded ${translationsCache.size} German rule translations`);
  } catch (error) {
    logger.warn('Could not load German translations, using fallback:', error);
  }

  return translationsCache;
}

/**
 * Get German translation for a rule
 */
export function getTranslation(ruleId: string): RuleTranslation | null {
  const translations = loadTranslations();
  return translations.get(ruleId) || null;
}

/**
 * Get all available translations
 */
export function getAllTranslations(): Map<string, RuleTranslation> {
  return loadTranslations();
}

/**
 * Extract WCAG criteria from axe-core tags
 */
export function extractWcagCriteria(tags: string[]): string[] {
  const criteria: string[] = [];
  const wcagPattern = /^wcag(\d)(\d)(\d)?$/;

  for (const tag of tags) {
    const match = tag.match(wcagPattern);
    if (match) {
      // Format: 1.4.3 for wcag143
      if (match[3]) {
        criteria.push(`${match[1]}.${match[2]}.${match[3]}`);
      } else {
        criteria.push(`${match[1]}.${match[2]}`);
      }
    }
  }

  return criteria;
}

/**
 * Extract WCAG level from axe-core tags
 */
export function extractWcagLevel(tags: string[]): 'A' | 'AA' | 'AAA' {
  for (const tag of tags) {
    if (tag === 'wcag2aaa' || tag === 'wcag21aaa' || tag === 'wcag22aaa') {
      return 'AAA';
    }
    if (tag === 'wcag2aa' || tag === 'wcag21aa' || tag === 'wcag22aa') {
      return 'AA';
    }
    if (tag === 'wcag2a' || tag === 'wcag21a' || tag === 'wcag22a') {
      return 'A';
    }
  }
  return 'A'; // Default to Level A
}

/**
 * Fallback translations for common rules (if JSON not available)
 */
export const FALLBACK_TRANSLATIONS: Record<string, Partial<RuleTranslation>> = {
  'color-contrast': {
    titleDe: 'Unzureichender Farbkontrast',
    descriptionDe:
      'Der Kontrast zwischen Vordergrund- und Hintergrundfarbe ist zu gering.',
    fixDe:
      'Erhöhen Sie den Kontrast auf mindestens 4.5:1 für normalen Text oder 3:1 für großen Text.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I',
    wcagCriteria: ['1.4.3'],
    wcagLevel: 'AA',
  },
  'image-alt': {
    titleDe: 'Bild ohne Alternativtext',
    descriptionDe: 'Bilder müssen einen Alternativtext (alt-Attribut) haben.',
    fixDe:
      'Fügen Sie dem img-Element ein beschreibendes alt-Attribut hinzu. Bei dekorativen Bildern: alt="".',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1a',
    wcagCriteria: ['1.1.1'],
    wcagLevel: 'A',
  },
  label: {
    titleDe: 'Formularfeld ohne Beschriftung',
    descriptionDe:
      'Formularfelder müssen eine programmatisch verknüpfte Beschriftung haben.',
    fixDe:
      'Verknüpfen Sie ein label-Element mit dem Formularfeld oder verwenden Sie aria-label.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1c',
    wcagCriteria: ['1.3.1', '3.3.2'],
    wcagLevel: 'A',
  },
  'link-name': {
    titleDe: 'Link ohne erkennbaren Text',
    descriptionDe:
      'Links müssen einen erkennbaren, beschreibenden Text haben.',
    fixDe:
      'Fügen Sie beschreibenden Linktext hinzu oder verwenden Sie aria-label für Icon-Links.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1b, 1c',
    wcagCriteria: ['2.4.4', '4.1.2'],
    wcagLevel: 'A',
  },
  'button-name': {
    titleDe: 'Schaltfläche ohne erkennbaren Namen',
    descriptionDe:
      'Schaltflächen müssen einen erkennbaren Namen haben.',
    fixDe:
      'Fügen Sie Text zur Schaltfläche hinzu oder verwenden Sie aria-label.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1d',
    wcagCriteria: ['4.1.2'],
    wcagLevel: 'A',
  },
  'html-has-lang': {
    titleDe: 'Fehlende Sprachangabe',
    descriptionDe:
      'Das html-Element muss ein lang-Attribut mit der Seitensprache haben.',
    fixDe: 'Fügen Sie dem html-Element das lang-Attribut hinzu: <html lang="de">',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1c',
    wcagCriteria: ['3.1.1'],
    wcagLevel: 'A',
  },
  'document-title': {
    titleDe: 'Fehlender oder leerer Seitentitel',
    descriptionDe: 'Jede Seite muss einen aussagekräftigen Titel haben.',
    fixDe: 'Fügen Sie einen beschreibenden, einzigartigen Titel hinzu.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1c',
    wcagCriteria: ['2.4.2'],
    wcagLevel: 'A',
  },
  'heading-order': {
    titleDe: 'Überschriftenhierarchie nicht eingehalten',
    descriptionDe:
      'Überschriften sollten in logischer Reihenfolge (h1, h2, h3...) verwendet werden.',
    fixDe:
      'Verwenden Sie Überschriften in der korrekten hierarchischen Reihenfolge ohne Ebenen zu überspringen.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1a',
    wcagCriteria: ['1.3.1'],
    wcagLevel: 'A',
  },
  'meta-viewport': {
    titleDe: 'Zoom im Viewport deaktiviert',
    descriptionDe:
      'Der Viewport sollte das Zoomen nicht deaktivieren (user-scalable=no).',
    fixDe:
      'Entfernen Sie user-scalable=no und maximum-scale < 5 aus dem meta viewport Tag.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1b',
    wcagCriteria: ['1.4.4'],
    wcagLevel: 'AA',
  },
  'aria-required-attr': {
    titleDe: 'Fehlende erforderliche ARIA-Attribute',
    descriptionDe:
      'ARIA-Rollen erfordern bestimmte Attribute, die fehlen.',
    fixDe:
      'Fügen Sie die erforderlichen ARIA-Attribute entsprechend der Rolle hinzu.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1d',
    wcagCriteria: ['4.1.2'],
    wcagLevel: 'A',
  },
  'aria-valid-attr-value': {
    titleDe: 'Ungültiger ARIA-Attributwert',
    descriptionDe: 'Ein ARIA-Attribut hat einen ungültigen Wert.',
    fixDe: 'Korrigieren Sie den ARIA-Attributwert gemäß der Spezifikation.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1d',
    wcagCriteria: ['4.1.2'],
    wcagLevel: 'A',
  },
  'duplicate-id': {
    titleDe: 'Doppelte ID',
    descriptionDe:
      'ID-Attribute müssen auf der Seite eindeutig sein.',
    fixDe: 'Stellen Sie sicher, dass jede ID nur einmal verwendet wird.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1d',
    wcagCriteria: ['4.1.1'],
    wcagLevel: 'A',
  },
  'frame-title': {
    titleDe: 'Frame ohne Titel',
    descriptionDe: 'Frames und iframes müssen ein title-Attribut haben.',
    fixDe:
      'Fügen Sie dem frame/iframe ein beschreibendes title-Attribut hinzu.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1c',
    wcagCriteria: ['2.4.1', '4.1.2'],
    wcagLevel: 'A',
  },
  'list': {
    titleDe: 'Ungültige Listenstruktur',
    descriptionDe:
      'Listenelemente (li) müssen in Listen (ul, ol) enthalten sein.',
    fixDe:
      'Stellen Sie sicher, dass li-Elemente direkte Kinder von ul oder ol sind.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1a',
    wcagCriteria: ['1.3.1'],
    wcagLevel: 'A',
  },
  'listitem': {
    titleDe: 'Listenelement außerhalb einer Liste',
    descriptionDe: 'li-Elemente müssen in ul oder ol enthalten sein.',
    fixDe: 'Verschieben Sie das li-Element in eine ul- oder ol-Liste.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1a',
    wcagCriteria: ['1.3.1'],
    wcagLevel: 'A',
  },
  'tabindex': {
    titleDe: 'Positiver tabindex-Wert',
    descriptionDe:
      'Vermeiden Sie positive tabindex-Werte, da sie die Fokusreihenfolge stören.',
    fixDe:
      'Entfernen Sie positive tabindex-Werte oder setzen Sie sie auf 0 oder -1.',
    bfsgReference: '§3 Abs. 2 Nr. 1 BFSG, Anlage 1 Abschnitt I Nr. 1b',
    wcagCriteria: ['2.4.3'],
    wcagLevel: 'A',
  },
};

/**
 * Get translation with fallback
 */
export function getTranslationWithFallback(
  ruleId: string
): Partial<RuleTranslation> | null {
  const translation = getTranslation(ruleId);
  if (translation) {
    return translation;
  }

  return FALLBACK_TRANSLATIONS[ruleId] || null;
}
