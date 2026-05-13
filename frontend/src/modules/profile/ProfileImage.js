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
                {/* Aktuální obrázek */}
                <div className="current-image-section">
                    <h3>Aktuální obrázek</h3>
                    {profileImage ? (
                        <div className="current-image">
                            <img 
                                src={profileImage.obrazek} 
                                alt="Profilový obrázek" 
                                className="profile-preview"
                            />
                            <div className="image-info">
                                <p>Nahráno: {new Date(profileImage.datum_nahrani).toLocaleDateString('cs-CZ')}</p>
                                <button 
                                    className="delete-button"
                                    onClick={handleDelete}
                                    disabled={loading}
                                >
                                    <i className="fas fa-trash"></i>
                                    Smazat obrázek
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="no-image">
                            <div className="no-image-icon">
                                <i className="fas fa-user-circle"></i>
                            </div>
                            <p>Žádný profilový obrázek</p>
                        </div>
                    )}
                </div>

                {/* Nahrání nového obrázku */}
                <div className="upload-section">
                    <h3>Nahrát nový obrázek</h3>
                    
                    <div className="upload-area">
                        <input
                            type="file"
                            id="image-upload"
                            accept="image/jpeg,image/jpg,image/png,image/gif"
                            onChange={handleFileSelect}
                            style={{ display: 'none' }}
                        />
                        
                        {!selectedFile ? (
                            <label htmlFor="image-upload" className="upload-button">
                                <i className="fas fa-cloud-upload-alt"></i>
                                <span>Vybrat obrázek</span>
                                <small>JPG, PNG nebo GIF (max 5MB)</small>
                            </label>
                        ) : (
                            <div className="file-selected">
                                <div className="file-preview">
                                    <img src={previewUrl} alt="Náhled" className="preview-image" />
                                </div>
                                <div className="file-info">
                                    <p><strong>Soubor:</strong> {selectedFile.name}</p>
                                    <p><strong>Velikost:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                                    <p><strong>Typ:</strong> {selectedFile.type}</p>
                                </div>
                                <div className="file-actions">
                                    <button 
                                        className="upload-confirm-button"
                                        onClick={handleUpload}
                                        disabled={loading}
                                    >
                                        {loading ? 'Nahrávám...' : 'Nahrát obrázek'}
                                    </button>
                                    <button 
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

                    <div className="upload-tips">
                        <h4>Tipy pro nahrávání:</h4>
                        <ul>
                            <li>Doporučená velikost: 300x300 pixelů</li>
                            <li>Podporované formáty: JPG, PNG, GIF</li>
                            <li>Maximální velikost: 5MB</li>
                            <li>Pro nejlepší kvalitu použijte čtvercový obrázek</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProfileImage; 