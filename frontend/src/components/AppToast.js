import React, { useEffect, useState } from 'react';
import './AppToast.css';

const AppToast = () => {
    const [toast, setToast] = useState(null);

    useEffect(() => {
        const handler = (e) => {
            const { message, duration = 4500 } = e.detail || {};
            if (!message) return;
            setToast({ message, duration });
        };
        window.addEventListener('app-toast', handler);
        return () => window.removeEventListener('app-toast', handler);
    }, []);

    useEffect(() => {
        if (!toast) return undefined;
        const id = window.setTimeout(() => setToast(null), toast.duration);
        return () => clearTimeout(id);
    }, [toast]);

    if (!toast) return null;

    return (
        <div className="app-toast" role="status">
            {toast.message}
        </div>
    );
};

export const showAppToast = (message, duration = 4500) => {
    window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, duration } }));
};

export default AppToast;
