/**
 * Unit tests for ConsentForm component
 * Tests GDPR compliance, form validation, and consent handling
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConsentForm } from '@/components/customer/ConsentForm';
import type { Customer } from '@/types/api';

describe('ConsentForm', () => {
  describe('Rendering', () => {
    it('renders consent form with title and description', () => {
      render(<ConsentForm />);

      expect(screen.getByText('Datenschutz & Einwilligung')).toBeInTheDocument();
      expect(
        screen.getByText(/Gemäß DSGVO benötigen wir Ihre Einwilligung/i)
      ).toBeInTheDocument();
    });

    it('renders all required form fields', () => {
      render(<ConsentForm />);

      expect(screen.getByLabelText(/Firmenname/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Ansprechpartner/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/E-Mail-Adresse/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Telefonnummer/i)).toBeInTheDocument();
    });

    it('renders all consent purposes', () => {
      render(<ConsentForm />);

      expect(screen.getByText('Angebotserstellung')).toBeInTheDocument();
      expect(screen.getByText('Datenspeicherung')).toBeInTheDocument();
      expect(screen.getByText('E-Mail-Kommunikation')).toBeInTheDocument();
      expect(screen.getByText('Marketing (optional)')).toBeInTheDocument();
    });

    it('renders privacy policy acknowledgment', () => {
      render(<ConsentForm />);

      expect(screen.getByText(/Ich habe die/i)).toBeInTheDocument();
      expect(screen.getByText(/Datenschutzerklärung/i)).toBeInTheDocument();
    });

    it('renders submit button disabled initially', () => {
      render(<ConsentForm />);

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      expect(submitButton).toBeDisabled();
    });

    it('renders GDPR rights information', () => {
      render(<ConsentForm />);

      expect(screen.getByText(/Ihre Rechte:/i)).toBeInTheDocument();
      expect(screen.getByText(/Recht auf Auskunft/i)).toBeInTheDocument();
      expect(screen.getByText(/Recht auf Löschung/i)).toBeInTheDocument();
      expect(screen.getByText(/Recht auf Widerruf/i)).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('validates required company name', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      // Try to submit without company name
      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });

      // Enable button by checking all required consents
      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes) {
        await user.click(checkbox);
      }

      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Firmenname ist erforderlich')).toBeInTheDocument();
      });
    });

    it('validates required contact person', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      // Fill company name but not contact person
      await user.type(screen.getByLabelText(/Firmenname/i), 'Test GmbH');

      // Check all consents
      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes) {
        await user.click(checkbox);
      }

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('Ansprechpartner ist erforderlich')
        ).toBeInTheDocument();
      });
    });

    it('validates email format', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      // Fill with invalid email
      await user.type(screen.getByLabelText(/E-Mail-Adresse/i), 'invalid-email');

      // Check all consents
      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes) {
        await user.click(checkbox);
      }

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Ungültige E-Mail-Adresse')).toBeInTheDocument();
      });
    });

    it('validates required consent purposes', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      // Fill all fields but no consents
      await user.type(screen.getByLabelText(/Firmenname/i), 'Test GmbH');
      await user.type(screen.getByLabelText(/Ansprechpartner/i), 'Max Mustermann');
      await user.type(
        screen.getByLabelText(/E-Mail-Adresse/i),
        'max@test.de'
      );

      // Only check privacy policy, not purposes
      const privacyCheckbox = screen.getByLabelText(/Ich habe die/i);
      await user.click(privacyCheckbox);

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Bitte stimmen Sie allen erforderlichen/i)
        ).toBeInTheDocument();
      });
    });

    it('validates privacy policy acknowledgment', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      // Fill all fields and check required purposes but not privacy
      await user.type(screen.getByLabelText(/Firmenname/i), 'Test GmbH');
      await user.type(screen.getByLabelText(/Ansprechpartner/i), 'Max Mustermann');
      await user.type(
        screen.getByLabelText(/E-Mail-Adresse/i),
        'max@test.de'
      );

      // Check only required purposes (not marketing)
      const purposes = ['offer_generation', 'data_storage', 'email_communication'];
      for (const purposeId of purposes) {
        const checkbox = screen.getByLabelText(
          new RegExp(purposeId.replace(/_/g, ' '), 'i')
        );
        await user.click(checkbox);
      }

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });

      // Button should still be disabled without privacy policy check
      expect(submitButton).toBeDisabled();
    });

    it('clears error when user starts typing', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      // Check all consents to enable submit
      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes) {
        await user.click(checkbox);
      }

      // Submit to trigger errors
      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      // Wait for error
      await waitFor(() => {
        expect(screen.getByText('Firmenname ist erforderlich')).toBeInTheDocument();
      });

      // Start typing
      await user.type(screen.getByLabelText(/Firmenname/i), 'T');

      // Error should be cleared
      await waitFor(() => {
        expect(
          screen.queryByText('Firmenname ist erforderlich')
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('submits form with valid data', async () => {
      const user = userEvent.setup();
      const handleConsent = jest.fn();

      render(<ConsentForm onConsent={handleConsent} />);

      // Fill all required fields
      await user.type(screen.getByLabelText(/Firmenname/i), 'Test GmbH');
      await user.type(screen.getByLabelText(/Ansprechpartner/i), 'Max Mustermann');
      await user.type(
        screen.getByLabelText(/E-Mail-Adresse/i),
        'max@test.de'
      );
      await user.type(screen.getByLabelText(/Telefonnummer/i), '+49 123 456789');

      // Check all required purposes
      const offerCheckbox = screen.getByLabelText(/Angebotserstellung/i);
      const storageCheckbox = screen.getByLabelText(/Datenspeicherung/i);
      const emailCheckbox = screen.getByLabelText(/E-Mail-Kommunikation/i);
      const privacyCheckbox = screen.getByLabelText(/Ich habe die/i);

      await user.click(offerCheckbox);
      await user.click(storageCheckbox);
      await user.click(emailCheckbox);
      await user.click(privacyCheckbox);

      // Submit form
      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      // Check that callback was called with correct data
      await waitFor(() => {
        expect(handleConsent).toHaveBeenCalledWith(
          expect.objectContaining({
            companyName: 'Test GmbH',
            contactPerson: 'Max Mustermann',
            email: 'max@test.de',
            phone: '+49 123 456789',
            gdprConsent: expect.objectContaining({
              given: true,
              purposes: expect.arrayContaining([
                'offer_generation',
                'data_storage',
                'email_communication',
              ]),
              consentTextVersion: '1.0',
            }),
          })
        );
      });
    });

    it('submits form without optional phone number', async () => {
      const user = userEvent.setup();
      const handleConsent = jest.fn();

      render(<ConsentForm onConsent={handleConsent} />);

      // Fill required fields only (no phone)
      await user.type(screen.getByLabelText(/Firmenname/i), 'Test GmbH');
      await user.type(screen.getByLabelText(/Ansprechpartner/i), 'Max Mustermann');
      await user.type(
        screen.getByLabelText(/E-Mail-Adresse/i),
        'max@test.de'
      );

      // Check all required purposes
      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes.slice(0, 4)) {
        // First 4 are required
        await user.click(checkbox);
      }

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(handleConsent).toHaveBeenCalledWith(
          expect.objectContaining({
            phone: undefined,
          })
        );
      });
    });

    it('includes marketing consent when checked', async () => {
      const user = userEvent.setup();
      const handleConsent = jest.fn();

      render(<ConsentForm onConsent={handleConsent} />);

      // Fill required fields
      await user.type(screen.getByLabelText(/Firmenname/i), 'Test GmbH');
      await user.type(screen.getByLabelText(/Ansprechpartner/i), 'Max Mustermann');
      await user.type(
        screen.getByLabelText(/E-Mail-Adresse/i),
        'max@test.de'
      );

      // Check ALL purposes including optional marketing
      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes) {
        await user.click(checkbox);
      }

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(handleConsent).toHaveBeenCalledWith(
          expect.objectContaining({
            gdprConsent: expect.objectContaining({
              purposes: expect.arrayContaining(['marketing']),
            }),
          })
        );
      });
    });

    it('uses custom consent text version', async () => {
      const user = userEvent.setup();
      const handleConsent = jest.fn();

      render(<ConsentForm onConsent={handleConsent} consentTextVersion="2.5" />);

      // Fill and submit form
      await user.type(screen.getByLabelText(/Firmenname/i), 'Test GmbH');
      await user.type(screen.getByLabelText(/Ansprechpartner/i), 'Max Mustermann');
      await user.type(
        screen.getByLabelText(/E-Mail-Adresse/i),
        'max@test.de'
      );

      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes.slice(0, 4)) {
        await user.click(checkbox);
      }

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(handleConsent).toHaveBeenCalledWith(
          expect.objectContaining({
            gdprConsent: expect.objectContaining({
              consentTextVersion: '2.5',
            }),
          })
        );
      });
    });
  });

  describe('Consent Purpose Handling', () => {
    it('toggles consent purpose on checkbox click', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      const checkbox = screen.getByLabelText(/Angebotserstellung/i);

      // Initially unchecked
      expect(checkbox).not.toBeChecked();

      // Click to check
      await user.click(checkbox);
      expect(checkbox).toBeChecked();

      // Click again to uncheck
      await user.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });

    it('enables submit button when all required consents given', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });

      // Initially disabled
      expect(submitButton).toBeDisabled();

      // Check all required checkboxes
      const offerCheckbox = screen.getByLabelText(/Angebotserstellung/i);
      const storageCheckbox = screen.getByLabelText(/Datenspeicherung/i);
      const emailCheckbox = screen.getByLabelText(/E-Mail-Kommunikation/i);
      const privacyCheckbox = screen.getByLabelText(/Ich habe die/i);

      await user.click(offerCheckbox);
      await user.click(storageCheckbox);
      await user.click(emailCheckbox);
      await user.click(privacyCheckbox);

      // Now should be enabled
      expect(submitButton).not.toBeDisabled();
    });

    it('displays required asterisk for required purposes', () => {
      render(<ConsentForm />);

      const offerLabel = screen.getByText(/Angebotserstellung/);
      expect(offerLabel.parentElement).toHaveTextContent('*');

      const marketingLabel = screen.getByText(/Marketing \(optional\)/);
      expect(marketingLabel.parentElement).not.toHaveTextContent('*');
    });
  });

  describe('Custom Class Name', () => {
    it('applies custom className', () => {
      const { container } = render(<ConsentForm className="custom-class" />);

      const card = container.querySelector('.custom-class');
      expect(card).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper labels for all inputs', () => {
      render(<ConsentForm />);

      expect(screen.getByLabelText(/Firmenname/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Ansprechpartner/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/E-Mail-Adresse/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Telefonnummer/i)).toBeInTheDocument();
    });

    it('has proper labels for checkboxes', () => {
      render(<ConsentForm />);

      expect(screen.getByLabelText(/Angebotserstellung/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Datenspeicherung/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/E-Mail-Kommunikation/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Marketing/i)).toBeInTheDocument();
    });

    it('provides error messages with proper ARIA roles', async () => {
      const user = userEvent.setup();
      render(<ConsentForm />);

      // Check consents and submit to trigger validation
      const checkboxes = screen.getAllByRole('checkbox');
      for (const checkbox of checkboxes) {
        await user.click(checkbox);
      }

      const submitButton = screen.getByRole('button', {
        name: /Einwilligung erteilen/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        const errorMessages = screen.getAllByText(/ist erforderlich/i);
        expect(errorMessages.length).toBeGreaterThan(0);
      });
    });
  });
});
