import React, { useState } from 'react';
import Post from './Post';
import './PostList.css';

const PostList = ({ 
    posts, 
    currentUser, 
    onDeletePost, 
    onAddReaction, 
    onRemoveReaction, 
    onAddComment, 
    onDeleteComment,
    onLoadComments,
}) => {
    const [expandedComments, setExpandedComments] = useState(new Set());
    const [loadingComments, setLoadingComments] = useState(new Set());

    const expandComments = (postId) => {
        setExpandedComments((prev) => new Set(prev).add(postId));
    };

    const toggleComments = async (post) => {
        const postId = post.id;
        const isExpanded = expandedComments.has(postId);

        if (!isExpanded) {
            const hasLocalComments = (post.komentare || []).length > 0;
            const expectedCount = post.pocet_komentaru || 0;
            if (!hasLocalComments && expectedCount > 0 && onLoadComments) {
                setLoadingComments((prev) => new Set(prev).add(postId));
                try {
                    await onLoadComments(postId);
                } finally {
                    setLoadingComments((prev) => {
                        const next = new Set(prev);
                        next.delete(postId);
                        return next;
                    });
                }
            }
            setExpandedComments((prev) => new Set(prev).add(postId));
            return;
        }

        setExpandedComments((prev) => {
            const next = new Set(prev);
            next.delete(postId);
            return next;
        });
    };

    if (posts.length === 0) {
        return (
            <div className="empty-posts">
                <div className="empty-icon">📝</div>
                <h3>Zatím žádné novinky</h3>
                <p>Buďte první, kdo přidá příspěvek!</p>
            </div>
        );
    }

    return (
        <div className="post-list">
            {posts.map(post => (
                <Post
                    key={post.id}
                    post={post}
                    currentUser={currentUser}
                    onDelete={onDeletePost}
                    onAddReaction={onAddReaction}
                    onRemoveReaction={onRemoveReaction}
                    onAddComment={onAddComment}
                    onDeleteComment={onDeleteComment}
                    showComments={expandedComments.has(post.id)}
                    commentsLoading={loadingComments.has(post.id)}
                    onToggleComments={() => toggleComments(post)}
                    onExpandComments={() => expandComments(post.id)}
                />
            ))}
        </div>
    );
};

export default PostList;
