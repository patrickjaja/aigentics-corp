/**
 * Unit tests for LanguageSelector component
 * Tests language selection, persistence, and multi-language support
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LanguageSelector, useLanguage } from '@/components/common/LanguageSelector';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    clear: () => {
      store = {};
    },
    removeItem: (key: string) => {
      delete store[key];
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('LanguageSelector', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('Dropdown Variant', () => {
    it('renders with default language (German)', () => {
      render(<LanguageSelector />);

      expect(screen.getByText('Deutsch')).toBeInTheDocument();
    });

    it('renders with custom language', () => {
      render(<LanguageSelector value="en" />);

      expect(screen.getByText('English')).toBeInTheDocument();
    });

    it('calls onValueChange when language is changed', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();

      render(<LanguageSelector value="de" onValueChange={handleChange} />);

      // Open dropdown
      const trigger = screen.getByRole('combobox');
      await user.click(trigger);

      // Select English
      const englishOption = screen.getByText('English');
      await user.click(englishOption);

      expect(handleChange).toHaveBeenCalledWith('en');
    });

    it('persists language selection to localStorage', async () => {
      const user = userEvent.setup();

      render(<LanguageSelector value="de" />);

      // Open dropdown and select French
      const trigger = screen.getByRole('combobox');
      await user.click(trigger);

      const frenchOption = screen.getByText('Français');
      await user.click(frenchOption);

      expect(localStorage.getItem('preferred-language')).toBe('fr');
    });

    it('updates when value prop changes', () => {
      const { rerender } = render(<LanguageSelector value="de" />);
      expect(screen.getByText('Deutsch')).toBeInTheDocument();

      rerender(<LanguageSelector value="en" />);
      expect(screen.getByText('English')).toBeInTheDocument();
    });

    it('displays all EU languages in dropdown', async () => {
      const user = userEvent.setup();

      render(<LanguageSelector />);

      // Open dropdown
      const trigger = screen.getByRole('combobox');
      await user.click(trigger);

      // Check for a few key languages
      expect(screen.getByText('Deutsch')).toBeInTheDocument();
      expect(screen.getByText('English')).toBeInTheDocument();
      expect(screen.getByText('Français')).toBeInTheDocument();
      expect(screen.getByText('Español')).toBeInTheDocument();
      expect(screen.getByText('Italiano')).toBeInTheDocument();
      expect(screen.getByText('Polski')).toBeInTheDocument();
    });

    it('shows check mark for selected language', async () => {
      const user = userEvent.setup();

      render(<LanguageSelector value="de" />);

      const trigger = screen.getByRole('combobox');
      await user.click(trigger);

      // Check that selected language has check mark icon
      const checkMark = screen.getAllByRole('img', { hidden: true });
      expect(checkMark.length).toBeGreaterThan(0);
    });

    it('applies custom className', () => {
      const { container } = render(<LanguageSelector className="custom-class" />);

      const selectTrigger = container.querySelector('.custom-class');
      expect(selectTrigger).toBeInTheDocument();
    });
  });

  describe('Compact Variant', () => {
    it('renders in compact mode', () => {
      render(<LanguageSelector variant="compact" value="de" />);

      expect(screen.getByText('DE')).toBeInTheDocument();
    });

    it('toggles between German and English on click', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();

      render(<LanguageSelector variant="compact" value="de" onValueChange={handleChange} />);

      const button = screen.getByRole('button');

      // Click to switch to English
      await user.click(button);
      expect(handleChange).toHaveBeenCalledWith('en');

      // Rerender with new value
      render(<LanguageSelector variant="compact" value="en" onValueChange={handleChange} />);

      // Click to switch back to German
      await user.click(screen.getByRole('button'));
      expect(handleChange).toHaveBeenLastCalledWith('de');
    });

    it('displays language icon in compact mode', () => {
      render(<LanguageSelector variant="compact" />);

      const icon = screen.getByRole('button').querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles invalid language code gracefully', () => {
      render(<LanguageSelector value="invalid" />);

      // Should fallback to English
      expect(screen.getByText('English')).toBeInTheDocument();
    });

    it('handles undefined onValueChange prop', async () => {
      const user = userEvent.setup();

      // Should not throw error
      render(<LanguageSelector value="de" />);

      const trigger = screen.getByRole('combobox');
      await user.click(trigger);

      const englishOption = screen.getByText('English');
      await user.click(englishOption);

      // Should persist despite no callback
      expect(localStorage.getItem('preferred-language')).toBe('en');
    });
  });
});

describe('useLanguage Hook', () => {
  beforeEach(() => {
    localStorage.clear();

    // Reset navigator.language
    Object.defineProperty(window.navigator, 'language', {
      writable: true,
      value: 'de-DE',
    });
  });

  it('returns default language', () => {
    const TestComponent = () => {
      const { language } = useLanguage();
      return <div data-testid="language">{language}</div>;
    };

    render(<TestComponent />);

    waitFor(() => {
      expect(screen.getByTestId('language')).toHaveTextContent('de');
    });
  });

  it('loads language from localStorage', () => {
    localStorage.setItem('preferred-language', 'fr');

    const TestComponent = () => {
      const { language } = useLanguage();
      return <div data-testid="language">{language}</div>;
    };

    render(<TestComponent />);

    waitFor(() => {
      expect(screen.getByTestId('language')).toHaveTextContent('fr');
    });
  });

  it('fallback to browser language if not in localStorage', () => {
    Object.defineProperty(window.navigator, 'language', {
      writable: true,
      value: 'es-ES',
    });

    const TestComponent = () => {
      const { language } = useLanguage();
      return <div data-testid="language">{language}</div>;
    };

    render(<TestComponent />);

    waitFor(() => {
      expect(screen.getByTestId('language')).toHaveTextContent('es');
    });
  });

  it('setLanguage updates the language', async () => {
    const TestComponent = () => {
      const { language, setLanguage } = useLanguage();

      return (
        <div>
          <div data-testid="language">{language}</div>
          <button onClick={() => setLanguage('it')}>Change</button>
        </div>
      );
    };

    const user = userEvent.setup();
    render(<TestComponent />);

    const button = screen.getByText('Change');
    await user.click(button);

    waitFor(() => {
      expect(screen.getByTestId('language')).toHaveTextContent('it');
    });
  });
});
