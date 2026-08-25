import React, { useEffect, useState } from 'react';
import './FinanceDokladEditForm.css';

const emptyForm = {
    dodavatel_nazev: '',
    cislo_faktury: '',
    vs: '',
    castka_celkem: '',
    castka_bez_dph: '',
    dph_castka: '',
    dph_sazba: '',
};

const fromDoklad = (d) => ({
    dodavatel_nazev: d?.dodavatel_nazev || '',
    cislo_faktury: d?.cislo_faktury || '',
    vs: d?.vs || '',
    castka_celkem: d?.castka_celkem != null ? String(d.castka_celkem) : '',
    castka_bez_dph: d?.castka_bez_dph != null ? String(d.castka_bez_dph) : '',
    dph_castka: d?.dph_castka != null ? String(d.dph_castka) : '',
    dph_sazba: d?.dph_sazba != null ? String(d.dph_sazba) : '',
});

/**
 * Ruční kontrola / doplnění údajů z FA (když OCR nic nevyčte).
 */
const FinanceDokladEditForm = ({ doklad, busy = false, onSave }) => {
    const [form, setForm] = useState(() => fromDoklad(doklad));

    useEffect(() => {
        setForm(fromDoklad(doklad));
    }, [doklad?.id, doklad?.vs, doklad?.cislo_faktury, doklad?.castka_celkem]);

    const setField = (field, value) => {
        setForm((prev) => ({ ...prev, [field]: value }));
    };

    const submit = (e) => {
        e.preventDefault();
        if (!onSave) return;
        onSave({ ...emptyForm, ...form });
    };

    const ocrEmpty =
        !doklad?.vs &&
        !doklad?.cislo_faktury &&
        doklad?.castka_celkem == null &&
        doklad?.castka_bez_dph == null;
    const chyby = Array.isArray(doklad?.ocr_chyby) ? doklad.ocr_chyby.filter(Boolean) : [];

    return (
        <form className="finance-doklad-edit" onSubmit={submit}>
            <h4>Údaje z faktury {ocrEmpty ? '(doplňte ručně)' : '(zkontrolujte / upravte)'}</h4>
            {chyby.length > 0 && (
                <p className="finance-doklad-edit__warn">{chyby.join(' ')}</p>
            )}
            {ocrEmpty && chyby.length === 0 && (
                <p className="finance-doklad-edit__warn">
                    OCR nevyčetlo údaje. Pro párování s Fio stačí doplnit aspoň VS.
                </p>
            )}
            <div className="finance-doklad-edit__grid">
                <label>
                    Dodavatel
                    <input
                        type="text"
                        value={form.dodavatel_nazev}
                        onChange={(e) => setField('dodavatel_nazev', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    Číslo FA
                    <input
                        type="text"
                        value={form.cislo_faktury}
                        onChange={(e) => setField('cislo_faktury', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    VS
                    <input
                        type="text"
                        value={form.vs}
                        onChange={(e) => setField('vs', e.target.value)}
                        disabled={busy}
                        required={doklad?.ceka_na_platbu}
                        placeholder="nutné pro auto-přiřazení"
                    />
                </label>
                <label>
                    Celkem
                    <input
                        type="text"
                        inputMode="decimal"
                        value={form.castka_celkem}
                        onChange={(e) => setField('castka_celkem', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    Základ
                    <input
                        type="text"
                        inputMode="decimal"
                        value={form.castka_bez_dph}
                        onChange={(e) => setField('castka_bez_dph', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    DPH
                    <input
                        type="text"
                        inputMode="decimal"
                        value={form.dph_castka}
                        onChange={(e) => setField('dph_castka', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    Sazba %
                    <input
                        type="text"
                        inputMode="numeric"
                        value={form.dph_sazba}
                        onChange={(e) => setField('dph_sazba', e.target.value)}
                        disabled={busy}
                        placeholder="21"
                    />
                </label>
            </div>
            <button type="submit" disabled={busy}>
                {busy ? 'Ukládám…' : 'Uložit údaje'}
            </button>
        </form>
    );
};

export default FinanceDokladEditForm;
