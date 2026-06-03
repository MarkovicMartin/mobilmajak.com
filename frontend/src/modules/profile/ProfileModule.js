import React, { useState, useEffect } from 'react';
import './ProfileModule.css';
import ProfileInfo from './ProfileInfo';
import ProfileAnalytics from './ProfileAnalytics';

const ProfileModule = () => {
    const [activeTab, setActiveTab] = useState('analytics');
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchUserProfile();
    }, []);

    const fetchUserProfile = async () => {
        try {
            const response = await fetch('/api/users/profile/', {
                credentials: 'include'
            });

            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            } else {
                console.error('Chyba při načítání profilu');
            }
        } catch (error) {
            console.error('Chyba při načítání profilu:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleProfileUpdate = (updatedUser) => {
        setUser(updatedUser);
    };

    if (loading) {
        return (
            <div className="profile-module">
                <div className="loading-spinner">
                    <div className="spinner"></div>
                    <p>Načítám profil...</p>
                </div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="profile-module">
                <div className="error-message">
                    <h2>Chyba</h2>
                    <p>Nepodařilo se načíst profil uživatele.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="profile-module">
            <div className="profile-tabs" role="tablist" aria-label="Sekce profilu">
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'analytics'}
                    className={`tab-button ${activeTab === 'analytics' ? 'active' : ''}`}
                    onClick={() => setActiveTab('analytics')}
                >
                    <i className="fas fa-chart-line" aria-hidden="true" />
                    Moje výsledky
                </button>
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'info'}
                    className={`tab-button ${activeTab === 'info' ? 'active' : ''}`}
                    onClick={() => setActiveTab('info')}
                >
                    <i className="fas fa-user" aria-hidden="true" />
                    Osobní údaje
                </button>
            </div>

            <div className="profile-content">
                {activeTab === 'analytics' && (
                    <ProfileAnalytics userId={user.id} />
                )}
                {activeTab === 'info' && (
                    <ProfileInfo
                        user={user}
                        onProfileUpdate={handleProfileUpdate}
                        onImageUpdate={fetchUserProfile}
                    />
                )}
            </div>
        </div>
    );
};

export default ProfileModule;
