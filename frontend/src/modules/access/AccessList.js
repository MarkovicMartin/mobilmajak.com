import React from 'react';
import { copyToClipboard, showCopySuccess, showCopyError } from '../../utils/clipboard';
import './AccessList.css';

const AccessList = ({ accesses, canEdit, canDelete, onEdit, onDelete, onRevealPassword }) => {
    const formatDate = (dateString) => {
        if (!dateString) return 'Nikdy';
        return new Date(dateString).toLocaleString('cs-CZ');
    };

    const handleCopyToClipboard = async (text, field) => {
        const result = await copyToClipboard(text);
        
        if (result.success) {
            showCopySuccess(field, result.method);
        } else {
            showCopyError(result.error);
            // Zobrazíme text v alert jako backup
            alert(`${field}: ${text}\n\n(Zkopírujte ručně)`);
        }
    };

    const handleOpenWebsite = (url) => {
        if (url) {
            window.open(url, '_blank');
        }
    };

    if (accesses.length === 0) {
        return (
            <div className="access-list-empty">
                <div className="empty-state">
                    <h3>🔍 Žádné přístupy</h3>
                    <p>Nenašli jsme žádné přístupy odpovídající vašim filtrům.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="access-list">
            <div className="access-grid">
                {accesses.map(access => (
                    <div key={access.id} className="access-card">
                        <div className="access-header">
                            <div className="company-info">
                                <h3 className="company-name">
                                    {access.company_name}
                                </h3>
                                <div className="store-badge">
                                    🏪 {access.store}
                                </div>
                                {access.category && (
                                    <div className="category-badge">
                                        📁 {access.category}
                                    </div>
                                )}
                            </div>
                            
                            <div className="access-actions">
                                {canEdit && (
                                    <button
                                        className="btn-icon edit"
                                        onClick={() => onEdit(access)}
                                        title="Upravit přístup"
                                    >
                                        ✏️
                                    </button>
                                )}
                                {canDelete && (
                                    <button
                                        className="btn-icon delete"
                                        onClick={() => onDelete(access.id)}
                                        title="Smazat přístup"
                                    >
                                        🗑️
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="access-details">
                            {access.website_url && (
                                <div className="detail-row">
                                    <span className="label">🌐 Web:</span>
                                    <span 
                                        className="value link"
                                        onClick={() => handleOpenWebsite(access.website_url)}
                                        title="Otevřít v novém okně"
                                    >
                                        {access.website_url}
                                    </span>
                                </div>
                            )}

                            <div className="detail-row">
                                <span className="label">👤 Login:</span>
                                <span 
                                    className="value clickable"
                                    onClick={() => handleCopyToClipboard(access.username, 'Uživatelské jméno')}
                                    title="Klikněte pro kopírování"
                                >
                                    {access.username}
                                </span>
                            </div>

                            <div className="detail-row">
                                <span className="label">🔒 Heslo:</span>
                                <div className="password-row">
                                    <span className="masked-password">
                                        {access.masked_password}
                                    </span>
                                    <button
                                        className="btn-reveal"
                                        onClick={() => onRevealPassword(access.id)}
                                        title="Zobrazit a zkopírovat heslo"
                                    >
                                        👁️ Odkrýt
                                    </button>
                                </div>
                            </div>

                            {access.description && (
                                <div className="detail-row">
                                    <span className="label">📝 Popis:</span>
                                    <span className="value">{access.description}</span>
                                </div>
                            )}

                            {access.notes && (
                                <div className="detail-row">
                                    <span className="label">💡 Poznámky:</span>
                                    <span className="value">{access.notes}</span>
                                </div>
                            )}
                        </div>

                        <div className="access-footer">
                            <div className="meta-info">
                                <div className="meta-item">
                                    <span className="meta-label">Přidal:</span>
                                    <span className="meta-value">{access.added_by}</span>
                                </div>
                                <div className="meta-item">
                                    <span className="meta-label">Naposledy použito:</span>
                                    <span className="meta-value">{formatDate(access.last_used)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default AccessList; 