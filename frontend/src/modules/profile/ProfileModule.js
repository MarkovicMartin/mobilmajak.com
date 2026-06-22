import React, { useState, useEffect, useMemo } from 'react';
import { useLocation, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { profileAPI } from '../../services/api';
import { PageHeader, Tabs } from '../../components/ui';
import './ProfileModule.css';
import ProfileInfo from './ProfileInfo';
import ProfileAnalytics from './ProfileAnalytics';
import ProfileCalendar from './ProfileCalendar';

const PROFILE_TABS = [
    { id: 'calendar', label: 'Můj kalendář', icon: <i className="fas fa-calendar" aria-hidden="true" /> },
    { id: 'shifts', label: 'Směny', icon: <i className="fas fa-calendar-alt" aria-hidden="true" /> },
    { id: 'analytics', label: 'Moje výsledky', icon: <i className="fas fa-chart-line" aria-hidden="true" /> },
    { id: 'info', label: 'Osobní údaje', icon: <i className="fas fa-user" aria-hidden="true" /> },
];

const ProfileModule = () => {
    const { user: authUser } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState(
        () => location.state?.profileTab || 'calendar',
    );
    const [profileUser, setProfileUser] = useState(null);
    const [profileLoading, setProfileLoading] = useState(true);
    const [profileError, setProfileError] = useState(false);

    const tabs = useMemo(() => PROFILE_TABS, []);

    useEffect(() => {
        if (location.state?.profileTab) {
            setActiveTab(location.state.profileTab);
        }
    }, [location.state?.profileTab, location.key]);

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

    if (location.state?.profileTab === 'tasks') {
        return (
            <Navigate
                to={location.state?.taskId
                    ? `/my-tasks?id=${location.state.taskId}`
                    : '/my-tasks'}
                replace
            />
        );
    }

    if (location.state?.profileTab === 'shifts') {
        return <Navigate to="/shifts" replace />;
    }

    const infoUser = profileUser || authUser;

    const handleTabChange = (tabId) => {
        if (tabId === 'shifts') {
            navigate('/shifts');
            return;
        }
        setActiveTab(tabId);
    };

    return (
        <div className="profile-module">
            <PageHeader title="Můj profil" />

            <Tabs
                tabs={tabs}
                activeId={activeTab}
                onTabChange={handleTabChange}
                ariaLabel="Sekce profilu"
                className="profile-module-tabs"
            />

            <div className="profile-content">
                {activeTab === 'calendar' && <ProfileCalendar />}
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
