import React, { useState, useRef, useEffect } from 'react';
import Modal from '../../components/Modal';
import { ticketAPI } from '../../services/api';
import './TicketForm.css';

const TicketForm = ({ onSuccess, onCancel }) => {
    const [nazev, setNazev] = useState('');
    const [popis, setPopis] = useState('');
    const [files, setFiles] = useState([]);
    const [previews, setPreviews] = useState([]);
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const fileInputRef = useRef(null);
    const formRef = useRef(null);

    useEffect(() => {
        return () => {
            previews.forEach((url) => URL.revokeObjectURL(url));
        };
    }, [previews]);

    const handleFileChange = (e) => {
        const selected = Array.from(e.target.files || []);
        const combined = [...files, ...selected].slice(0, 5);
        setFiles(combined);
        previews.forEach((url) => URL.revokeObjectURL(url));
        setPreviews(combined.map((f) => URL.createObjectURL(f)));
        e.target.value = '';
    };

    const removeFile = (idx) => {
        const nextFiles = files.filter((_, i) => i !== idx);
        URL.revokeObjectURL(previews[idx]);
        setFiles(nextFiles);
        setPreviews(previews.filter((_, i) => i !== idx));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (submitting) return;
        setError('');
        setSubmitting(true);
        try {
            const fd = new FormData();
            fd.append('nazev', nazev.trim());
            fd.append('popis', popis.trim());
            if (typeof window !== 'undefined' && window.location?.href) {
                fd.append('url', window.location.href.slice(0, 500));
            }
            files.forEach((f) => fd.append('images', f));
            await ticketAPI.create(fd);
            onSuccess?.();
        } catch (err) {
            const detail = err?.response?.data?.error;
            setError(detail || 'Chyba při odesílání ticketu.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Modal
            title="🐛 Nový ticket"
            onClose={onCancel}
            size="sm"
            onSubmit={handleSubmit}
            formRef={formRef}
            footer={(
                <>
                    <button type="button" className="btn-cancel" onClick={onCancel}>
                        Zrušit
                    </button>
                    <button type="submit" className="btn-submit" disabled={submitting}>
                        {submitting ? 'Odesílám...' : 'Odeslat ticket'}
                    </button>
                </>
            )}
        >
            {error && <div className="ticket-form-error">{error}</div>}

            <div className="form-group">
                <label>Název *</label>
                <input
                    type="text"
                    value={nazev}
                    onChange={(e) => setNazev(e.target.value)}
                    placeholder="Krátký popis problému nebo nápadu"
                    maxLength={200}
                    required
                />
            </div>

            <div className="form-group">
                <label>Popis *</label>
                <textarea
                    value={popis}
                    onChange={(e) => setPopis(e.target.value)}
                    placeholder="Popište podrobně: co se stalo, kde, jak to reprodukovat..."
                    rows={5}
                    required
                />
            </div>

            <div className="form-group">
                <label>Obrázky / screenshoty (max. 5)</label>
                <div
                    className="file-drop-area"
                    onClick={() => fileInputRef.current?.click()}
                >
                    <span>📎 Klikni pro přidání obrázků</span>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        multiple
                        onChange={handleFileChange}
                        style={{ display: 'none' }}
                    />
                </div>

                {previews.length > 0 && (
                    <div className="file-previews">
                        {previews.map((src, idx) => (
                            <div key={idx} className="file-preview-item">
                                <img src={src} alt={`preview ${idx}`} />
                                <button
                                    type="button"
                                    className="file-remove"
                                    onClick={() => removeFile(idx)}
                                >
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </Modal>
    );
};

export default TicketForm;
