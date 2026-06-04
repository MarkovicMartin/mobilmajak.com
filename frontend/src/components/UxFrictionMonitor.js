import { useEffect } from 'react';
import { startUxFrictionMonitor } from '../utils/uxFrictionMonitor';

/** Po přihlášení spustí přísnější detekci UX záseků → automatické UX tickety (s limity). */
const UxFrictionMonitor = () => {
    useEffect(() => {
        startUxFrictionMonitor();
    }, []);

    return null;
};

export default UxFrictionMonitor;
