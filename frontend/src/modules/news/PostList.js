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
    onDeleteComment 
}) => {
    const [expandedComments, setExpandedComments] = useState(new Set());

    const toggleComments = (postId) => {
        const newExpanded = new Set(expandedComments);
        if (newExpanded.has(postId)) {
            newExpanded.delete(postId);
        } else {
            newExpanded.add(postId);
        }
        setExpandedComments(newExpanded);
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
                    onToggleComments={() => toggleComments(post.id)}
                />
            ))}
        </div>
    );
};

export default PostList; 