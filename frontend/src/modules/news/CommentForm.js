import React, { useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import './CommentForm.css';

const CommentForm = ({ postId, onSubmit, onCancel }) => {
    const { user } = useAuth();
    const [content, setContent] = useState('');
    const [files, setFiles] = useState([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const fileInputRef = useRef(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!content.trim() && files.length === 0) {
            alert('Zadejte obsah nebo nahrajte soubor');
            return;
        }

        setIsSubmitting(true);
        
        try {
            // Předáme data přes callback místo přímého API volání
            await onSubmit(postId, {
                obsah: content
            });
            
            // Reset formuláře po úspěšném odeslání
            setContent('');
            setFiles([]);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
            
        } catch (error) {
            console.error('Chyba při vytváření komentáře:', error);
            alert('Chyba při vytváření komentáře: ' + (error.message || error));
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

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div className="comment-form">
            <div className="comment-author">
                <div className="author-avatar">
                    {user?.inicialy || 'U'}
                </div>
                <div className="author-info">
                    <span className="author-name">{user?.jmeno} {user?.prijmeni}</span>
                </div>
            </div>

            <form onSubmit={handleSubmit}>
                <div className="comment-content">
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="Napište komentář..."
                        rows={3}
                        maxLength={500}
                    />
                    <div className="content-counter">
                        {content.length}/500
                    </div>
                </div>

                {files.length > 0 && (
                    <div className="selected-files">
                        <h5>Vybrané soubory:</h5>
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

                <div className="comment-actions">
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
                            {isSubmitting ? 'Přidávám...' : 'Přidat komentář'}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    );
};

export default CommentForm; 