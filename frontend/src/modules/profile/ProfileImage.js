import React, { useState, useEffect } from 'react';
import './ProfileImage.css';

const ProfileImage = ({ user, onImageUpdate }) => {
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
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                setMessage('Nepodporovaný typ souboru. Povolené jsou pouze JPG, PNG a GIF.');
                setMessageType('error');
                return;
            }

            if (file.size > 5 * 1024 * 1024) {
                setMessage('Soubor je příliš velký. Maximální velikost je 5MB.');
                setMessageType('error');
                return;
            }

            setSelectedFile(file);
            setMessage('');

            const reader = new FileReader();
            reader.onload = (ev) => {
                setPreviewUrl(ev.target.result);
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
                onImageUpdate();
            } else {
                const error = await response.json();
                setMessage(error.error || 'Chyba při nahrávání obrázku');
                setMessageType('error');
            }
        } catch {
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
                onImageUpdate();
            } else {
                const error = await response.json();
                setMessage(error.error || 'Chyba při mazání obrázku');
                setMessageType('error');
            }
        } catch {
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

    const uploadControls = (
        <div className="upload-area">
            <input
                type="file"
                id="image-upload-embedded"
                accept="image/jpeg,image/jpg,image/png,image/gif"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
            />
            {!selectedFile ? (
                <>
                    <label htmlFor="image-upload-embedded" className="upload-button upload-button--compact">
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
};

export default ProfileImage;
