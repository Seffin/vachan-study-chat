import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from '../components/LoginPage';

// Mock fetch globally
global.fetch = jest.fn() as jest.Mock;

describe('LoginForm / LoginPage', () => {
  const mockOnLogin = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('test_renders_form: component mounts with inputs and submit button', () => {
    render(<LoginPage onLogin={mockOnLogin} />);
    
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('test_submits_credentials: valid input calls fetch with POST /api/auth/login', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'fake-token', token_type: 'bearer' }),
    });

    render(<LoginPage onLogin={mockOnLogin} />);
    
    await userEvent.type(screen.getByLabelText(/username/i), 'default_user');
    await userEvent.type(screen.getByLabelText(/password/i), 'Default@123');
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/login'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: 'default_user', password: 'Default@123' }),
        })
      );
    });
  });

  it('test_shows_success: login OK triggers success feedback and calls onLogin callback', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'fake-token', user: { username: 'default_user', user_id: '123' } }),
    });

    render(<LoginPage onLogin={mockOnLogin} />);
    
    await userEvent.type(screen.getByLabelText(/username/i), 'default_user');
    await userEvent.type(screen.getByLabelText(/password/i), 'Default@123');
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockOnLogin).toHaveBeenCalledWith('fake-token', expect.any(Object));
    });
  });

  it('test_shows_error: login fails displays error message', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Invalid username or password' }),
    });

    render(<LoginPage onLogin={mockOnLogin} />);
    
    await userEvent.type(screen.getByLabelText(/username/i), 'default_user');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword');
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid username or password')).toBeInTheDocument();
    });
  });

  it('test_loading_state: submit in progress disables button and shows spinner text', async () => {
    // Return a promise that doesn't resolve immediately
    let resolveFetch: any;
    const fetchPromise = new Promise(resolve => {
      resolveFetch = resolve;
    });
    (global.fetch as jest.Mock).mockReturnValueOnce(fetchPromise);

    render(<LoginPage onLogin={mockOnLogin} />);
    
    await userEvent.type(screen.getByLabelText(/username/i), 'default_user');
    await userEvent.type(screen.getByLabelText(/password/i), 'Default@123');
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Button text should change to Signing in... or be disabled
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();

    // Resolve the promise to clean up
    resolveFetch({
      ok: true,
      json: async () => ({ access_token: 'fake-token' }),
    });
  });

  it('test_empty_validation: submit with empty fields shows validation errors and prevents API call', async () => {
    render(<LoginPage onLogin={mockOnLogin} />);
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Should not call API
    expect(global.fetch).not.toHaveBeenCalled();
    // Should show error
    expect(screen.getByText(/username is required/i)).toBeInTheDocument();
  });
});
