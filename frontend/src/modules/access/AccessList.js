import React, { useState } from 'react';
import { copyToClipboard, showCopyError } from '../../utils/clipboard';
import './AccessList.css';

const AccessList = ({ accesses, canEdit, canDelete, onEdit, onDelete, onRevealPassword }) => {
    const [copiedKey, setCopiedKey] = useState(null);

    const formatDate = (dateString) => {
        if (!dateString) return 'Nikdy';
        return new Date(dateString).toLocaleString('cs-CZ');
    };

    const markCopied = (key) => {
        setCopiedKey(key);
        window.setTimeout(() => setCopiedKey(null), 1600);
    };

    const handleCopyToClipboard = async (text, key) => {
        const result = await copyToClipboard(text);

        if (result.success) {
            markCopied(key);
        } else {
            showCopyError(result.error);
            alert(`Login: ${text}\n\n(Zkopírujte ručně)`);
        }
    };

    const handleRevealPassword = async (accessId) => {
        const key = `pwd-${accessId}`;
        const result = await onRevealPassword(accessId);

        if (result?.success) {
            markCopied(key);
            return;
        }

        if (result?.password) {
            showCopyError(result.error);
            alert(`Heslo: ${result.password}\n\n(Zkopírujte ručně)`);
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
                {accesses.map(access => {
                    const loginKey = `login-${access.id}`;
                    const pwdKey = `pwd-${access.id}`;
                    const loginCopied = copiedKey === loginKey;
                    const pwdCopied = copiedKey === pwdKey;

                    return (
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
                                    <span className="access-action">
                                        <button
                                            type="button"
                                            className="value link access-action__btn"
                                            onClick={() => handleOpenWebsite(access.website_url)}
                                            aria-label="Otevřít web"
                                        >
                                            {access.website_url}
                                        </button>
                                        <span className="access-action__hint" aria-hidden="true">Otevřít</span>
                                    </span>
                                </div>
                            )}

                            <div className="detail-row">
                                <span className="label">👤 Login:</span>
                                <span className={`access-action${loginCopied ? ' access-action--done' : ''}`}>
                                    <button
                                        type="button"
                                        className={`value clickable access-action__btn${loginCopied ? ' access-action__btn--copied' : ''}`}
                                        onClick={() => handleCopyToClipboard(access.username, loginKey)}
                                        aria-label={loginCopied ? 'Zkopírováno' : 'Zkopírovat login'}
                                    >
                                        {access.username}
                                    </button>
                                    <span className="access-action__hint" aria-hidden="true">Kopírovat</span>
                                    {loginCopied ? (
                                        <span className="access-action__toast" role="status">
                                            Zkopírováno
                                        </span>
                                    ) : null}
                                </span>
                            </div>

                            <div className="detail-row">
                                <span className="label">🔒 Heslo:</span>
                                <span className={`access-action${pwdCopied ? ' access-action--done' : ''}`}>
                                    <button
                                        type="button"
                                        className={`value clickable access-action__btn access-action__btn--password${pwdCopied ? ' access-action__btn--copied' : ''}`}
                                        onClick={() => handleRevealPassword(access.id)}
                                        aria-label={pwdCopied ? 'Zkopírováno' : 'Zkopírovat heslo'}
                                    >
                                        {access.masked_password}
                                    </button>
                                    <span className="access-action__hint" aria-hidden="true">Kopírovat</span>
                                    {pwdCopied ? (
                                        <span className="access-action__toast" role="status">
                                            Zkopírováno
                                        </span>
                                    ) : null}
                                </span>
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
                    );
                })}
            </div>
        </div>
    );
};

export default AccessList;
