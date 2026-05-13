import React, { useState } from 'react';
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
        servisni_cislo: ''
    });
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Předvolené možnosti pro rychlejší zadávání
    const phoneTypes = [
        'iPhone 13', 'iPhone 14', 'iPhone 15', 'iPhone 12',
        'Samsung Galaxy S23', 'Samsung Galaxy S24', 'Samsung Galaxy A54',
        'Huawei P40', 'Xiaomi Redmi Note 13', 'OnePlus Nord'
    ];

    const partTypes = [
        'sklíčko fotáku', 'baterie', 'LCD display', 'sklíčko', 'reproduktor',
        'mikrofon', 'kamera', 'flex tlačítek', 'konektor nabíjení',
        'home button', 'flex kamery', 'sluchátko'
    ];

    const colors = [
        'černá', 'bílá', 'modrá', 'červená', 'zelená', 'zlatá', 'stříbrná',
        'růžová', 'fialová', 'žlutá', 'oranžová'
    ];

    // Validace formuláře
    const validateForm = () => {
        const newErrors = {};

        if (!formData.jmeno_zakaznika.trim()) {
            newErrors.jmeno_zakaznika = 'Jméno zákazníka je povinné';
        }

        if (!formData.prijmeni_zakaznika.trim()) {
            newErrors.prijmeni_zakaznika = 'Příjmení zákazníka je povinné';
        }

        if (!formData.telefon_zakaznika.trim()) {
            newErrors.telefon_zakaznika = 'Telefon zákazníka je povinný';
        } else if (!/^(\+420\s?)?[0-9\s]{9,}$/.test(formData.telefon_zakaznika)) {
            newErrors.telefon_zakaznika = 'Nesprávný formát telefonu';
        }

        if (!formData.typ_telefonu.trim()) {
            newErrors.typ_telefonu = 'Typ telefonu je povinný';
        }

        if (!formData.dil.trim()) {
            newErrors.dil = 'Díl je povinný';
        }

        if (formData.cena && isNaN(parseFloat(formData.cena))) {
            newErrors.cena = 'Cena musí být číslo';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    // Zpracování změny vstupů
    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));

        // Vymaž chybu pro toto pole
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }
    };

    // Odeslání formuláře
    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }

        setIsSubmitting(true);

        try {
            // Připravíme data pro odeslání
            const submitData = {
                ...formData,
                // Převedeme cenu na number pokud je zadána
                cena: formData.cena ? parseFloat(formData.cena) : null
            };

            const result = await onSubmit(submitData);
            
            if (result.success) {
                onClose();
            } else {
                // Zobrazíme chyby z backendu
                if (typeof result.error === 'object') {
                    setErrors(result.error);
                } else {
                    alert(result.error);
                }
            }
        } catch (error) {
            console.error('Chyba při odesílání formuláře:', error);
            alert('Nepodařilo se vytvořit objednávku');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="order-form-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>➕ Nová objednávka</h2>
                    <button className="close-btn" onClick={onClose}>✕</button>
                </div>

                <form onSubmit={handleSubmit} className="order-form">
                    {/* Informace o zákazníkovi */}
                    <div className="form-section">
                        <h3>👤 Zákazník</h3>
                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="jmeno_zakaznika">Jméno *</label>
                                <input
                                    type="text"
                                    id="jmeno_zakaznika"
                                    name="jmeno_zakaznika"
                                    value={formData.jmeno_zakaznika}
                                    onChange={handleInputChange}
                                    className={errors.jmeno_zakaznika ? 'error' : ''}
                                    placeholder="Jan"
                                />
                                {errors.jmeno_zakaznika && (
                                    <span className="error-message">{errors.jmeno_zakaznika}</span>
                                )}
                            </div>
                            
                            <div className="form-group">
                                <label htmlFor="prijmeni_zakaznika">Příjmení *</label>
                                <input
                                    type="text"
                                    id="prijmeni_zakaznika"
                                    name="prijmeni_zakaznika"
                                    value={formData.prijmeni_zakaznika}
                                    onChange={handleInputChange}
                                    className={errors.prijmeni_zakaznika ? 'error' : ''}
                                    placeholder="Novák"
                                />
                                {errors.prijmeni_zakaznika && (
                                    <span className="error-message">{errors.prijmeni_zakaznika}</span>
                                )}
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="telefon_zakaznika">Telefon *</label>
                            <input
                                type="tel"
                                id="telefon_zakaznika"
                                name="telefon_zakaznika"
                                value={formData.telefon_zakaznika}
                                onChange={handleInputChange}
                                className={errors.telefon_zakaznika ? 'error' : ''}
                                placeholder="+420 123 456 789"
                            />
                            {errors.telefon_zakaznika && (
                                <span className="error-message">{errors.telefon_zakaznika}</span>
                            )}
                        </div>
                    </div>

                    {/* Informace o dílu */}
                    <div className="form-section">
                        <h3>📱 Díl/Produkt</h3>
                        <div className="form-group">
                            <label htmlFor="typ_telefonu">Typ telefonu *</label>
                            <input
                                type="text"
                                id="typ_telefonu"
                                name="typ_telefonu"
                                value={formData.typ_telefonu}
                                onChange={handleInputChange}
                                className={errors.typ_telefonu ? 'error' : ''}
                                placeholder="iPhone 13"
                                list="phone-types"
                            />
                            <datalist id="phone-types">
                                {phoneTypes.map(type => (
                                    <option key={type} value={type} />
                                ))}
                            </datalist>
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
                                    list="part-types"
                                />
                                <datalist id="part-types">
                                    {partTypes.map(part => (
                                        <option key={part} value={part} />
                                    ))}
                                </datalist>
                                {errors.dil && (
                                    <span className="error-message">{errors.dil}</span>
                                )}
                            </div>

                            <div className="form-group">
                                <label htmlFor="barva">Barva</label>
                                <input
                                    type="text"
                                    id="barva"
                                    name="barva"
                                    value={formData.barva}
                                    onChange={handleInputChange}
                                    placeholder="černá"
                                    list="colors"
                                />
                                <datalist id="colors">
                                    {colors.map(color => (
                                        <option key={color} value={color} />
                                    ))}
                                </datalist>
                            </div>
                        </div>
                    </div>

                    {/* Doplňující informace */}
                    <div className="form-section">
                        <h3>📝 Doplňující informace</h3>
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
                                    placeholder="1500"
                                    step="0.01"
                                    min="0"
                                />
                                {errors.cena && (
                                    <span className="error-message">{errors.cena}</span>
                                )}
                            </div>

                            <div className="form-group">
                                <label htmlFor="servisni_cislo">Servisní číslo</label>
                                <input
                                    type="text"
                                    id="servisni_cislo"
                                    name="servisni_cislo"
                                    value={formData.servisni_cislo}
                                    onChange={handleInputChange}
                                    placeholder="S123456"
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="dodavatel">Dodavatel</label>
                            <input
                                type="text"
                                id="dodavatel"
                                name="dodavatel"
                                value={formData.dodavatel}
                                onChange={handleInputChange}
                                placeholder="ASWO, Globus, atd."
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="poznamka">Poznámka</label>
                            <textarea
                                id="poznamka"
                                name="poznamka"
                                value={formData.poznamka}
                                onChange={handleInputChange}
                                placeholder="Další poznámky k objednávce..."
                                rows="3"
                            />
                        </div>
                    </div>

                    {/* Tlačítka */}
                    <div className="form-actions">
                        <button 
                            type="button" 
                            className="btn btn-secondary"
                            onClick={onClose}
                            disabled={isSubmitting}
                        >
                            Zrušit
                        </button>
                        <button 
                            type="submit" 
                            className="btn btn-primary"
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? (
                                <>
                                    <span className="spinner-small"></span>
                                    Vytváření...
                                </>
                            ) : (
                                '✅ Vytvořit objednávku'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default OrderForm; 