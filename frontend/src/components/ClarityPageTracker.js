import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { initClarity, trackClarityPage } from '../utils/clarity';

/** Načte Clarity (pokud je REACT_APP_CLARITY_PROJECT_ID) a při změně routy posílá tagy route/screen. */
const ClarityPageTracker = () => {
    const { pathname } = useLocation();

    useEffect(() => {
        initClarity();
    }, []);

    useEffect(() => {
        trackClarityPage(pathname);
    }, [pathname]);

    return null;
};

export default ClarityPageTracker;
