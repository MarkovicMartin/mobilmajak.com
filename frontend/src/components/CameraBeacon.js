import React from 'react';
import './CameraBeacon.css';

const MAJACEK_OK = `${process.env.PUBLIC_URL}/assets/majacek/ok.png`;
const MAJACEK_QUIET = `${process.env.PUBLIC_URL}/assets/majacek/quiet.png`;

/**
 * Majáček z logomanuálu – jen u prodejen v pilotu kamer.
 * ok = pohyb (ruce nahoru), quiet = bez pohybu (ruka na ústech).
 */
export default function CameraBeacon({ camera, title, className = '' }) {
    if (!camera?.in_pilot) return null;

    const active = Boolean(camera.active);
    const src = active ? MAJACEK_OK : MAJACEK_QUIET;
    const defaultTitle = active ? 'Kamera: pohyb' : 'Kamera: bez pohybu';

    return (
        <img
            src={src}
            alt=""
            className={`camera-beacon-icon${active ? ' camera-beacon-icon--on' : ''} ${className}`.trim()}
            title={title || defaultTitle}
            aria-hidden="true"
        />
    );
}
