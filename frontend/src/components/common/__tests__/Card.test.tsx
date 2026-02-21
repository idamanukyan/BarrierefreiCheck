import { describe, it, expect } from 'vitest';
import { render, screen } from '../../../test/test-utils';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  describe('padding', () => {
    it('applies medium padding by default', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('p-4');
    });

    it('applies no padding when padding is none', () => {
      const { container } = render(<Card padding="none">Content</Card>);
      const card = container.firstChild;
      expect(card).not.toHaveClass('p-3', 'p-4', 'p-6');
    });

    it('applies small padding', () => {
      const { container } = render(<Card padding="sm">Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('p-3');
    });

    it('applies large padding', () => {
      const { container } = render(<Card padding="lg">Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('p-6');
    });
  });

  describe('shadow', () => {
    it('applies small shadow by default', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('shadow-sm');
    });

    it('applies no shadow when shadow is none', () => {
      const { container } = render(<Card shadow="none">Content</Card>);
      const card = container.firstChild;
      expect(card).not.toHaveClass('shadow-sm', 'shadow-md', 'shadow-lg');
    });

    it('applies medium shadow', () => {
      const { container } = render(<Card shadow="md">Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('shadow-md');
    });

    it('applies large shadow', () => {
      const { container } = render(<Card shadow="lg">Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('shadow-lg');
    });
  });

  describe('hover', () => {
    it('does not apply hover effect by default', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).not.toHaveClass('hover:shadow-md');
    });

    it('applies hover effect when hover is true', () => {
      const { container } = render(<Card hover>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('hover:shadow-md', 'transition-shadow', 'cursor-pointer');
    });
  });

  describe('custom className', () => {
    it('applies custom className', () => {
      const { container } = render(<Card className="custom-class">Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('custom-class');
    });
  });

  describe('base styles', () => {
    it('has white background', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('bg-white');
    });

    it('has rounded corners', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('rounded-lg');
    });

    it('has border', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('border', 'border-gray-200');
    });
  });
});

describe('CardHeader', () => {
  it('renders children', () => {
    render(<CardHeader>Header content</CardHeader>);
    expect(screen.getByText('Header content')).toBeInTheDocument();
  });

  it('renders action slot', () => {
    render(
      <CardHeader action={<button>Action</button>}>
        Header content
      </CardHeader>
    );
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });

  it('applies flex layout', () => {
    const { container } = render(<CardHeader>Header content</CardHeader>);
    const header = container.firstChild;
    expect(header).toHaveClass('flex', 'items-center', 'justify-between');
  });

  it('applies custom className', () => {
    const { container } = render(<CardHeader className="custom-header">Header content</CardHeader>);
    const header = container.firstChild;
    expect(header).toHaveClass('custom-header');
  });
});

describe('CardTitle', () => {
  it('renders children as heading', () => {
    render(<CardTitle>Card Title</CardTitle>);
    expect(screen.getByRole('heading', { name: 'Card Title' })).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    render(<CardTitle subtitle="Subtitle text">Card Title</CardTitle>);
    expect(screen.getByText('Subtitle text')).toBeInTheDocument();
  });

  it('applies heading styles', () => {
    render(<CardTitle>Card Title</CardTitle>);
    const heading = screen.getByRole('heading');
    expect(heading).toHaveClass('text-lg', 'font-semibold', 'text-gray-900');
  });

  it('applies subtitle styles', () => {
    render(<CardTitle subtitle="Subtitle text">Card Title</CardTitle>);
    const subtitle = screen.getByText('Subtitle text');
    expect(subtitle).toHaveClass('text-sm', 'text-gray-500');
  });

  it('applies custom className', () => {
    const { container } = render(<CardTitle className="custom-title">Card Title</CardTitle>);
    const titleContainer = container.firstChild;
    expect(titleContainer).toHaveClass('custom-title');
  });
});

describe('CardContent', () => {
  it('renders children', () => {
    render(<CardContent>Content</CardContent>);
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<CardContent className="custom-content">Content</CardContent>);
    const content = container.firstChild;
    expect(content).toHaveClass('custom-content');
  });
});

describe('CardFooter', () => {
  it('renders children', () => {
    render(<CardFooter>Footer content</CardFooter>);
    expect(screen.getByText('Footer content')).toBeInTheDocument();
  });

  it('applies border and spacing styles', () => {
    const { container } = render(<CardFooter>Footer content</CardFooter>);
    const footer = container.firstChild;
    expect(footer).toHaveClass('mt-4', 'pt-4', 'border-t', 'border-gray-100');
  });

  it('applies flex layout for actions', () => {
    const { container } = render(<CardFooter>Footer content</CardFooter>);
    const footer = container.firstChild;
    expect(footer).toHaveClass('flex', 'items-center', 'justify-end', 'gap-3');
  });

  it('applies custom className', () => {
    const { container } = render(<CardFooter className="custom-footer">Footer content</CardFooter>);
    const footer = container.firstChild;
    expect(footer).toHaveClass('custom-footer');
  });
});

describe('Card composition', () => {
  it('renders full card with all sub-components', () => {
    render(
      <Card>
        <CardHeader action={<button>Edit</button>}>
          <CardTitle subtitle="Subtitle">Title</CardTitle>
        </CardHeader>
        <CardContent>Main content</CardContent>
        <CardFooter>
          <button>Cancel</button>
          <button>Save</button>
        </CardFooter>
      </Card>
    );

    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument();
    expect(screen.getByText('Subtitle')).toBeInTheDocument();
    expect(screen.getByText('Main content')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });
});
