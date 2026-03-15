import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('App', () => {
  it('renders Single and Batch tabs', () => {
    render(<App />);
    expect(screen.getByRole('button', { name: /single/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /batch/i })).toBeInTheDocument();
  });

  it('renders header with Morocco', () => {
    render(<App />);
    expect(screen.getByText(/Morocco/i)).toBeInTheDocument();
  });
});
