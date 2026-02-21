import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  withRouter?: boolean;
}

function Providers({ children }: { children: React.ReactNode }) {
  return <BrowserRouter>{children}</BrowserRouter>;
}

function customRender(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { withRouter = true, ...renderOptions } = options;

  const wrapper = withRouter ? Providers : undefined;

  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper, ...renderOptions }),
  };
}

// Re-export everything from testing-library
export * from '@testing-library/react';

// Override render with custom render
export { customRender as render };
