import React, { useState } from 'react';
import { financeAPI } from '../../services/api';
import './FinanceKontrolaPanel.css';

const predchoziMesic = () => {
    const dnes = new Date();
    const den = new Date(dnes.getFullYear(), dnes.getMonth() - 1, 1);
    return { rok: den.getFullYear(), mesic: den.getMonth() + 1 };
};

const FinanceUzaverkaPanel = () => {
    const vychozi = predchoziMesic();
    const [rok, setRok] = useState(vychozi.rok);
    const [mesic, setMesic] = useState(vychozi.mesic);
    const [priznani, setPriznani] = useState('');
    const [vynosy, setVynosy] = useState('');
    const [cistyZisk, setCistyZisk] = useState('');
    const [allegro, setAllegro] = useState('');
    const [vs, setVs] = useState('');
    const [report, setReport] = useState(null);
    const [upominka, setUpominka] = useState(null);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);

    const params = () => ({
        rok,
        mesic,
        priznani,
        vynosy,
        cisty_zisk: cistyZisk,
        allegro,
    });

    const load = async () => {
        setLoading(true);
        setError('');
        setMessage('');
        try {
            const data = await financeAPI.getUcetniDph(params());
            setReport(data);
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Kontrola selhala');
        } finally {
            setLoading(false);
        }
    };

    const zapis = async () => {
        setLoading(true);
        setError('');
        setMessage('');
        try {
            const data = await financeAPI.zapsatUcetniVykupy({ rok, mesic });
            const zapisTabulky = data.zapis || {};
            await load();
            if (zapisTabulky.ok) {
                setMessage(`Zapsáno ${zapisTabulky.pocet} řádků na list ${zapisTabulky.sheet}.`);
            } else if (zapisTabulky.skipped) {
                setMessage('Tabulka se nezapsala. Chybí přístup k Google Sheets, řádky jsou v přehledu.');
            } else {
                setMessage(zapisTabulky.error || 'Zápis tabulky selhal');
            }
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Zápis selhal');
            setLoading(false);
        }
    };

    const overVs = async () => {
        setError('');
        try {
            setUpominka(await financeAPI.getUcetniUpominka(vs));
        } catch (e) {
            setError(e.response?.data?.error || 'Kontrola VS selhala');
        }
    };

    return (
        <section className="finance-panel finance-uzaverka">
            <p className="finance-panel__intro">
                Měsíční uzávěrka před podáním DPH. Systém připraví výkupy, předpisy bazaru
                a tři interní doklady. Přiznání neodesílá. Platbu faktury schvaluje p. Bajtek.
            </p>
            <div className="finance-uzaverka-form">
                <label>
                    Rok
                    <input type="number" value={rok} onChange={(e) => setRok(e.target.value)} />
                </label>
                <label>
                    Měsíc
                    <input type="number" min="1" max="12" value={mesic} onChange={(e) => setMesic(e.target.value)} />
                </label>
                <label>
                    Řádek 1 přiznání
                    <input value={priznani} onChange={(e) => setPriznani(e.target.value)} />
                </label>
                <label>
                    Výnosy z výkazu
                    <input value={vynosy} onChange={(e) => setVynosy(e.target.value)} />
                </label>
                <label>
                    Čistý zisk z tabulky
                    <input value={cistyZisk} onChange={(e) => setCistyZisk(e.target.value)} />
                </label>
                <label>
                    Nová FA Allegro
                    <input value={allegro} onChange={(e) => setAllegro(e.target.value)} />
                </label>
                <button type="button" onClick={load} disabled={loading}>Spočítat</button>
                <button type="button" onClick={zapis} disabled={loading}>Zapsat výkupy do tabulky</button>
            </div>
            <div className="finance-uzaverka-form">
                <label>
                    VS upomínky
                    <input value={vs} onChange={(e) => setVs(e.target.value)} />
                </label>
                <button type="button" onClick={overVs}>Zkontrolovat úhradu</button>
                {upominka && <p>{upominka.duvod}</p>}
            </div>
            {error && <p className="finance-error">{error}</p>}
            {message && <p className="finance-message">{message}</p>}
            {report && (
                <>
                    <p>
                        Období {report.obdobi}, termín {report.termin}.
                        {' '}
                        {report.pripraveno ? 'Podklady sedí.' : 'Podklady ještě nesedí.'}
                        {' '}
                        {report.podani}
                    </p>
                    <ul className="finance-uzaverka-list">
                        {report.polozky.map((row) => (
                            <li key={row.kod}>
                                <strong>{row.nazev}:</strong> {row.detail}
                            </li>
                        ))}
                    </ul>
                    <h3>Interní doklady</h3>
                    <ul className="finance-uzaverka-list">
                        {report.interni_doklady.map((row) => (
                            <li key={row.radek}>
                                {row.vystaveno} – {row.nazev}: {row.castka}
                            </li>
                        ))}
                    </ul>
                    <p>
                        {report.allegro?.akce}
                        {report.allegro?.nova_fa ? ` ${report.allegro.nova_fa}` : ''}
                    </p>
                    <p>{report.obrat?.dalsi_krok}</p>
                    {report.souhrn_bazaru && (
                        <p>
                            Bazar: nákup {report.souhrn_bazaru.nakupni_cena}, zisk {report.souhrn_bazaru.zisk},
                            DPH {report.souhrn_bazaru.dph} ({report.souhrn_bazaru.vzorec_dph}).
                        </p>
                    )}
                    {report.bazary?.length > 0 && (
                        <>
                            <h3>Účtenky bazaru ({report.bazaru_celkem})</h3>
                            <ul className="finance-uzaverka-list">
                                {report.bazary.map((row) => (
                                    <li key={`${row.doklad}-${row.popis}`}>
                                        {row.doklad || 'bez čísla'}: {row.popis}
                                    </li>
                                ))}
                            </ul>
                        </>
                    )}
                </>
            )}
        </section>
    );
};

export default FinanceUzaverkaPanel;
