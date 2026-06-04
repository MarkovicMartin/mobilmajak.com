import React from 'react';

const KAT_LABELS = {
    NOVE_TELEFONY: 'Telefony nové',
    BAZAROVE_TELEFONY: 'Telefony bazarové',
    PRISLUSENSTVI: 'Příslušenství',
    PRISLUSENSTVI_SKLA: 'Skla',
    PRISLUSENSTVI_OBALY: 'Obaly',
    PRISLUSENSTVI_OSTATNI: 'Příslušenství ostatní',
    SLUZBY: 'Služby',
    SERVIS: 'Servis',
    OSTATNI: 'Ostatní',
};

const SignalsChips = ({ signaly }) => {
    if (!signaly) return null;
    const chips = [];
    if (signaly.systematicky_pod_planem) {
        chips.push({ key: 'pod', label: 'Pod plánem 3M', tone: 'bad' });
    }
    (signaly.silne_kategorie || []).forEach((k) => {
        chips.push({ key: `s-${k}`, label: `Silné: ${KAT_LABELS[k] || k}`, tone: 'good' });
    });
    (signaly.slabe_kategorie || []).forEach((k) => {
        chips.push({ key: `w-${k}`, label: `Slabé: ${KAT_LABELS[k] || k}`, tone: 'warn' });
    });
    if (!chips.length) return <span className="coaching-muted">Bez signálů</span>;
    return (
        <div className="coaching-signals">
            {chips.map((c) => (
                <span key={c.key} className={`coaching-signal coaching-signal--${c.tone}`}>{c.label}</span>
            ))}
        </div>
    );
};

export default SignalsChips;
