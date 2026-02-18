/**
 * Rule Translator Tests
 *
 * Tests for German translations and WCAG criteria extraction.
 */

import { describe, it, expect } from 'vitest';
import {
  extractWcagCriteria,
  extractWcagLevel,
  FALLBACK_TRANSLATIONS,
} from '../src/axe/translator.js';

describe('extractWcagCriteria', () => {
  it('should extract WCAG 2.x criteria from tags', () => {
    const tags = ['wcag143', 'cat.color', 'wcag2aa'];
    const criteria = extractWcagCriteria(tags);
    expect(criteria).toContain('1.4.3');
  });

  it('should extract multiple WCAG criteria', () => {
    const tags = ['wcag111', 'wcag143', 'wcag244'];
    const criteria = extractWcagCriteria(tags);
    expect(criteria).toHaveLength(3);
    expect(criteria).toContain('1.1.1');
    expect(criteria).toContain('1.4.3');
    expect(criteria).toContain('2.4.4');
  });

  it('should handle two-digit criteria', () => {
    const tags = ['wcag21'];
    const criteria = extractWcagCriteria(tags);
    expect(criteria).toContain('2.1');
  });

  it('should ignore non-WCAG tags', () => {
    const tags = ['cat.color', 'best-practice', 'ACT'];
    const criteria = extractWcagCriteria(tags);
    expect(criteria).toHaveLength(0);
  });

  it('should return empty array for empty tags', () => {
    const criteria = extractWcagCriteria([]);
    expect(criteria).toHaveLength(0);
  });
});

describe('extractWcagLevel', () => {
  describe('Level A', () => {
    it('should detect wcag2a', () => {
      expect(extractWcagLevel(['wcag2a'])).toBe('A');
    });

    it('should detect wcag21a', () => {
      expect(extractWcagLevel(['wcag21a'])).toBe('A');
    });

    it('should detect wcag22a', () => {
      expect(extractWcagLevel(['wcag22a'])).toBe('A');
    });
  });

  describe('Level AA', () => {
    it('should detect wcag2aa', () => {
      expect(extractWcagLevel(['wcag2aa'])).toBe('AA');
    });

    it('should detect wcag21aa', () => {
      expect(extractWcagLevel(['wcag21aa'])).toBe('AA');
    });

    it('should detect wcag22aa', () => {
      expect(extractWcagLevel(['wcag22aa'])).toBe('AA');
    });

    it('should prioritize AA over A when both present', () => {
      expect(extractWcagLevel(['wcag2a', 'wcag2aa'])).toBe('AA');
    });
  });

  describe('Level AAA', () => {
    it('should detect wcag2aaa', () => {
      expect(extractWcagLevel(['wcag2aaa'])).toBe('AAA');
    });

    it('should detect wcag21aaa', () => {
      expect(extractWcagLevel(['wcag21aaa'])).toBe('AAA');
    });

    it('should detect wcag22aaa', () => {
      expect(extractWcagLevel(['wcag22aaa'])).toBe('AAA');
    });

    it('should prioritize AAA over AA', () => {
      expect(extractWcagLevel(['wcag2aa', 'wcag2aaa'])).toBe('AAA');
    });
  });

  it('should default to Level A when no level tag present', () => {
    expect(extractWcagLevel(['cat.color', 'best-practice'])).toBe('A');
  });

  it('should default to Level A for empty tags', () => {
    expect(extractWcagLevel([])).toBe('A');
  });
});

describe('FALLBACK_TRANSLATIONS', () => {
  it('should have German translation for color-contrast rule', () => {
    const translation = FALLBACK_TRANSLATIONS['color-contrast'];
    expect(translation).toBeDefined();
    expect(translation.titleDe).toBeDefined();
    expect(translation.titleDe).toContain('Kontrast');
    expect(translation.wcagCriteria).toContain('1.4.3');
    expect(translation.wcagLevel).toBe('AA');
    expect(translation.bfsgReference).toContain('BFSG');
  });

  it('should have German translation for image-alt rule', () => {
    const translation = FALLBACK_TRANSLATIONS['image-alt'];
    expect(translation).toBeDefined();
    expect(translation.titleDe).toBeDefined();
    expect(translation.titleDe).toContain('Alternativtext');
    expect(translation.wcagCriteria).toContain('1.1.1');
    expect(translation.wcagLevel).toBe('A');
  });

  it('should have German translation for label rule', () => {
    const translation = FALLBACK_TRANSLATIONS['label'];
    expect(translation).toBeDefined();
    expect(translation.titleDe).toBeDefined();
    expect(translation.titleDe).toContain('Formularfeld');
  });

  it('should include BFSG references in all fallback translations', () => {
    for (const [ruleId, translation] of Object.entries(FALLBACK_TRANSLATIONS)) {
      expect(translation.bfsgReference).toBeDefined();
      expect(translation.bfsgReference).toContain('BFSG');
    }
  });

  it('should include fix instructions in German', () => {
    for (const [ruleId, translation] of Object.entries(FALLBACK_TRANSLATIONS)) {
      expect(translation.fixDe).toBeDefined();
      expect(translation.fixDe!.length).toBeGreaterThan(10);
    }
  });
});
