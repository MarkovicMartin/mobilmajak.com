import React, { useState } from 'react';
import CommentForm from './CommentForm';
import CommentList from './CommentList';
import './Post.css';

const Post = ({ 
    post, 
    currentUser, 
    onDelete, 
    onAddReaction, 
    onRemoveReaction, 
    onAddComment, 
    onDeleteComment,
    showComments,
    onToggleComments
}) => {
    const [showCommentForm, setShowCommentForm] = useState(false);

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

    const handleReaction = (reactionType) => {
        if (post.moje_reakce && post.moje_reakce.typ === reactionType) {
            onRemoveReaction(post.id);
        } else {
            onAddReaction(post.id, reactionType);
        }
    };

    const getReactionCount = (type) => {
        return post.reakce.filter(r => r.typ === type).length;
    };

    const isMyReaction = (type) => {
        return post.moje_reakce && post.moje_reakce.typ === type;
    };

    const canDelete = () => {
        return currentUser.role === 'ADMIN' || currentUser.id === post.autor.id;
    };

    const handleDelete = () => {
        if (window.confirm('Opravdu chcete smazat tento příspěvek?')) {
            onDelete(post.id);
        }
    };

    const renderFile = (file) => {
        if (file.typ === 'obrazek') {
            return (
                <div key={file.id} className="file-preview">
                    <img src={file.url} alt={file.nazev} className="image-preview" />
                </div>
            );
        } else {
            return (
                <div key={file.id} className="file-preview">
                    <a href={file.url} target="_blank" rel="noopener noreferrer" className="file-link">
                        📎 {file.nazev}
                    </a>
                </div>
            );
        }
    };

    return (
        <div className="post">
            <div className="post-header">
                <div className="post-author">
                    <div className="author-avatar">
                        {post.autor.inicialy || 'U'}
                    </div>
                    <div className="author-info">
                        <span className="author-name">{post.autor.jmeno} {post.autor.prijmeni}</span>
                        <span className="post-date">{formatDate(post.datum_vytvoreni)}</span>
                    </div>
                </div>
                {canDelete() && (
                    <button className="delete-btn" onClick={handleDelete}>
                        🗑️
                    </button>
                )}
            </div>

            <div className="post-content">
                <p>{post.obsah}</p>
                
                {post.soubory && post.soubory.length > 0 && (
                    <div className="post-files">
                        {post.soubory.map(renderFile)}
                    </div>
                )}
            </div>

            {post.kategorie && post.kategorie.length > 0 && (
                <div className="post-categories">
                    {post.kategorie.map(category => (
                        <span 
                            key={category.id}
                            className="category-tag"
                            style={{ backgroundColor: category.barva }}
                        >
                            {category.ikona && <i className={category.ikona}></i>}
                            {category.nazev}
                        </span>
                    ))}
                </div>
            )}

            <div className="post-stats">
                <span className="reactions-count">
                    {post.pocet_reakci > 0 && `${post.pocet_reakci} reakcí`}
                </span>
                <span className="comments-count">
                    {post.pocet_komentaru > 0 && `${post.pocet_komentaru} komentářů`}
                </span>
            </div>

            <div className="post-actions">
                <div className="reactions">
                    <button 
                        className={`reaction-btn ${isMyReaction('like') ? 'active' : ''}`}
                        onClick={() => handleReaction('like')}
                    >
                        👍 {getReactionCount('like') > 0 && getReactionCount('like')}
                    </button>
                    <button 
                        className={`reaction-btn ${isMyReaction('srdce') ? 'active' : ''}`}
                        onClick={() => handleReaction('srdce')}
                    >
                        ❤️ {getReactionCount('srdce') > 0 && getReactionCount('srdce')}
                    </button>
                    <button 
                        className={`reaction-btn ${isMyReaction('smich') ? 'active' : ''}`}
                        onClick={() => handleReaction('smich')}
                    >
                        😂 {getReactionCount('smich') > 0 && getReactionCount('smich')}
                    </button>
                    <button 
                        className={`reaction-btn ${isMyReaction('prekvapeni') ? 'active' : ''}`}
                        onClick={() => handleReaction('prekvapeni')}
                    >
                        😮 {getReactionCount('prekvapeni') > 0 && getReactionCount('prekvapeni')}
                    </button>
                </div>

                <div className="action-buttons">
                    <button 
                        className="comment-btn"
                        onClick={() => setShowCommentForm(!showCommentForm)}
                    >
                        💬 Komentovat
                    </button>
                    {post.pocet_komentaru > 0 && (
                        <button 
                            className="show-comments-btn"
                            onClick={onToggleComments}
                        >
                            {showComments ? 'Skrýt komentáře' : 'Zobrazit komentáře'}
                        </button>
                    )}
                </div>
            </div>

            {showCommentForm && (
                <CommentForm
                    postId={post.id}
                    onSubmit={onAddComment}
                    onCancel={() => setShowCommentForm(false)}
                />
            )}

            {showComments && (
                <CommentList
                    comments={post.komentare}
                    currentUser={currentUser}
                    onDeleteComment={onDeleteComment}
                />
            )}
        </div>
    );
};

export default Post; 