import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { categoryAPI } from '../services/api';
import './CategoryManager.css';

const CategoryManager = () => {
    const { user } = useAuth();
    const [categories, setCategories] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [newCategory, setNewCategory] = useState({
        nazev: '',
        barva: '#0066cc',
        ikona: ''
    });
    const [isLoading, setIsLoading] = useState(false);

    // Hook musí být vždy na začátku, před jakýmkoli podmíněným return
    useEffect(() => {
        // Načteme kategorie pouze pokud je uživatel admin
        if (user && user.role === 'ADMIN') {
            fetchCategories();
        }
    }, [user]);

    // Kontrola práv admina - až po hooks
    if (!user || user.role !== 'ADMIN') {
        return (
            <div className="category-manager-error">
                <p>Nemáte oprávnění pro správu kategorií.</p>
            </div>
        );
    }

    const fetchCategories = async () => {
        try {
            const response = await categoryAPI.getCategories();
            setCategories(response);
        } catch (error) {
            console.error('Chyba při načítání kategorií:', error);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const response = await categoryAPI.createCategory(newCategory);
            await fetchCategories(); // Obnovit seznam
            setNewCategory({ nazev: '', barva: '#0066cc', ikona: '' });
            setShowForm(false);
            alert('Kategorie byla úspěšně vytvořena!');
        } catch (error) {
            const errorMessage = error.response?.data?.nazev?.[0] || error.message || 'Neznámá chyba';
            alert('Chyba při vytváření kategorie: ' + errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDelete = async (categoryId) => {
        if (!window.confirm('Opravdu chcete smazat tuto kategorii?')) {
            return;
        }

        try {
            await categoryAPI.deleteCategory(categoryId);
            await fetchCategories(); // Obnovit seznam
            alert('Kategorie byla smazána!');
        } catch (error) {
            alert('Chyba při mazání kategorie: ' + error.message);
        }
    };

    return (
        <div className="category-manager">
            <div className="category-manager-header">
                <h2>Správa kategorií</h2>
                <button 
                    className="add-category-btn"
                    onClick={() => setShowForm(!showForm)}
                >
                    {showForm ? 'Zrušit' : '+ Přidat kategorii'}
                </button>
            </div>

            {showForm && (
                <form className="category-form" onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Název kategorie:</label>
                        <input
                            type="text"
                            value={newCategory.nazev}
                            onChange={(e) => setNewCategory({...newCategory, nazev: e.target.value})}
                            required
                            maxLength={100}
                        />
                    </div>
                    
                    <div className="form-group">
                        <label>Barva:</label>
                        <input
                            type="color"
                            value={newCategory.barva}
                            onChange={(e) => setNewCategory({...newCategory, barva: e.target.value})}
                        />
                    </div>
                    
                    <div className="form-group">
                        <label>CSS ikona (volitelné):</label>
                        <input
                            type="text"
                            value={newCategory.ikona}
                            onChange={(e) => setNewCategory({...newCategory, ikona: e.target.value})}
                            placeholder="např. fas fa-star"
                        />
                    </div>
                    
                    <div className="form-preview">
                        <span>Náhled:</span>
                        <span 
                            className="category-preview"
                            style={{ backgroundColor: newCategory.barva }}
                        >
                            {newCategory.ikona && <i className={newCategory.ikona}></i>}
                            {newCategory.nazev || 'Název kategorie'}
                        </span>
                    </div>
                    
                    <div className="form-buttons">
                        <button type="submit" disabled={isLoading}>
                            {isLoading ? 'Vytváření...' : 'Vytvořit'}
                        </button>
                        <button type="button" onClick={() => setShowForm(false)}>
                            Zrušit
                        </button>
                    </div>
                </form>
            )}

            <div className="categories-list">
                <h3>Existující kategorie ({categories.length})</h3>
                {categories.length === 0 ? (
                    <p>Žádné kategorie nebyly nalezeny.</p>
                ) : (
                    <div className="categories-grid">
                        {categories.map(category => (
                            <div key={category.id} className="category-item">
                                <span 
                                    className="category-badge"
                                    style={{ backgroundColor: category.barva }}
                                >
                                    {category.ikona && <i className={category.ikona}></i>}
                                    {category.nazev}
                                </span>
                                <button 
                                    className="delete-category-btn"
                                    onClick={() => handleDelete(category.id)}
                                    title="Smazat kategorii"
                                >
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CategoryManager; 