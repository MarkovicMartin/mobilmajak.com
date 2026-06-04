import { useEffect } from 'react';
import { startUxFrictionMonitor } from '../utils/uxFrictionMonitor';

/** Po přihlášení spustí detekci rage/dead kliků a JS chyb → automatické UX tickety. */
const UxFrictionMonitor = () => {
    useEffect(() => {
        startUxFrictionMonitor();
    }, []);

    return null;
};

export default UxFrictionMonitor;
