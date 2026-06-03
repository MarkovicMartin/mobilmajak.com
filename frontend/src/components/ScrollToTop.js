import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/** Posune stránku nahoru při přepnutí route (např. analytika → žebříček). */
export function scrollAppToTop() {
    window.scrollTo(0, 0);
    if (document.documentElement) {
        document.documentElement.scrollTop = 0;
    }
    if (document.body) {
        document.body.scrollTop = 0;
    }
}

const ScrollToTop = () => {
    const { pathname } = useLocation();

    useEffect(() => {
        scrollAppToTop();
        // Po vykreslení nové stránky (layout může posunout scroll zpět)
        const id = requestAnimationFrame(() => scrollAppToTop());
        return () => cancelAnimationFrame(id);
    }, [pathname]);

    return null;
};

export default ScrollToTop;
