import React, { useState, useEffect } from 'react';
import './ProfileModule.css';
import ProfileInfo from './ProfileInfo';
import ProfileAnalytics from './ProfileAnalytics';
import ProfileImage from './ProfileImage';

const ProfileModule = () => {
    const [activeTab, setActiveTab] = useState('info');
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
            <div className="profile-header">
                <h1>Můj profil</h1>
                <p>Správa osobních údajů a přehled výsledků</p>
            </div>

            <div className="profile-tabs">
                <button 
                    className={`tab-button ${activeTab === 'info' ? 'active' : ''}`}
                    onClick={() => setActiveTab('info')}
                >
                    <i className="fas fa-user"></i>
                    Osobní údaje
                </button>
                <button 
                    className={`tab-button ${activeTab === 'analytics' ? 'active' : ''}`}
                    onClick={() => setActiveTab('analytics')}
                >
                    <i className="fas fa-chart-line"></i>
                    Moje výsledky
                </button>
                <button 
                    className={`tab-button ${activeTab === 'image' ? 'active' : ''}`}
                    onClick={() => setActiveTab('image')}
                >
                    <i className="fas fa-camera"></i>
                    Profilový obrázek
                </button>
            </div>

            <div className="profile-content">
                {activeTab === 'info' && (
                    <ProfileInfo 
                        user={user} 
                        onProfileUpdate={handleProfileUpdate}
                    />
                )}
                {activeTab === 'analytics' && (
                    <ProfileAnalytics 
                        userId={user.id}
                    />
                )}
                {activeTab === 'image' && (
                    <ProfileImage 
                        user={user}
                        onImageUpdate={fetchUserProfile}
                    />
                )}
            </div>
        </div>
    );
};

export default ProfileModule; 