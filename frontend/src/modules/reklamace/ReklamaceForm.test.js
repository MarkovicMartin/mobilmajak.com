import { fireEvent, render, screen } from '@testing-library/react';
import ReklamaceForm from './ReklamaceForm';

test('Uložit bez čísla zásilky otevře potvrzení nad formulářem', () => {
    const onSave = jest.fn();
    render(
        <ReklamaceForm defaultProdejna="Servis" onSave={onSave} onCancel={() => {}} />,
    );

    fireEvent.change(screen.getByLabelText(/název zboží/i), {
        target: { name: 'nazev_zbozi', value: 'Displej' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Uložit' }));

    expect(screen.getByRole('heading', { name: /bez čísla balíčku/i })).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();

    const overlay = document.querySelector('.reklamace-form-confirm-overlay');
    expect(overlay).not.toBeNull();
    expect(overlay.parentElement).toBe(document.body);
});
