import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ticketAPI } from '../../services/api';
import './TicketForm.css';

const TicketForm = ({ onSuccess, onCancel }) => {
    const [nazev, setNazev] = useState('');
    const [popis, setPopis] = useState('');
    const [files, setFiles] = useState([]);
    const [previews, setPreviews] = useState([]);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        const prev = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = prev;
        };
    }, []);

    const handleFileChange = (e) => {
        const selected = Array.from(e.target.files);
        const newFiles = [...files, ...selected].slice(0, 5);
        setFiles(newFiles);
        const newPreviews = newFiles.map(f => URL.createObjectURL(f));
        setPreviews(newPreviews);
    };

    const removeFile = (idx) => {
        const newFiles = files.filter((_, i) => i !== idx);
        setFiles(newFiles);
        URL.revokeObjectURL(previews[idx]);
        setPreviews(newFiles.map(f => URL.createObjectURL(f)));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!nazev.trim() || !popis.trim()) {
            setError('Název a popis jsou povinné.');
            return;
        }
        setError(null);
        setSubmitting(true);

        try {
            const formData = new FormData();
            formData.append('nazev', nazev.trim());
            formData.append('popis', popis.trim());
            formData.append('url', window.location.href);
            files.forEach(f => formData.append('images', f));

            const response = await ticketAPI.create(formData);
            if (response.success) {
                onSuccess && onSuccess(response.ticket);
            } else {
                setError(response.error || 'Chyba při odesílání.');
            }
        } catch (e) {
            setError('Chyba při odesílání ticketu.');
        } finally {
            setSubmitting(false);
        }
    };

    const overlay = (
        <div
            className="ticket-form-overlay"
            role="presentation"
            onClick={(e) => e.target === e.currentTarget && onCancel && onCancel()}
        >
            <div className="ticket-form-modal">
                <div className="ticket-form-header">
                    <h3>🐛 Nový ticket</h3>
                    <button type="button" className="ticket-form-close" onClick={onCancel} aria-label="Zavřít">
                        ✕
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="ticket-form-body">
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

                    <div className="ticket-form-footer">
                        <button type="button" className="btn-cancel" onClick={onCancel}>
                            Zrušit
                        </button>
                        <button type="submit" className="btn-submit" disabled={submitting}>
                            {submitting ? 'Odesílám...' : 'Odeslat ticket'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );

    return createPortal(overlay, document.body);
};

export default TicketForm;
