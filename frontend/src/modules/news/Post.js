import React, { useState } from 'react';
import CommentForm from './CommentForm';
import CommentList from './CommentList';
import {
    REACTION_EMOJI,
    REACTION_ORDER,
    reactionNamesForType,
    reactionSummaryLines,
    reactionsByType,
} from './reactionUtils';
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
    commentsLoading,
    onToggleComments,
    onExpandComments,
}) => {
    const [showCommentForm, setShowCommentForm] = useState(false);

    const commentCount = Math.max(post.pocet_komentaru || 0, (post.komentare || []).length);
    const reactionSummary = reactionSummaryLines(post.reakce);

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

    const getReactionCount = (type) => reactionsByType(post.reakce, type).length;

    const isMyReaction = (type) => post.moje_reakce && post.moje_reakce.typ === type;

    const canDelete = () => currentUser.role === 'ADMIN' || currentUser.id === post.autor.id;

    const handleDelete = () => {
        if (window.confirm('Opravdu chcete smazat tento příspěvek?')) {
            onDelete(post.id);
        }
    };

    const handleAddComment = async (postId, commentData) => {
        await onAddComment(postId, commentData);
        onExpandComments?.(postId);
        setShowCommentForm(false);
    };

    const renderReactionButton = (type) => {
        const count = getReactionCount(type);
        const names = reactionNamesForType(post.reakce, type);
        const emoji = REACTION_EMOJI[type];

        return (
            <span key={type} className="reaction-btn-wrap">
                <button 
                    type="button"
                    className={`reaction-btn ${isMyReaction(type) ? 'active' : ''}`}
                    onClick={() => handleReaction(type)}
                    aria-label={`${emoji} reakce`}
                >
                    {emoji} {count > 0 && count}
                </button>
                {count > 0 && (
                    <span className="reaction-tooltip" role="tooltip">
                        <strong>{emoji}</strong>
                        <span>{names.join(', ')}</span>
                    </span>
                )}
            </span>
        );
    };

    const renderFile = (file) => {
        if (file.typ === 'obrazek') {
            return (
                <div key={file.id} className="file-preview">
                    <img src={file.url} alt={file.nazev} className="image-preview" />
                </div>
            );
        }
        return (
            <div key={file.id} className="file-preview">
                <a href={file.url} target="_blank" rel="noopener noreferrer" className="file-link">
                    📎 {file.nazev}
                </a>
            </div>
        );
    };

    return (
        <div className="post" id={`post-${post.id}`}>
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
                    <button type="button" className="delete-btn" onClick={handleDelete}>
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
                {post.pocet_reakci > 0 && (
                    <span className="reactions-summary-wrap">
                        <span className="reactions-count">
                            {post.pocet_reakci} reakcí
                        </span>
                        {reactionSummary.length > 0 && (
                            <span className="reaction-tooltip reaction-tooltip--summary" role="tooltip">
                                {reactionSummary.map((line) => (
                                    <span key={line} className="reaction-summary-line">{line}</span>
                                ))}
                            </span>
                        )}
                    </span>
                )}
                {commentCount > 0 && (
                    <button
                        type="button"
                        className="comments-count-btn"
                        onClick={onToggleComments}
                    >
                        {commentCount} komentářů
                    </button>
                )}
            </div>

            <div className="post-actions">
                <div className="reactions">
                    {REACTION_ORDER.map(renderReactionButton)}
                </div>

                <div className="action-buttons">
                    <button 
                        type="button"
                        className="comment-btn"
                        onClick={() => setShowCommentForm(!showCommentForm)}
                    >
                        💬 Komentovat
                    </button>
                    {commentCount > 0 && (
                        <button 
                            type="button"
                            className="show-comments-btn"
                            onClick={onToggleComments}
                        >
                            {commentsLoading
                                ? 'Načítám…'
                                : showComments
                                    ? 'Skrýt komentáře'
                                    : 'Zobrazit komentáře'}
                        </button>
                    )}
                </div>
            </div>

            {showCommentForm && (
                <CommentForm
                    postId={post.id}
                    onSubmit={handleAddComment}
                    onCancel={() => setShowCommentForm(false)}
                />
            )}

            {showComments && (
                commentsLoading ? (
                    <div className="comments-loading">Načítám komentáře…</div>
                ) : (
                    <CommentList
                        comments={post.komentare || []}
                        currentUser={currentUser}
                        onDeleteComment={onDeleteComment}
                    />
                )
            )}
        </div>
    );
};

export default Post;
