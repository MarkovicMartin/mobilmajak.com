import React from 'react';
import './CommentList.css';

const CommentList = ({ comments, currentUser, onDeleteComment }) => {
    const formatDate = (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffInHours = (now - date) / (1000 * 60 * 60);
        
        if (diffInHours < 1) {
            const diffInMinutes = Math.floor((now - date) / (1000 * 60));
            return `před ${diffInMinutes} min`;
        } else if (diffInHours < 24) {
            return `před ${Math.floor(diffInHours)} h`;
        } else {
            return date.toLocaleDateString('cs-CZ');
        }
    };

    const canDeleteComment = (comment) => {
        return currentUser.role === 'ADMIN' || currentUser.id === comment.autor.id;
    };

    const handleDeleteComment = (commentId) => {
        if (window.confirm('Opravdu chcete smazat tento komentář?')) {
            onDeleteComment(commentId);
        }
    };

    const renderFile = (file) => {
        if (file.typ === 'obrazek') {
            return (
                <div key={file.id} className="comment-file">
                    <img src={file.url} alt={file.nazev} className="comment-image" />
                </div>
            );
        } else {
            return (
                <div key={file.id} className="comment-file">
                    <a href={file.url} target="_blank" rel="noopener noreferrer" className="comment-file-link">
                        📎 {file.nazev}
                    </a>
                </div>
            );
        }
    };

    if (comments.length === 0) {
        return (
            <div className="comments-section">
                <div className="no-comments">
                    <p>Zatím žádné komentáře</p>
                </div>
            </div>
        );
    }

    return (
        <div className="comments-section">
            <h4>Komentáře ({comments.length})</h4>
            <div className="comments-list">
                {comments.map(comment => (
                    <div key={comment.id} className="comment">
                        <div className="comment-header">
                            <div className="comment-author">
                                <div className="author-avatar">
                                    {comment.autor.inicialy || 'U'}
                                </div>
                                <div className="author-info">
                                    <span className="author-name">
                                        {comment.autor.jmeno} {comment.autor.prijmeni}
                                    </span>
                                    <span className="comment-date">
                                        {formatDate(comment.datum_vytvoreni)}
                                    </span>
                                </div>
                            </div>
                            {canDeleteComment(comment) && (
                                <button 
                                    className="delete-comment-btn"
                                    onClick={() => handleDeleteComment(comment.id)}
                                >
                                    🗑️
                                </button>
                            )}
                        </div>

                        <div className="comment-content">
                            <p>{comment.obsah}</p>
                            
                            {comment.soubory && comment.soubory.length > 0 && (
                                <div className="comment-files">
                                    {comment.soubory.map(renderFile)}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default CommentList; 