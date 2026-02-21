import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../../test/test-utils';
import { Alert } from '../Alert';

describe('Alert', () => {
  it('renders children', () => {
    render(<Alert>Alert message</Alert>);
    expect(screen.getByText('Alert message')).toBeInTheDocument();
  });

  it('has role="alert" for accessibility', () => {
    render(<Alert>Alert message</Alert>);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  describe('variants', () => {
    it('applies info variant styles by default', () => {
      render(<Alert>Info alert</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-blue-50', 'border-blue-200', 'text-blue-800');
    });

    it('applies success variant styles', () => {
      render(<Alert variant="success">Success alert</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-green-50', 'border-green-200', 'text-green-800');
    });

    it('applies warning variant styles', () => {
      render(<Alert variant="warning">Warning alert</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-yellow-50', 'border-yellow-200', 'text-yellow-800');
    });

    it('applies error variant styles', () => {
      render(<Alert variant="error">Error alert</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-red-50', 'border-red-200', 'text-red-800');
    });
  });

  describe('title', () => {
    it('renders title when provided', () => {
      render(<Alert title="Alert Title">Alert message</Alert>);
      expect(screen.getByText('Alert Title')).toBeInTheDocument();
    });

    it('applies title styling', () => {
      render(<Alert title="Alert Title">Alert message</Alert>);
      const title = screen.getByText('Alert Title');
      expect(title).toHaveClass('text-sm', 'font-medium');
    });

    it('renders as h3 heading', () => {
      render(<Alert title="Alert Title">Alert message</Alert>);
      expect(screen.getByRole('heading', { name: 'Alert Title', level: 3 })).toBeInTheDocument();
    });
  });

  describe('icons', () => {
    it('renders default icon for info variant', () => {
      render(<Alert variant="info">Info</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert.querySelector('svg')).toBeInTheDocument();
    });

    it('renders default icon for success variant', () => {
      render(<Alert variant="success">Success</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert.querySelector('svg')).toBeInTheDocument();
    });

    it('renders default icon for warning variant', () => {
      render(<Alert variant="warning">Warning</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert.querySelector('svg')).toBeInTheDocument();
    });

    it('renders default icon for error variant', () => {
      render(<Alert variant="error">Error</Alert>);
      const alert = screen.getByRole('alert');
      expect(alert.querySelector('svg')).toBeInTheDocument();
    });

    it('renders custom icon when provided', () => {
      const CustomIcon = () => <span data-testid="custom-icon">Custom</span>;
      render(<Alert icon={<CustomIcon />}>Alert</Alert>);
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });
  });

  describe('dismissible', () => {
    it('does not show close button by default', () => {
      render(<Alert>Alert message</Alert>);
      expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument();
    });

    it('shows close button when dismissible and onDismiss provided', () => {
      render(<Alert dismissible onDismiss={() => {}}>Alert message</Alert>);
      expect(screen.getByRole('button', { name: 'Dismiss' })).toBeInTheDocument();
    });

    it('does not show close button when dismissible but no onDismiss', () => {
      render(<Alert dismissible>Alert message</Alert>);
      expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument();
    });

    it('calls onDismiss when close button is clicked', async () => {
      const handleDismiss = vi.fn();
      const { user } = render(
        <Alert dismissible onDismiss={handleDismiss}>Alert message</Alert>
      );

      await user.click(screen.getByRole('button', { name: 'Dismiss' }));

      expect(handleDismiss).toHaveBeenCalledTimes(1);
    });

    it('applies correct focus ring color for info variant', () => {
      render(<Alert variant="info" dismissible onDismiss={() => {}}>Alert</Alert>);
      const button = screen.getByRole('button', { name: 'Dismiss' });
      expect(button).toHaveClass('focus:ring-blue-500');
    });

    it('applies correct focus ring color for success variant', () => {
      render(<Alert variant="success" dismissible onDismiss={() => {}}>Alert</Alert>);
      const button = screen.getByRole('button', { name: 'Dismiss' });
      expect(button).toHaveClass('focus:ring-green-500');
    });

    it('applies correct focus ring color for warning variant', () => {
      render(<Alert variant="warning" dismissible onDismiss={() => {}}>Alert</Alert>);
      const button = screen.getByRole('button', { name: 'Dismiss' });
      expect(button).toHaveClass('focus:ring-yellow-500');
    });

    it('applies correct focus ring color for error variant', () => {
      render(<Alert variant="error" dismissible onDismiss={() => {}}>Alert</Alert>);
      const button = screen.getByRole('button', { name: 'Dismiss' });
      expect(button).toHaveClass('focus:ring-red-500');
    });
  });

  describe('custom className', () => {
    it('applies custom className', () => {
      render(<Alert className="custom-class">Alert</Alert>);
      expect(screen.getByRole('alert')).toHaveClass('custom-class');
    });
  });

  describe('base styles', () => {
    it('has rounded corners', () => {
      render(<Alert>Alert</Alert>);
      expect(screen.getByRole('alert')).toHaveClass('rounded-lg');
    });

    it('has border', () => {
      render(<Alert>Alert</Alert>);
      expect(screen.getByRole('alert')).toHaveClass('border');
    });

    it('has padding', () => {
      render(<Alert>Alert</Alert>);
      expect(screen.getByRole('alert')).toHaveClass('p-4');
    });
  });

  describe('complex content', () => {
    it('renders complex children content', () => {
      render(
        <Alert title="Error" variant="error">
          <p>Something went wrong.</p>
          <ul>
            <li>Error 1</li>
            <li>Error 2</li>
          </ul>
        </Alert>
      );

      expect(screen.getByText('Something went wrong.')).toBeInTheDocument();
      expect(screen.getByText('Error 1')).toBeInTheDocument();
      expect(screen.getByText('Error 2')).toBeInTheDocument();
    });
  });
});
