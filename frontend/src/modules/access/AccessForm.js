import React, { useState, useEffect } from 'react';
import Modal from '../../components/Modal';
import './AccessForm.css';

const BUILTIN_CATEGORIES = ['Dodavatel', 'E-shop', 'Admin', 'Marketing', 'Ostatní'];

const AccessForm = ({ access, stores, categories, onSubmit, onCancel, canUseAdminCategory = false }) => {
    const [formData, setFormData] = useState({
        company_name: '',
        website_url: '',
        username: '',
        password: '',
        category: '',
        store: '',
        description: '',
        notes: ''
    });
    const [errors, setErrors] = useState({});
    const [formError, setFormError] = useState('');
    const [loading, setLoading] = useState(false);

    // Získání unikátních názvů prodejen ze statistik
    const storeNames = stores.map(store => store.store);

    const categoryOptions = [
        ...new Set([
            ...categories,
            ...BUILTIN_CATEGORIES.filter(
                (c) => c !== 'Admin' || canUseAdminCategory
            ),
        ]),
    ].filter((c) => c !== 'Admin' || canUseAdminCategory);

    useEffect(() => {
        if (access) {
            setFormData({
                company_name: access.company_name || '',
                website_url: access.website_url || '',
                username: access.username || '',
                // Heslo API nevrací — prázdné = při uložení ponechat stávající
                password: '',
                category: access.category || '',
                store: access.store || '',
                description: access.description || '',
                notes: access.notes || ''
            });
            setFormError('');
            setErrors({});
        }
    }, [access]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        setFormError('');
        
        // Vymazání chyby pro dané pole
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.company_name.trim()) {
            newErrors.company_name = 'Název společnosti je povinný';
        }

        if (!formData.store.trim()) {
            newErrors.store = 'Prodejna je povinná';
        }

        if (!formData.username.trim()) {
            newErrors.username = 'Uživatelské jméno je povinné';
        }

        // Při úpravě prázdné heslo = ponechat stávající
        if (!access && !formData.password.trim()) {
            newErrors.password = 'Heslo je povinné';
        }

        if (formData.website_url && !isValidUrl(formData.website_url)) {
            newErrors.website_url = 'Neplatná URL adresa';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const isValidUrl = (string) => {
        try {
            new URL(string.startsWith('http') ? string : 'https://' + string);
            return true;
        } catch (_) {
            return false;
        }
    };

    const normalizeWebsiteUrl = (value) => {
        const trimmed = (value || '').trim();
        if (!trimmed) return '';
        if (/^https?:\/\//i.test(trimmed)) return trimmed;
        return `https://${trimmed}`;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }

        setLoading(true);
        setFormError('');
        try {
            const payload = {
                ...formData,
                website_url: normalizeWebsiteUrl(formData.website_url),
            };
            if (access && !payload.password.trim()) {
                delete payload.password;
            }
            await onSubmit(payload);
        } catch (error) {
            console.error('Error submitting form:', error);
            setFormError(error?.message || 'Uložení selhalo');
        } finally {
            setLoading(false);
        }
    };

    const generatePassword = () => {
        const length = 12;
        const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
        let password = "";
        for (let i = 0; i < length; i++) {
            password += charset.charAt(Math.floor(Math.random() * charset.length));
        }
        setFormData(prev => ({ ...prev, password }));
    };

    return (
        <Modal
            title={access ? '✏️ Upravit přístup' : '➕ Přidat nový přístup'}
            onClose={onCancel}
            size="md"
            contentClassName="access-form-modal"
            onSubmit={handleSubmit}
            bodyClassName="access-form"
            footer={(
                <>
                    <button type="button" className="btn-cancel" onClick={onCancel} disabled={loading}>
                        Zrušit
                    </button>
                    <button type="submit" className="btn-submit" disabled={loading}>
                        {loading ? 'Ukládám...' : (
                            access ? 'Uložit změny' : 'Přidat přístup'
                        )}
                    </button>
                </>
            )}
        >
                    {formError && (
                        <p className="access-form__error" role="alert">{formError}</p>
                    )}
                    <div className="form-grid">
                        <div className="form-group">
                            <label htmlFor="company_name">
                                Název společnosti *
                            </label>
                            <input
                                type="text"
                                id="company_name"
                                name="company_name"
                                value={formData.company_name}
                                onChange={handleChange}
                                className={errors.company_name ? 'error' : ''}
                                placeholder="např. Google, Facebook, Apple..."
                            />
                            {errors.company_name && (
                                <span className="error-text">{errors.company_name}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="store">
                                Prodejna *
                            </label>
                            <select
                                id="store"
                                name="store"
                                value={formData.store}
                                onChange={handleChange}
                                className={errors.store ? 'error' : ''}
                            >
                                <option value="">Vyberte prodejnu</option>
                                {storeNames.map(storeName => (
                                    <option key={storeName} value={storeName}>
                                        {storeName}
                                    </option>
                                ))}
                            </select>
                            {errors.store && (
                                <span className="error-text">{errors.store}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="website_url">
                                URL adresa
                            </label>
                            <input
                                type="text"
                                id="website_url"
                                name="website_url"
                                value={formData.website_url}
                                onChange={handleChange}
                                className={errors.website_url ? 'error' : ''}
                                placeholder="např. example.com nebo https://example.com"
                            />
                            {errors.website_url && (
                                <span className="error-text">{errors.website_url}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="category">
                                Kategorie
                            </label>
                            <select
                                id="category"
                                name="category"
                                value={formData.category}
                                onChange={handleChange}
                            >
                                <option value="">Vyberte kategorii</option>
                                {categoryOptions.map((category) => (
                                    <option key={category} value={category}>
                                        {category}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="username">
                                Uživatelské jméno *
                            </label>
                            <input
                                type="text"
                                id="username"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                className={errors.username ? 'error' : ''}
                                placeholder="uživatelské jméno nebo email"
                            />
                            {errors.username && (
                                <span className="error-text">{errors.username}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">
                                {access ? 'Heslo (volitelné)' : 'Heslo *'}
                            </label>
                            <div className="password-input-group">
                                <input
                                    type="password"
                                    id="password"
                                    name="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    className={errors.password ? 'error' : ''}
                                    placeholder={access ? 'ponechat beze změny' : 'heslo'}
                                    autoComplete="new-password"
                                />
                                <button
                                    type="button"
                                    className="btn-generate"
                                    onClick={generatePassword}
                                    title="Generovat náhodné heslo"
                                >
                                    🎲
                                </button>
                            </div>
                            {access && !errors.password && (
                                <span className="form-hint">Nevyplňujte, pokud heslo neměníte</span>
                            )}
                            {errors.password && (
                                <span className="error-text">{errors.password}</span>
                            )}
                        </div>
                    </div>

                    <div className="form-group full-width">
                        <label htmlFor="description">
                            Popis
                        </label>
                        <textarea
                            id="description"
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            rows="3"
                            placeholder="Stručný popis účelu tohoto přístupu..."
                        />
                    </div>

                    <div className="form-group full-width">
                        <label htmlFor="notes">
                            Poznámky
                        </label>
                        <textarea
                            id="notes"
                            name="notes"
                            value={formData.notes}
                            onChange={handleChange}
                            rows="3"
                            placeholder="Dodatečné poznámky, instrukce nebo důležité informace..."
                        />
                    </div>
        </Modal>
    );
};

export default AccessForm; 