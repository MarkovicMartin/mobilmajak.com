import React, { useState } from 'react';
import Modal from '../../components/Modal';
import { validateTelefonZakaznika } from './orderHelpers';
import './OrderForm.css';

const OrderForm = ({ onClose, onSubmit }) => {
    const [formData, setFormData] = useState({
        jmeno_zakaznika: '',
        prijmeni_zakaznika: '',
        telefon_zakaznika: '',
        typ_telefonu: '',
        dil: '',
        barva: '',
        poznamka: '',
        cena: '',
        dodavatel: '',
        servisni_cislo: '',
    });
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const validateForm = () => {
        const newErrors = {};
        const hasServiska = !!formData.servisni_cislo.trim();
        const hasCustomer = !!(formData.jmeno_zakaznika.trim() && formData.telefon_zakaznika.trim());

        if (!formData.typ_telefonu.trim()) {
            newErrors.typ_telefonu = 'Model je povinný';
        }

        if (!formData.dil.trim()) {
            newErrors.dil = 'Díl je povinný';
        }

        if (!formData.barva.trim()) {
            newErrors.barva = 'Barva je povinná';
        }

        if (!hasServiska && !hasCustomer) {
            newErrors.servisni_cislo = 'Vyplňte servisku, nebo jméno a telefon zákazníka';
            newErrors.jmeno_zakaznika = 'Nebo vyplňte jméno a telefon';
        }

        const telefonErr = validateTelefonZakaznika(formData.telefon_zakaznika);
        if (telefonErr) {
            newErrors.telefon_zakaznika = telefonErr;
        }

        if (formData.cena && isNaN(parseFloat(formData.cena))) {
            newErrors.cena = 'Cena musí být číslo';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }));

        if (errors[name]) {
            setErrors((prev) => ({
                ...prev,
                [name]: '',
            }));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        setIsSubmitting(true);

        try {
            const submitData = {
                ...formData,
                cena: formData.cena ? parseFloat(formData.cena) : null,
                servisni_cislo: formData.servisni_cislo.trim() || '',
                jmeno_zakaznika: formData.jmeno_zakaznika.trim() || '',
                prijmeni_zakaznika: formData.prijmeni_zakaznika.trim() || '',
                telefon_zakaznika: formData.telefon_zakaznika.trim() || '',
            };

            const result = await onSubmit(submitData);

            if (result.success) {
                onClose();
            } else if (result.error && typeof result.error === 'object') {
                setErrors(result.error);
            } else {
                alert(typeof result.error === 'string' && result.error.trim()
                    ? result.error
                    : 'Nepodařilo se vytvořit objednávku');
            }
        } catch (error) {
            console.error('Chyba při odesílání formuláře:', error);
            alert('Nepodařilo se vytvořit objednávku');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Modal
            title="Nová objednávka"
            onClose={onClose}
            size="sm"
            onSubmit={handleSubmit}
            bodyClassName="order-form"
            footer={(
                <>
                    <button type="button" className="btn-cancel" onClick={onClose}>
                        Zrušit
                    </button>
                    <button type="submit" className="btn-submit" disabled={isSubmitting}>
                        {isSubmitting ? 'Vytváření...' : 'Vytvořit objednávku'}
                    </button>
                </>
            )}
        >
            <div className="form-group">
                <label htmlFor="typ_telefonu">Model *</label>
                <input
                    type="text"
                    id="typ_telefonu"
                    name="typ_telefonu"
                    value={formData.typ_telefonu}
                    onChange={handleInputChange}
                    className={errors.typ_telefonu ? 'error' : ''}
                    placeholder="iPhone 14 Pro"
                    autoComplete="off"
                />
                {errors.typ_telefonu && (
                    <span className="error-message">{errors.typ_telefonu}</span>
                )}
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label htmlFor="dil">Díl *</label>
                    <input
                        type="text"
                        id="dil"
                        name="dil"
                        value={formData.dil}
                        onChange={handleInputChange}
                        className={errors.dil ? 'error' : ''}
                        placeholder="baterie"
                        autoComplete="off"
                    />
                    {errors.dil && (
                        <span className="error-message">{errors.dil}</span>
                    )}
                </div>

                <div className="form-group">
                    <label htmlFor="barva">Barva *</label>
                    <input
                        type="text"
                        id="barva"
                        name="barva"
                        value={formData.barva}
                        onChange={handleInputChange}
                        className={errors.barva ? 'error' : ''}
                        placeholder="černá"
                        autoComplete="off"
                    />
                    {errors.barva && (
                        <span className="error-message">{errors.barva}</span>
                    )}
                </div>
            </div>

            <div className="form-group">
                <label htmlFor="servisni_cislo">Serviska</label>
                <input
                    type="text"
                    id="servisni_cislo"
                    name="servisni_cislo"
                    value={formData.servisni_cislo}
                    onChange={handleInputChange}
                    className={errors.servisni_cislo ? 'error' : ''}
                    placeholder="952501099"
                    autoComplete="off"
                />
                {errors.servisni_cislo && (
                    <span className="error-message">{errors.servisni_cislo}</span>
                )}
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label htmlFor="jmeno_zakaznika">Jméno zákazníka</label>
                    <input
                        type="text"
                        id="jmeno_zakaznika"
                        name="jmeno_zakaznika"
                        value={formData.jmeno_zakaznika}
                        onChange={handleInputChange}
                        className={errors.jmeno_zakaznika ? 'error' : ''}
                        placeholder="Pan"
                        autoComplete="off"
                    />
                    {errors.jmeno_zakaznika && (
                        <span className="error-message">{errors.jmeno_zakaznika}</span>
                    )}
                </div>

                <div className="form-group">
                    <label htmlFor="prijmeni_zakaznika">Příjmení</label>
                    <input
                        type="text"
                        id="prijmeni_zakaznika"
                        name="prijmeni_zakaznika"
                        value={formData.prijmeni_zakaznika}
                        onChange={handleInputChange}
                        placeholder="Zákazník"
                        autoComplete="off"
                    />
                </div>
            </div>

            <div className="form-group">
                <label htmlFor="telefon_zakaznika">Telefon zákazníka</label>
                <input
                    type="tel"
                    id="telefon_zakaznika"
                    name="telefon_zakaznika"
                    value={formData.telefon_zakaznika}
                    onChange={handleInputChange}
                    className={errors.telefon_zakaznika ? 'error' : ''}
                    placeholder="777 123 456"
                    maxLength={20}
                    autoComplete="off"
                />
                {errors.telefon_zakaznika && (
                    <span className="error-message">{errors.telefon_zakaznika}</span>
                )}
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label htmlFor="cena">Cena (Kč)</label>
                    <input
                        type="number"
                        id="cena"
                        name="cena"
                        value={formData.cena}
                        onChange={handleInputChange}
                        className={errors.cena ? 'error' : ''}
                        placeholder="2000"
                        step="0.01"
                        min="0"
                    />
                    {errors.cena && (
                        <span className="error-message">{errors.cena}</span>
                    )}
                </div>

                <div className="form-group">
                    <label htmlFor="dodavatel">Dodavatel</label>
                    <input
                        type="text"
                        id="dodavatel"
                        name="dodavatel"
                        value={formData.dodavatel}
                        onChange={handleInputChange}
                        placeholder="skladem / ASWO…"
                        autoComplete="off"
                    />
                </div>
            </div>

            <div className="form-group">
                <label htmlFor="poznamka">Poznámka</label>
                <textarea
                    id="poznamka"
                    name="poznamka"
                    value={formData.poznamka}
                    onChange={handleInputChange}
                    placeholder="Další poznámky…"
                    rows="2"
                />
            </div>
        </Modal>
    );
};

export default OrderForm;
