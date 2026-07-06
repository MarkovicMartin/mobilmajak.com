import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { PageHeader } from '../../components/ui';
import './DailyDutiesModule.css';

const DailyDutiesModule = () => {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        (async () => {
            try {
                const res = await api.get('/daily-duties/templates/');
                setTemplates(res.data);
            } catch (err) {
                setError('Modul denních povinností není dostupný (testovací režim).');
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    return (
        <div className="daily-duties-module">
            <PageHeader
                title="Denní povinnosti"
                subtitle="Testovací modul – není na produkci"
            />

            <div className="daily-duties-banner">
                <i className="fas fa-flask" />
                Scaffold pro budoucí checklist provozu. Propojení se Slackem a financemi zatím chybí.
            </div>

            {error && <div className="alert alert-warning">{error}</div>}
            {loading && <p>Načítám…</p>}

            {!loading && !error && (
                <div className="daily-duties-list">
                    {templates.length === 0 ? (
                        <p className="daily-duties-empty">
                            Zatím žádné šablony. Přidejte je v Django adminu nebo importujte z Mastersheetu později.
                        </p>
                    ) : (
                        templates.map((t) => (
                            <div key={t.id} className="daily-duties-card">
                                <div className="daily-duties-card__title">{t.title}</div>
                                <div className="daily-duties-card__meta">
                                    {t.periodicity_display}
                                    {t.store && ` · ${t.store}`}
                                    {t.role && ` · ${t.role}`}
                                </div>
                                {t.description && (
                                    <p className="daily-duties-card__desc">{t.description}</p>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
};

export default DailyDutiesModule;
