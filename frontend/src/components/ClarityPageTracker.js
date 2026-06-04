import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { initClarity, trackClarityPage, trackClarityUser } from '../utils/clarity';

/** Clarity: init + tagy obrazovky při každé změně React Router cesty. */
const ClarityPageTracker = () => {
    const { pathname } = useLocation();
    const { user } = useAuth();

    useEffect(() => {
        initClarity();
    }, []);

    useEffect(() => {
        trackClarityUser(user);
    }, [user]);

    useEffect(() => {
        trackClarityPage(pathname, user);
    }, [pathname, user]);

    return null;
};

export default ClarityPageTracker;
