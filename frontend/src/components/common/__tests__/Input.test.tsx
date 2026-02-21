import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../../test/test-utils';
import { Input, Textarea, Select, Checkbox } from '../Input';

describe('Input', () => {
  describe('basic rendering', () => {
    it('renders with placeholder', () => {
      render(<Input placeholder="Enter text" />);
      expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
    });

    it('renders with label', () => {
      render(<Input label="Email" name="email" />);
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    it('shows required indicator when required', () => {
      render(<Input label="Email" name="email" required />);
      expect(screen.getByText('*')).toBeInTheDocument();
    });

    it('uses name as id when id is not provided', () => {
      render(<Input label="Email" name="email" />);
      const input = screen.getByLabelText('Email');
      expect(input).toHaveAttribute('id', 'email');
    });

    it('uses provided id over name', () => {
      render(<Input label="Email" name="email" id="custom-id" />);
      const input = screen.getByLabelText('Email');
      expect(input).toHaveAttribute('id', 'custom-id');
    });
  });

  describe('error and hint', () => {
    it('displays error message', () => {
      render(<Input name="email" error="Invalid email" />);
      expect(screen.getByText('Invalid email')).toBeInTheDocument();
    });

    it('sets aria-invalid when error is present', () => {
      render(<Input name="email" error="Invalid email" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('displays hint message', () => {
      render(<Input name="email" hint="We'll never share your email" />);
      expect(screen.getByText("We'll never share your email")).toBeInTheDocument();
    });

    it('hides hint when error is present', () => {
      render(<Input name="email" error="Invalid email" hint="Hint text" />);
      expect(screen.queryByText('Hint text')).not.toBeInTheDocument();
    });

    it('sets aria-describedby for error', () => {
      render(<Input name="email" error="Invalid email" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'email-error');
    });

    it('sets aria-describedby for hint', () => {
      render(<Input name="email" hint="Hint text" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'email-hint');
    });
  });

  describe('icons', () => {
    const TestIcon = () => <span data-testid="test-icon">Icon</span>;

    it('renders icon on the left by default', () => {
      render(<Input name="search" icon={<TestIcon />} />);
      expect(screen.getByTestId('test-icon')).toBeInTheDocument();
    });

    it('applies padding for left icon', () => {
      render(<Input name="search" icon={<TestIcon />} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('pl-10');
    });

    it('applies padding for right icon', () => {
      render(<Input name="search" icon={<TestIcon />} iconPosition="right" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('pr-10');
    });
  });

  describe('disabled state', () => {
    it('disables input when disabled', () => {
      render(<Input name="email" disabled />);
      expect(screen.getByRole('textbox')).toBeDisabled();
    });

    it('applies disabled styles', () => {
      render(<Input name="email" disabled />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('disabled:bg-gray-50');
    });
  });

  describe('fullWidth', () => {
    it('applies full width by default', () => {
      render(<Input name="email" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('w-full');
    });

    it('does not apply full width when fullWidth is false', () => {
      render(<Input name="email" fullWidth={false} />);
      const input = screen.getByRole('textbox');
      expect(input).not.toHaveClass('w-full');
    });
  });

  describe('onChange', () => {
    it('calls onChange when value changes', async () => {
      const handleChange = vi.fn();
      const { user } = render(<Input name="email" onChange={handleChange} />);

      await user.type(screen.getByRole('textbox'), 'test');

      expect(handleChange).toHaveBeenCalled();
    });
  });
});

describe('Textarea', () => {
  it('renders with placeholder', () => {
    render(<Textarea placeholder="Enter description" name="description" />);
    expect(screen.getByPlaceholderText('Enter description')).toBeInTheDocument();
  });

  it('renders with label', () => {
    render(<Textarea label="Description" name="description" />);
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
  });

  it('displays error message', () => {
    render(<Textarea name="description" error="Description is required" />);
    expect(screen.getByText('Description is required')).toBeInTheDocument();
  });

  it('sets aria-invalid when error is present', () => {
    render(<Textarea name="description" error="Error" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
  });

  it('displays hint message', () => {
    render(<Textarea name="description" hint="Max 500 characters" />);
    expect(screen.getByText('Max 500 characters')).toBeInTheDocument();
  });

  it('shows required indicator when required', () => {
    render(<Textarea label="Description" name="description" required />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('applies resize-y class', () => {
    render(<Textarea name="description" />);
    expect(screen.getByRole('textbox')).toHaveClass('resize-y');
  });
});

describe('Select', () => {
  const options = [
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
    { value: 'option3', label: 'Option 3' },
  ];

  it('renders with label', () => {
    render(<Select label="Choose option" name="option" options={options} />);
    expect(screen.getByLabelText('Choose option')).toBeInTheDocument();
  });

  it('renders all options', () => {
    render(<Select name="option" options={options} />);
    expect(screen.getByRole('option', { name: 'Option 1' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Option 2' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Option 3' })).toBeInTheDocument();
  });

  it('displays error message', () => {
    render(<Select name="option" options={options} error="Please select an option" />);
    expect(screen.getByText('Please select an option')).toBeInTheDocument();
  });

  it('sets aria-invalid when error is present', () => {
    render(<Select name="option" options={options} error="Error" />);
    expect(screen.getByRole('combobox')).toHaveAttribute('aria-invalid', 'true');
  });

  it('displays hint message', () => {
    render(<Select name="option" options={options} hint="Select your preference" />);
    expect(screen.getByText('Select your preference')).toBeInTheDocument();
  });

  it('shows required indicator when required', () => {
    render(<Select label="Option" name="option" options={options} required />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('calls onChange when selection changes', async () => {
    const handleChange = vi.fn();
    const { user } = render(
      <Select name="option" options={options} onChange={handleChange} />
    );

    await user.selectOptions(screen.getByRole('combobox'), 'option2');

    expect(handleChange).toHaveBeenCalled();
  });
});

describe('Checkbox', () => {
  it('renders with label', () => {
    render(<Checkbox label="Accept terms" name="terms" />);
    expect(screen.getByLabelText('Accept terms')).toBeInTheDocument();
  });

  it('renders with description', () => {
    render(
      <Checkbox
        label="Accept terms"
        name="terms"
        description="By checking this box, you agree to our terms"
      />
    );
    expect(screen.getByText('By checking this box, you agree to our terms')).toBeInTheDocument();
  });

  it('renders as checkbox type', () => {
    render(<Checkbox label="Accept terms" name="terms" />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('can be checked', async () => {
    const { user } = render(<Checkbox label="Accept terms" name="terms" />);
    const checkbox = screen.getByRole('checkbox');

    await user.click(checkbox);

    expect(checkbox).toBeChecked();
  });

  it('calls onChange when toggled', async () => {
    const handleChange = vi.fn();
    const { user } = render(
      <Checkbox label="Accept terms" name="terms" onChange={handleChange} />
    );

    await user.click(screen.getByRole('checkbox'));

    expect(handleChange).toHaveBeenCalled();
  });

  it('uses name as id when id is not provided', () => {
    render(<Checkbox label="Accept terms" name="terms" />);
    expect(screen.getByRole('checkbox')).toHaveAttribute('id', 'terms');
  });
});
