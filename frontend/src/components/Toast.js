import React, { useState, useEffect } from 'react';
import './Toast.css';

const Toast = ({ message, type = 'success', duration = 3000, onClose }) => {
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsVisible(false);
            setTimeout(onClose, 300); // Wait for fade-out animation
        }, duration);

        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const handleClose = () => {
        setIsVisible(false);
        setTimeout(onClose, 300);
    };

    return (
        <div className={`toast toast-${type} ${isVisible ? 'toast-visible' : 'toast-hidden'}`}>
            <div className="toast-content">
                <span className="toast-icon">
                    {type === 'success' && '✅'}
                    {type === 'error' && '❌'}
                    {type === 'warning' && '⚠️'}
                    {type === 'info' && 'ℹ️'}
                </span>
                <span className="toast-message">{message}</span>
                <button className="toast-close" onClick={handleClose}>
                    ✕
                </button>
            </div>
        </div>
    );
};

// Toast Manager Component
export const ToastContainer = ({ toasts, removeToast }) => {
    return (
        <div className="toast-container">
            {toasts.map((toast) => (
                <Toast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    duration={toast.duration}
                    onClose={() => removeToast(toast.id)}
                />
            ))}
        </div>
    );
};

// Hook pro správu toastů
export const useToast = () => {
    const [toasts, setToasts] = useState([]);

    const addToast = (message, type = 'success', duration = 3000) => {
        const id = Date.now() + Math.random();
        const newToast = { id, message, type, duration };
        
        setToasts(prev => [...prev, newToast]);
        return id;
    };

    const removeToast = (id) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    };

    const showSuccess = (message, duration = 3000) => addToast(message, 'success', duration);
    const showError = (message, duration = 4000) => addToast(message, 'error', duration);
    const showWarning = (message, duration = 3500) => addToast(message, 'warning', duration);
    const showInfo = (message, duration = 3000) => addToast(message, 'info', duration);

    return {
        toasts,
        removeToast,
        showSuccess,
        showError,
        showWarning,
        showInfo
    };
};

export default Toast; 