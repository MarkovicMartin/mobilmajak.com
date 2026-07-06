import React, { useState } from 'react';
import { financeAPI } from '../../services/api';

const FinanceDokladUpload = ({ polozka, onUploaded, compact = false }) => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    if (polozka.doklad_id) {
        return <span className="finance-badge">FA ✓</span>;
    }

    const handleUpload = async () => {
        if (!file) {
            setError('Vyberte soubor');
            return;
        }
        setUploading(true);
        setError('');
        try {
            await financeAPI.uploadDoklad({
                file,
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

    return (
        <div className={compact ? 'finance-fa-upload finance-fa-upload--compact' : 'finance-fa-upload'}>
            <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,image/*,application/pdf"
                onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setError('');
                }}
            />
            <button type="button" disabled={uploading || !file} onClick={handleUpload}>
                {uploading ? '…' : 'FA'}
            </button>
            {error && <span className="finance-fa-upload__err">{error}</span>}
        </div>
    );
};

export default FinanceDokladUpload;
