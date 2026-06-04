import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { profileAPI } from '../../services/api';
import './ProfileModule.css';
import ProfileInfo from './ProfileInfo';
import ProfileAnalytics from './ProfileAnalytics';
import ProfileCalendar from './ProfileCalendar';
import ProfileTasks from './ProfileTasks';

const ProfileModule = () => {
    const { user: authUser } = useAuth();
    const location = useLocation();
    const [activeTab, setActiveTab] = useState(
        () => location.state?.profileTab || 'calendar',
    );
    const [profileUser, setProfileUser] = useState(null);
    const [profileLoading, setProfileLoading] = useState(true);
    const [profileError, setProfileError] = useState(false);

    useEffect(() => {
        if (location.state?.profileTab) {
            setActiveTab(location.state.profileTab);
        }
    }, [location.state?.profileTab]);

    useEffect(() => {
        let cancelled = false;

        const fetchUserProfile = async () => {
            setProfileLoading(true);
            setProfileError(false);
            try {
                const userData = await profileAPI.getProfile();
                if (!cancelled) setProfileUser(userData);
            } catch {
                if (!cancelled) setProfileError(true);
            } finally {
                if (!cancelled) setProfileLoading(false);
            }
        };

        fetchUserProfile();
        return () => { cancelled = true; };
    }, []);

    if (!authUser) {
        return (
            <div className="profile-module">
                <div className="error-message">
                    <h2>Chyba</h2>
                    <p>Nepodařilo se načíst profil uživatele.</p>
                </div>
            </div>
        );
    }

    const infoUser = profileUser || authUser;

    return (
        <div className="profile-module">
            <div className="profile-tabs" role="tablist" aria-label="Sekce profilu">
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'calendar'}
                    className={`tab-button ${activeTab === 'calendar' ? 'active' : ''}`}
                    onClick={() => setActiveTab('calendar')}
                >
                    <i className="fas fa-calendar" aria-hidden="true" />
                    Můj kalendář
                </button>
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'tasks'}
                    className={`tab-button ${activeTab === 'tasks' ? 'active' : ''}`}
                    onClick={() => setActiveTab('tasks')}
                >
                    <i className="fas fa-clipboard-list" aria-hidden="true" />
                    Moje úkoly
                </button>
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
                {activeTab === 'calendar' && <ProfileCalendar />}
                {activeTab === 'tasks' && <ProfileTasks />}
                {activeTab === 'analytics' && (
                    <ProfileAnalytics userId={authUser.id} />
                )}
                {activeTab === 'info' && (
                    profileLoading ? (
                        <div className="loading-spinner">
                            <div className="spinner" />
                            <p>Načítám osobní údaje…</p>
                        </div>
                    ) : profileError ? (
                        <div className="error-message">
                            <p>Nepodařilo se načíst osobní údaje.</p>
                        </div>
                    ) : (
                        <ProfileInfo
                            user={infoUser}
                            onProfileUpdate={setProfileUser}
                            onImageUpdate={async () => {
                                try {
                                    setProfileUser(await profileAPI.getProfile());
                                } catch {
                                    /* profil zůstane beze změny */
                                }
                            }}
                        />
                    )
                )}
            </div>
        </div>
    );
};

export default ProfileModule;
