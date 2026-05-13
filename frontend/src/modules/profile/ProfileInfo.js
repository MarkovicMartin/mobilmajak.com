import React, { useState } from 'react';
import './ProfileInfo.css';

const ProfileInfo = ({ user, onProfileUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [isChangingPassword, setIsChangingPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');

    const [formData, setFormData] = useState({
        jmeno: user.jmeno || '',
        prijmeni: user.prijmeni || '',
        prodejna: user.prodejna || '',
        telefon: user.telefon || '',
        email: user.email || '',
        adresa: user.adresa || '',
        poznamka: user.poznamka || ''
    });

    const [passwordData, setPasswordData] = useState({
        stare_heslo: '',
        nove_heslo: '',
        potvrzeni_hesla: ''
    });

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handlePasswordChange = (e) => {
        const { name, value } = e.target;
        setPasswordData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleProfileSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');

        try {
            const response = await fetch('/api/users/profile/update/', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                const updatedUser = await response.json();
                onProfileUpdate(updatedUser);
                setIsEditing(false);
                setMessage('Profil byl úspěšně aktualizován');
                setMessageType('success');
            } else {
                const error = await response.json();
                setMessage(error.error || 'Chyba při aktualizaci profilu');
                setMessageType('error');
            }
        } catch (error) {
            setMessage('Chyba při komunikaci se serverem');
            setMessageType('error');
        } finally {
            setLoading(false);
        }
    };

    const handlePasswordSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');

        if (passwordData.nove_heslo !== passwordData.potvrzeni_hesla) {
            setMessage('Nová hesla se neshodují');
            setMessageType('error');
            setLoading(false);
            return;
        }

        try {
            const response = await fetch('/api/users/profile/change-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(passwordData)
            });

            if (response.ok) {
                setMessage('Heslo bylo úspěšně změněno');
                setMessageType('success');
                setIsChangingPassword(false);
                setPasswordData({
                    stare_heslo: '',
                    nove_heslo: '',
                    potvrzeni_hesla: ''
                });
            } else {
                const error = await response.json();
                setMessage(error.error || 'Chyba při změně hesla');
                setMessageType('error');
            }
        } catch (error) {
            setMessage('Chyba při komunikaci se serverem');
            setMessageType('error');
        } finally {
            setLoading(false);
        }
    };

    const cancelEdit = () => {
        setFormData({
            jmeno: user.jmeno || '',
            prijmeni: user.prijmeni || '',
            prodejna: user.prodejna || '',
            telefon: user.telefon || '',
            email: user.email || '',
            adresa: user.adresa || '',
            poznamka: user.poznamka || ''
        });
        setIsEditing(false);
        setMessage('');
    };

    return (
        <div className="profile-info">
            <div className="info-header">
                <h2>Osobní údaje</h2>
                {!isEditing && (
                    <button 
                        className="edit-button"
                        onClick={() => setIsEditing(true)}
                    >
                        <i className="fas fa-edit"></i>
                        Upravit
                    </button>
                )}
            </div>

            {message && (
                <div className={`message ${messageType}`}>
                    {message}
                </div>
            )}

            <div className="info-sections">
                {/* Osobní údaje */}
                <div className="info-section">
                    <h3>Základní informace</h3>
                    {isEditing ? (
                        <form onSubmit={handleProfileSubmit} className="edit-form">
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Jméno</label>
                                    <input
                                        type="text"
                                        name="jmeno"
                                        value={formData.jmeno}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Příjmení</label>
                                    <input
                                        type="text"
                                        name="prijmeni"
                                        value={formData.prijmeni}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>Prodejna</label>
                                <input
                                    type="text"
                                    name="prodejna"
                                    value={formData.prodejna}
                                    onChange={handleInputChange}
                                />
                            </div>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Telefon</label>
                                    <input
                                        type="tel"
                                        name="telefon"
                                        value={formData.telefon}
                                        onChange={handleInputChange}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>E-mail</label>
                                    <input
                                        type="email"
                                        name="email"
                                        value={formData.email}
                                        onChange={handleInputChange}
                                    />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>Adresa</label>
                                <textarea
                                    name="adresa"
                                    value={formData.adresa}
                                    onChange={handleInputChange}
                                    rows="3"
                                />
                            </div>
                            <div className="form-group">
                                <label>Poznámka</label>
                                <textarea
                                    name="poznamka"
                                    value={formData.poznamka}
                                    onChange={handleInputChange}
                                    rows="3"
                                />
                            </div>
                            <div className="form-actions">
                                <button type="submit" className="save-button" disabled={loading}>
                                    {loading ? 'Ukládám...' : 'Uložit změny'}
                                </button>
                                <button type="button" className="cancel-button" onClick={cancelEdit}>
                                    Zrušit
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div className="info-display">
                            <div className="info-row">
                                <span className="label">Jméno:</span>
                                <span className="value">{user.jmeno || 'Neuvedeno'}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">Příjmení:</span>
                                <span className="value">{user.prijmeni || 'Neuvedeno'}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">Prodejna:</span>
                                <span className="value">{user.prodejna || 'Neuvedeno'}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">Telefon:</span>
                                <span className="value">{user.telefon || 'Neuvedeno'}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">E-mail:</span>
                                <span className="value">{user.email || 'Neuvedeno'}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">Adresa:</span>
                                <span className="value">{user.adresa || 'Neuvedeno'}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">Poznámka:</span>
                                <span className="value">{user.poznamka || 'Neuvedeno'}</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Změna hesla */}
                <div className="info-section">
                    <h3>Zabezpečení</h3>
                    {isChangingPassword ? (
                        <form onSubmit={handlePasswordSubmit} className="password-form">
                            <div className="form-group">
                                <label>Aktuální heslo</label>
                                <input
                                    type="password"
                                    name="stare_heslo"
                                    value={passwordData.stare_heslo}
                                    onChange={handlePasswordChange}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Nové heslo</label>
                                <input
                                    type="password"
                                    name="nove_heslo"
                                    value={passwordData.nove_heslo}
                                    onChange={handlePasswordChange}
                                    required
                                    minLength="6"
                                />
                            </div>
                            <div className="form-group">
                                <label>Potvrzení nového hesla</label>
                                <input
                                    type="password"
                                    name="potvrzeni_hesla"
                                    value={passwordData.potvrzeni_hesla}
                                    onChange={handlePasswordChange}
                                    required
                                    minLength="6"
                                />
                            </div>
                            <div className="form-actions">
                                <button type="submit" className="save-button" disabled={loading}>
                                    {loading ? 'Měním heslo...' : 'Změnit heslo'}
                                </button>
                                <button 
                                    type="button" 
                                    className="cancel-button" 
                                    onClick={() => {
                                        setIsChangingPassword(false);
                                        setPasswordData({
                                            stare_heslo: '',
                                            nove_heslo: '',
                                            potvrzeni_hesla: ''
                                        });
                                    }}
                                >
                                    Zrušit
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div className="password-section">
                            <p>Zde můžete změnit své heslo pro přihlášení do systému.</p>
                            <button 
                                className="change-password-button"
                                onClick={() => setIsChangingPassword(true)}
                            >
                                <i className="fas fa-key"></i>
                                Změnit heslo
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProfileInfo; 