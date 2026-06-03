import React, { useState, useEffect } from 'react';
import './ProfileImage.css';

const ProfileImage = ({ user, onImageUpdate, embedded = false }) => {
    const [profileImage, setProfileImage] = useState(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [previewUrl, setPreviewUrl] = useState('');

    useEffect(() => {
        loadProfileImage();
    }, [user]);

    const loadProfileImage = async () => {
        try {
            const response = await fetch('/api/users/profile/image/', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setProfileImage(data);
            } else if (response.status === 404) {
                setProfileImage(null);
            }
        } catch (error) {
            console.error('Chyba při načítání profilového obrázku:', error);
        }
    };

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            // Kontrola typu souboru
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                setMessage('Nepodporovaný typ souboru. Povolené jsou pouze JPG, PNG a GIF.');
                setMessageType('error');
                return;
            }

            // Kontrola velikosti (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                setMessage('Soubor je příliš velký. Maximální velikost je 5MB.');
                setMessageType('error');
                return;
            }

            setSelectedFile(file);
            setMessage('');
            
            // Vytvoření náhledu
            const reader = new FileReader();
            reader.onload = (e) => {
                setPreviewUrl(e.target.result);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            setMessage('Vyberte prosím soubor k nahrání.');
            setMessageType('error');
            return;
        }

        setLoading(true);
        setMessage('');

        const formData = new FormData();
        formData.append('obrazek', selectedFile);

        try {
            const response = await fetch('/api/users/profile/image/upload/', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                setProfileImage(data);
                setSelectedFile(null);
                setPreviewUrl('');
                setMessage('Profilový obrázek byl úspěšně nahrán');
                setMessageType('success');
                onImageUpdate(); // Aktualizace rodičovské komponenty
            } else {
                const error = await response.json();
                setMessage(error.error || 'Chyba při nahrávání obrázku');
                setMessageType('error');
            }
        } catch (error) {
            setMessage('Chyba při komunikaci se serverem');
            setMessageType('error');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!profileImage) return;

        setLoading(true);
        setMessage('');

        try {
            const response = await fetch('/api/users/profile/image/delete/', {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                setProfileImage(null);
                setMessage('Profilový obrázek byl smazán');
                setMessageType('success');
                onImageUpdate(); // Aktualizace rodičovské komponenty
            } else {
                const error = await response.json();
                setMessage(error.error || 'Chyba při mazání obrázku');
                setMessageType('error');
            }
        } catch (error) {
            setMessage('Chyba při komunikaci se serverem');
            setMessageType('error');
        } finally {
            setLoading(false);
        }
    };

    const cancelUpload = () => {
        setSelectedFile(null);
        setPreviewUrl('');
        setMessage('');
    };

    const uploadInputId = embedded ? 'image-upload-embedded' : 'image-upload';

    const uploadControls = (
        <div className="upload-area">
            <input
                type="file"
                id={uploadInputId}
                accept="image/jpeg,image/jpg,image/png,image/gif"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
            />
            {!selectedFile ? (
                <>
                    <label htmlFor={uploadInputId} className="upload-button upload-button--compact">
                        <i className="fas fa-camera" aria-hidden="true" />
                        <span>{profileImage ? 'Změnit foto' : 'Nahrát foto'}</span>
                    </label>
                    {profileImage && (
                        <button
                            type="button"
                            className="delete-button delete-button--compact"
                            onClick={handleDelete}
                            disabled={loading}
                        >
                            <i className="fas fa-trash" aria-hidden="true" />
                            Smazat
                        </button>
                    )}
                </>
            ) : (
                <div className="file-selected file-selected--compact">
                    <img src={previewUrl} alt="Náhled" className="preview-image preview-image--compact" />
                    <div className="file-actions">
                        <button
                            type="button"
                            className="upload-confirm-button"
                            onClick={handleUpload}
                            disabled={loading}
                        >
                            {loading ? 'Nahrávám…' : 'Nahrát'}
                        </button>
                        <button
                            type="button"
                            className="cancel-button"
                            onClick={cancelUpload}
                            disabled={loading}
                        >
                            Zrušit
                        </button>
                    </div>
                </div>
            )}
            {!embedded && !selectedFile && (
                <small className="upload-hint">JPG, PNG nebo GIF (max 5 MB)</small>
            )}
        </div>
    );

    const avatarBlock = profileImage ? (
        <img
            src={profileImage.obrazek}
            alt="Profilový obrázek"
            className="profile-preview"
        />
    ) : (
        <div className="no-image-icon" aria-hidden="true">
            <i className="fas fa-user-circle" />
        </div>
    );

    if (embedded) {
        return (
            <div className="profile-image profile-image--embedded">
                {message && (
                    <div className={`message ${messageType}`}>
                        {message}
                    </div>
                )}
                <div className="profile-image-embedded">
                    <div className="profile-image-embedded__avatar">{avatarBlock}</div>
                    <div className="profile-image-embedded__body">
                        <p className="profile-image-embedded__name">
                            {[user?.jmeno, user?.prijmeni].filter(Boolean).join(' ') || 'Váš profil'}
                        </p>
                        {profileImage?.datum_nahrani && (
                            <p className="profile-image-embedded__meta">
                                Foto z {new Date(profileImage.datum_nahrani).toLocaleDateString('cs-CZ')}
                            </p>
                        )}
                        {uploadControls}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="profile-image">
            <div className="image-header">
                <h2>Profilový obrázek</h2>
                <p>Nahrajte svůj profilový obrázek pro personalizaci účtu</p>
            </div>

            {message && (
                <div className={`message ${messageType}`}>
                    {message}
                </div>
            )}

            <div className="image-content">
                <div className="current-image-section">
                    <h3>Aktuální obrázek</h3>
                    {profileImage ? (
                        <div className="current-image">
                            {avatarBlock}
                            <div className="image-info">
                                <p>Nahráno: {new Date(profileImage.datum_nahrani).toLocaleDateString('cs-CZ')}</p>
                                <button
                                    type="button"
                                    className="delete-button"
                                    onClick={handleDelete}
                                    disabled={loading}
                                >
                                    <i className="fas fa-trash" aria-hidden="true" />
                                    Smazat obrázek
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="no-image">
                            <div className="no-image-icon">
                                <i className="fas fa-user-circle" aria-hidden="true" />
                            </div>
                            <p>Žádný profilový obrázek</p>
                        </div>
                    )}
                </div>

                <div className="upload-section">
                    <h3>Nahrát nový obrázek</h3>
                    {uploadControls}
                    <div className="upload-tips">
                        <h4>Tipy pro nahrávání:</h4>
                        <ul>
                            <li>Doporučená velikost: 300×300 pixelů</li>
                            <li>Podporované formáty: JPG, PNG, GIF</li>
                            <li>Maximální velikost: 5 MB</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProfileImage; 