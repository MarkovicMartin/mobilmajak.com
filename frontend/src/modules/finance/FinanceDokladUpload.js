import React, { useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceDropZone from './FinanceDropZone';
import FinanceDokladSummary from './FinanceDokladSummary';

const FinanceDokladUpload = ({ polozka, onUploaded, compact = false }) => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const [uploadedDoklad, setUploadedDoklad] = useState(null);

    const doklad = uploadedDoklad || polozka.doklad;
    if (polozka.doklad_id || doklad) {
        return <FinanceDokladSummary doklad={doklad || { id: polozka.doklad_id }} compact={compact} />;
    }

    const upload = async (selected) => {
        if (!selected) {
            setError('Vyberte soubor');
            return;
        }
        setUploading(true);
        setError('');
        try {
            const result = await financeAPI.uploadDoklad({
                file: selected,
                naklad_polozka_id: polozka.id,
                cislo_faktury: polozka.faktura_hint?.cislo_faktury || '',
                dodavatel_nazev: polozka.faktura_hint?.dodavatel_nazev || '',
            });
            setFile(null);
            if (result?.doklad) {
                setUploadedDoklad(result.doklad);
            }
            onUploaded?.(result);
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
                    label={uploading ? '…' : 'FA'}
                    onFile={(f) => {
                        setFile(f);
                        upload(f);
                    }}
                />
                {uploading && <span className="finance-fa-upload__busy">Nahrávám…</span>}
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
