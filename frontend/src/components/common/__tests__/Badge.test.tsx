import { describe, it, expect } from 'vitest';
import { render, screen } from '../../../test/test-utils';
import {
  Badge,
  ImpactBadge,
  WcagBadge,
  StatusBadge,
  ScoreBadge,
} from '../Badge';

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>Label</Badge>);
    expect(screen.getByText('Label')).toBeInTheDocument();
  });

  describe('variants', () => {
    it('applies default variant styles', () => {
      render(<Badge>Default</Badge>);
      expect(screen.getByText('Default')).toHaveClass('bg-gray-100', 'text-gray-800');
    });

    it('applies primary variant styles', () => {
      render(<Badge variant="primary">Primary</Badge>);
      expect(screen.getByText('Primary')).toHaveClass('bg-blue-100', 'text-blue-800');
    });

    it('applies success variant styles', () => {
      render(<Badge variant="success">Success</Badge>);
      expect(screen.getByText('Success')).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('applies warning variant styles', () => {
      render(<Badge variant="warning">Warning</Badge>);
      expect(screen.getByText('Warning')).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });

    it('applies danger variant styles', () => {
      render(<Badge variant="danger">Danger</Badge>);
      expect(screen.getByText('Danger')).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('applies info variant styles', () => {
      render(<Badge variant="info">Info</Badge>);
      expect(screen.getByText('Info')).toHaveClass('bg-purple-100', 'text-purple-800');
    });
  });

  describe('sizes', () => {
    it('applies medium size by default', () => {
      render(<Badge>Medium</Badge>);
      expect(screen.getByText('Medium')).toHaveClass('px-2.5', 'py-0.5', 'text-sm');
    });

    it('applies small size', () => {
      render(<Badge size="sm">Small</Badge>);
      expect(screen.getByText('Small')).toHaveClass('px-2', 'py-0.5', 'text-xs');
    });

    it('applies large size', () => {
      render(<Badge size="lg">Large</Badge>);
      expect(screen.getByText('Large')).toHaveClass('px-3', 'py-1');
    });
  });

  describe('dot indicator', () => {
    it('does not show dot by default', () => {
      render(<Badge>No dot</Badge>);
      const badge = screen.getByText('No dot');
      expect(badge.querySelector('.w-1\\.5')).not.toBeInTheDocument();
    });

    it('shows dot when dot prop is true', () => {
      render(<Badge dot>With dot</Badge>);
      const badge = screen.getByText('With dot');
      const dot = badge.querySelector('.rounded-full');
      expect(dot).toBeInTheDocument();
    });

    it('applies correct dot color for variant', () => {
      render(<Badge variant="success" dot>Success</Badge>);
      const badge = screen.getByText('Success');
      const dot = badge.querySelector('.rounded-full');
      expect(dot).toHaveClass('bg-green-500');
    });
  });

  describe('custom className', () => {
    it('applies custom className', () => {
      render(<Badge className="custom-class">Custom</Badge>);
      expect(screen.getByText('Custom')).toHaveClass('custom-class');
    });
  });

  describe('base styles', () => {
    it('has rounded-full class', () => {
      render(<Badge>Label</Badge>);
      expect(screen.getByText('Label')).toHaveClass('rounded-full');
    });

    it('has inline-flex display', () => {
      render(<Badge>Label</Badge>);
      expect(screen.getByText('Label')).toHaveClass('inline-flex', 'items-center');
    });
  });
});

describe('ImpactBadge', () => {
  it('renders critical impact with danger variant', () => {
    render(<ImpactBadge impact="critical" />);
    expect(screen.getByText('Kritisch')).toHaveClass('bg-red-100');
  });

  it('renders serious impact with warning variant', () => {
    render(<ImpactBadge impact="serious" />);
    expect(screen.getByText('Schwerwiegend')).toHaveClass('bg-yellow-100');
  });

  it('renders moderate impact with info variant', () => {
    render(<ImpactBadge impact="moderate" />);
    expect(screen.getByText('Mittel')).toHaveClass('bg-purple-100');
  });

  it('renders minor impact with default variant', () => {
    render(<ImpactBadge impact="minor" />);
    expect(screen.getByText('Gering')).toHaveClass('bg-gray-100');
  });

  it('shows impact level instead of label when showLabel is false', () => {
    render(<ImpactBadge impact="critical" showLabel={false} />);
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.queryByText('Kritisch')).not.toBeInTheDocument();
  });

  it('applies size prop', () => {
    render(<ImpactBadge impact="critical" size="sm" />);
    expect(screen.getByText('Kritisch')).toHaveClass('text-xs');
  });

  it('shows dot indicator', () => {
    render(<ImpactBadge impact="critical" />);
    const badge = screen.getByText('Kritisch');
    expect(badge.querySelector('.rounded-full')).toBeInTheDocument();
  });
});

describe('WcagBadge', () => {
  it('renders level A with success variant', () => {
    render(<WcagBadge level="A" />);
    expect(screen.getByText('WCAG A')).toHaveClass('bg-green-100');
  });

  it('renders level AA with primary variant', () => {
    render(<WcagBadge level="AA" />);
    expect(screen.getByText('WCAG AA')).toHaveClass('bg-blue-100');
  });

  it('renders level AAA with info variant', () => {
    render(<WcagBadge level="AAA" />);
    expect(screen.getByText('WCAG AAA')).toHaveClass('bg-purple-100');
  });

  it('applies size prop', () => {
    render(<WcagBadge level="AA" size="lg" />);
    expect(screen.getByText('WCAG AA')).toHaveClass('px-3', 'py-1');
  });
});

describe('StatusBadge', () => {
  it('renders queued status', () => {
    render(<StatusBadge status="queued" />);
    expect(screen.getByText('In Warteschlange')).toHaveClass('bg-gray-100');
  });

  it('renders crawling status', () => {
    render(<StatusBadge status="crawling" />);
    expect(screen.getByText('Crawling')).toHaveClass('bg-purple-100');
  });

  it('renders scanning status', () => {
    render(<StatusBadge status="scanning" />);
    expect(screen.getByText('Scanning')).toHaveClass('bg-blue-100');
  });

  it('renders processing status', () => {
    render(<StatusBadge status="processing" />);
    expect(screen.getByText('Verarbeitung')).toHaveClass('bg-purple-100');
  });

  it('renders completed status', () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText('Abgeschlossen')).toHaveClass('bg-green-100');
  });

  it('renders failed status', () => {
    render(<StatusBadge status="failed" />);
    expect(screen.getByText('Fehlgeschlagen')).toHaveClass('bg-red-100');
  });

  it('renders cancelled status', () => {
    render(<StatusBadge status="cancelled" />);
    expect(screen.getByText('Abgebrochen')).toHaveClass('bg-yellow-100');
  });

  it('applies size prop', () => {
    render(<StatusBadge status="completed" size="sm" />);
    expect(screen.getByText('Abgeschlossen')).toHaveClass('text-xs');
  });

  it('shows dot indicator', () => {
    render(<StatusBadge status="completed" />);
    const badge = screen.getByText('Abgeschlossen');
    expect(badge.querySelector('.rounded-full')).toBeInTheDocument();
  });
});

describe('ScoreBadge', () => {
  it('renders score with percentage', () => {
    render(<ScoreBadge score={85} />);
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('applies success variant for score >= 90', () => {
    render(<ScoreBadge score={95} />);
    expect(screen.getByText('95%')).toHaveClass('bg-green-100');
  });

  it('applies success variant for score = 90', () => {
    render(<ScoreBadge score={90} />);
    expect(screen.getByText('90%')).toHaveClass('bg-green-100');
  });

  it('applies primary variant for score >= 70 and < 90', () => {
    render(<ScoreBadge score={75} />);
    expect(screen.getByText('75%')).toHaveClass('bg-blue-100');
  });

  it('applies warning variant for score >= 50 and < 70', () => {
    render(<ScoreBadge score={55} />);
    expect(screen.getByText('55%')).toHaveClass('bg-yellow-100');
  });

  it('applies danger variant for score < 50', () => {
    render(<ScoreBadge score={30} />);
    expect(screen.getByText('30%')).toHaveClass('bg-red-100');
  });

  it('applies size prop', () => {
    render(<ScoreBadge score={85} size="lg" />);
    expect(screen.getByText('85%')).toHaveClass('px-3', 'py-1');
  });

  it('handles edge case score = 0', () => {
    render(<ScoreBadge score={0} />);
    expect(screen.getByText('0%')).toHaveClass('bg-red-100');
  });

  it('handles edge case score = 100', () => {
    render(<ScoreBadge score={100} />);
    expect(screen.getByText('100%')).toHaveClass('bg-green-100');
  });
});
