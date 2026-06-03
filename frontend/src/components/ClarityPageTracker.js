import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { trackClarityPage } from '../utils/clarity';

/** Při změně React Router cesty pošle do Clarity tagy route/screen a událost spa_pageview. */
const ClarityPageTracker = () => {
    const { pathname } = useLocation();

    useEffect(() => {
        trackClarityPage(pathname);
    }, [pathname]);

    return null;
};

export default ClarityPageTracker;
