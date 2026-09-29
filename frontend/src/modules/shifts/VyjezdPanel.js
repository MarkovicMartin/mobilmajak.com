import React, { useCallback, useEffect, useState } from 'react';
import { shiftsAPI } from '../../services/api';
import { Select } from '../../components/ui';
import './VyjezdPanel.css';

const isSaturday = (iso) => {
    if (!iso) return false;
    const [year, month, day] = iso.split('-').map(Number);
    return new Date(year, month - 1, day).getDay() === 6;
};

const isSenimo = (store) => (store?.nazev || '').trim() === 'Senimo';

function VyjezdPanel({ month, stores }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [info, setInfo] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const payload = await shiftsAPI.listVyjezdy(month);
            setData(payload);
        } catch (err) {
            setData(null);
            setError(err?.response?.data?.error || 'Návrhy se nepodařilo načíst.');
        } finally {
            setLoading(false);
        }
    }, [month]);

    useEffect(() => {
        load();
    }, [load]);

    const navrhni = async () => {
        setBusy(true);
        setError('');
        setInfo('');
        try {
            const payload = await shiftsAPI.navrhniVyjezdy(month);
            setData(payload);
            setInfo(payload.vytvoreno
                ? `Přidáno ${payload.vytvoreno} návrhů.`
                : 'Nové návrhy nepřibyly. Komu už návrh vyšel, ten se nemění.');
        } catch (err) {
            setError(err?.response?.data?.error || 'Návrh se nepodařilo založit.');
        } finally {
            setBusy(false);
        }
    };

    const potvrdit = async () => {
        setBusy(true);
        setError('');
        setInfo('');
        try {
            const payload = await shiftsAPI.potvrditVyjezdy(month);
            setData(payload);
            const chyb = payload.chyby?.length || 0;
            setInfo(chyb
                ? `Založeno ${payload.vytvoreno} směn. ${chyb} se nepodařilo – viz řádek.`
                : `Založeno ${payload.vytvoreno} směn.`);
            if (chyb) {
                setError(payload.chyby.map((row) => `${row.jmeno}: ${row.error}`).join(' '));
            }
        } catch (err) {
            setError(err?.response?.data?.error || 'Směny se nepodařilo založit.');
        } finally {
            setBusy(false);
        }
    };

    const uloz = async (id, datum, prodejnaId) => {
        setBusy(true);
        setError('');
        setInfo('');
        try {
            const payload = await shiftsAPI.ulozVyjezd(id, { datum, prodejna_id: prodejnaId });
            setData(payload);
        } catch (err) {
            setError(err?.response?.data?.error || 'Změnu se nepodařilo uložit.');
            await load();
        } finally {
            setBusy(false);
        }
    };

    if (loading) {
        return <p className="vyjezd-panel__status">Načítám návrhy…</p>;
    }

    const skupiny = data?.skupiny || [];
    const bez = data?.bez_navrhu || [];
    const maNavrh = skupiny.some((skupina) => skupina.polozky.some((row) => row.stav === 'navrh'));

    return (
        <div className="vyjezd-panel">
            <p className="vyjezd-panel__lead">
                Dva výjezdy na prodejce. Vsetín jezdí na Přerov a Zlín, Zlín na Vsetín a Přerov,
                Globus, Senimo, Šternberk a Přerov mezi sebou. Senimo v sobotu nejde vybrat.
                Ručně lze zvolit i jinou prodejnu.
            </p>
            {error && <div className="vyjezd-panel__error" role="alert">{error}</div>}
            {info && <p className="vyjezd-panel__info">{info}</p>}
            <div className="vyjezd-panel__actions">
                <button type="button" className="btn-secondary" onClick={navrhni} disabled={busy}>
                    Navrhnout chybějící
                </button>
                <button type="button" className="btn-submit" onClick={potvrdit} disabled={busy || !maNavrh}>
                    Založit směny
                </button>
            </div>
            {skupiny.length === 0 && (
                <p className="vyjezd-panel__status">V tomto měsíci zatím není žádný návrh.</p>
            )}
            {skupiny.map((skupina) => (
                <section key={skupina.user_id} className="vyjezd-card">
                    <header className="vyjezd-card__head">
                        <strong>{skupina.jmeno}</strong>
                        <span>{skupina.domaci_prodejna}</span>
                    </header>
                    {skupina.polozky.map((row) => {
                        const locked = row.stav !== 'navrh';
                        const options = stores
                            .filter((store) => store.id !== skupina.domaci_prodejna_id)
                            .filter((store) => !(isSaturday(row.datum) && isSenimo(store)))
                            .map((store) => ({ value: String(store.id), label: store.nazev }));
                        return (
                            <div key={row.id} className="vyjezd-row">
                                <input
                                    type="date"
                                    value={row.datum}
                                    min={`${month}-01`}
                                    max={`${month}-31`}
                                    disabled={locked || busy}
                                    aria-label={`Den výjezdu ${skupina.jmeno}`}
                                    onChange={(event) => {
                                        if (event.target.value) uloz(row.id, event.target.value, row.prodejna_id);
                                    }}
                                />
                                <Select
                                    options={options}
                                    value={String(row.prodejna_id)}
                                    disabled={locked || busy}
                                    aria-label={`Prodejna výjezdu ${skupina.jmeno}`}
                                    onChange={(value) => uloz(row.id, row.datum, Number(value))}
                                />
                                {locked ? (
                                    <span className="vyjezd-row__tag vyjezd-row__tag--done">v rozpisu</span>
                                ) : row.obsazeno ? (
                                    <span className="vyjezd-row__tag vyjezd-row__tag--busy">na prodejně už někdo je</span>
                                ) : (
                                    <span className="vyjezd-row__tag">volný den</span>
                                )}
                            </div>
                        );
                    })}
                </section>
            ))}
            {bez.length > 0 && (
                <p className="vyjezd-panel__missing">
                    Bez dvou návrhů: {bez.map((row) => row.jmeno).join(', ')}.
                </p>
            )}
        </div>
    );
}

export default VyjezdPanel;
