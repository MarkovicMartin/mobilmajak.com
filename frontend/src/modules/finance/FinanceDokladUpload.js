import React, { useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceDropZone from './FinanceDropZone';

const FinanceDokladUpload = ({ polozka, onUploaded, compact = false }) => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    if (polozka.doklad_id) {
        return <span className="finance-badge">FA ✓</span>;
    }

    const upload = async (selected) => {
        if (!selected) {
            setError('Vyberte soubor');
            return;
        }
        setUploading(true);
        setError('');
        try {
            await financeAPI.uploadDoklad({
                file: selected,
                naklad_polozka_id: polozka.id,
                cislo_faktury: polozka.faktura_hint?.cislo_faktury || '',
                dodavatel_nazev: polozka.faktura_hint?.dodavatel_nazev || '',
            });
            setFile(null);
            onUploaded?.();
        } catch (e) {
            setError(e.response?.data?.error || 'Nahrání selhalo');
        } finally {
            setUploading(false);
        }
    };

    if (compact) {
        return (
            <div className="finance-fa-upload finance-fa-upload--compact">
                <FinanceDropZone
                    compact
                    disabled={uploading}
                    label="FA"
                    onFile={(f) => {
                        setFile(f);
                        upload(f);
                    }}
                />
                {error && <span className="finance-fa-upload__err">{error}</span>}
            </div>
        );
    }

    return (
        <div className="finance-fa-upload">
            <FinanceDropZone
                disabled={uploading}
                onFile={(f) => {
                    setFile(f);
                }}
            />
            {file && <p className="finance-fa-upload__name">{file.name}</p>}
            <button type="button" disabled={uploading || !file} onClick={() => upload(file)}>
                {uploading ? 'Nahrávám…' : 'Přiložit fakturu'}
            </button>
            {error && <span className="finance-fa-upload__err">{error}</span>}
        </div>
    );
};

export default FinanceDokladUpload;
