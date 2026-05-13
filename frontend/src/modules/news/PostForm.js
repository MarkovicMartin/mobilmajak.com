import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import './PostForm.css';

const PostForm = ({ onSubmit, onCancel }) => {
    const { user } = useAuth();
    const [content, setContent] = useState('');
    const [files, setFiles] = useState([]);
    const [categories, setCategories] = useState([]);
    const [selectedCategories, setSelectedCategories] = useState([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const fileInputRef = useRef(null);

    // Načtení kategorií při inicializaci komponenty
    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const response = await api.get('/news/kategorie/');
                setCategories(response.data);
            } catch (error) {
                console.error('Chyba při načítání kategorií:', error);
            }
        };
        
        fetchCategories();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!content.trim() && files.length === 0) {
            alert('Zadejte obsah nebo nahrajte soubor');
            return;
        }

        setIsSubmitting(true);
        
        try {
            // Debug: Zobrazím co posíláme na backend
            console.log('DEBUG: Odesílám na backend:', { 
                obsah: content,
                kategorie: selectedCategories 
            });
            
            // Nejdříve vytvoříme příspěvek
            const postResponse = await api.post('/news/', {
                obsah: content,
                kategorie: selectedCategories,
            });

            const newPost = postResponse.data;
            console.log('Nový příspěvek:', newPost); // Debug

            // Pak nahrajeme soubory
            const uploadedFiles = [];
            for (const file of files) {
                const formData = new FormData();
                formData.append('soubor', file);

                const fileResponse = await api.post(`/news/${newPost.id}/soubory/`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });

                const uploadedFile = fileResponse.data;
                uploadedFiles.push(uploadedFile);
            }

            // Vytvoříme kompletní příspěvek se soubory
            const completePost = {
                ...newPost,
                soubory: uploadedFiles
            };

            // Necháme parent komponentu zpracovat nový příspěvek
            onSubmit(completePost);
            setContent('');
            setFiles([]);
            setSelectedCategories([]);
        } catch (error) {
            alert('Chyba při vytváření příspěvku: ' + error.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleFileSelect = (e) => {
        const selectedFiles = Array.from(e.target.files);
        setFiles(prev => [...prev, ...selectedFiles]);
    };

    const removeFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleCategoryToggle = (categoryId) => {
        setSelectedCategories(prev => {
            if (prev.includes(categoryId)) {
                return prev.filter(id => id !== categoryId);
            } else {
                return [...prev, categoryId];
            }
        });
    };

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div className="post-form-overlay">
            <div className="post-form">
                <div className="post-form-header">
                    <h3>Nový příspěvek</h3>
                    <button className="close-btn" onClick={onCancel}>✕</button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="post-author">
                        <div className="author-avatar">
                            {user?.inicialy || 'U'}
                        </div>
                        <div className="author-info">
                            <span className="author-name">{user?.jmeno} {user?.prijmeni}</span>
                        </div>
                    </div>

                    <div className="post-content">
                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            placeholder="Co se děje?"
                            rows={4}
                            maxLength={1000}
                        />
                        <div className="content-counter">
                            {content.length}/1000
                        </div>
                    </div>

                    {categories.length > 0 && (
                        <div className="category-selector">
                            <h4>Kategorie:</h4>
                            <div className="category-options">
                                {categories.map(category => (
                                    <label key={category.id} className="category-option">
                                        <input
                                            type="checkbox"
                                            checked={selectedCategories.includes(category.id)}
                                            onChange={() => handleCategoryToggle(category.id)}
                                        />
                                        <span 
                                            className="category-badge"
                                            style={{ backgroundColor: category.barva }}
                                        >
                                            {category.ikona && <i className={category.ikona}></i>}
                                            {category.nazev}
                                        </span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    )}

                    {files.length > 0 && (
                        <div className="selected-files">
                            <h4>Vybrané soubory:</h4>
                            {files.map((file, index) => (
                                <div key={index} className="file-item">
                                    <span className="file-name">{file.name}</span>
                                    <span className="file-size">({formatFileSize(file.size)})</span>
                                    <button 
                                        type="button" 
                                        className="remove-file-btn"
                                        onClick={() => removeFile(index)}
                                    >
                                        ✕
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="post-actions">
                        <div className="file-upload">
                            <button 
                                type="button" 
                                className="upload-btn"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                📎 Přidat soubor
                            </button>
                            <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                onChange={handleFileSelect}
                                style={{ display: 'none' }}
                                accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.txt"
                            />
                        </div>

                        <div className="form-buttons">
                            <button 
                                type="button" 
                                className="cancel-btn"
                                onClick={onCancel}
                                disabled={isSubmitting}
                            >
                                Zrušit
                            </button>
                            <button 
                                type="submit" 
                                className="submit-btn"
                                disabled={isSubmitting || (!content.trim() && files.length === 0)}
                            >
                                {isSubmitting ? 'Vytvářím...' : 'Publikovat'}
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default PostForm; 