import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { PageHeader } from '../../components/ui';
import PostForm from './PostForm';
import PostList from './PostList';
import './NewsModule.css';

const NewsModule = () => {
    const { user } = useAuth();
    const location = useLocation();
    const [posts, setPosts] = useState([]);
    const [categories, setCategories] = useState([]);
    const [selectedCategories, setSelectedCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showPostForm, setShowPostForm] = useState(false);

    // Načtení novinek
    const fetchPosts = async () => {
        try {
            setLoading(true);
            const response = await api.get('/news/');
            setPosts(response.data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Načtení kategorií
    const fetchCategories = async () => {
        try {
            const response = await api.get('/news/kategorie/');
            setCategories(response.data);
        } catch (err) {
            console.error('Chyba při načítání kategorií:', err);
        }
    };

    useEffect(() => {
        fetchPosts();
        fetchCategories();
    }, []);

    useEffect(() => {
        if (loading) return;
        const match = (location.hash || '').match(/^#post-(\d+)$/);
        if (!match) return;
        const el = document.getElementById(`post-${match[1]}`);
        if (el) {
            requestAnimationFrame(() => {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }
    }, [loading, location.hash, posts]);

    // Přidání nového příspěvku
    const handleAddPost = async (newPost) => {
        try {
            // Nový příspěvek už byl vytvořen v PostForm, jen ho přidáme do seznamu
            const completePost = {
                ...newPost,
                reakce: newPost.reakce || [],
                komentare: newPost.komentare || [],
                soubory: newPost.soubory || [],
                pocet_reakci: newPost.pocet_reakci || 0,
                pocet_komentaru: newPost.pocet_komentaru || 0,
                moje_reakce: newPost.moje_reakce || null
            };
            setPosts(prevPosts => [completePost, ...prevPosts]);
            setShowPostForm(false);
        } catch (err) {
            setError(err.message);
        }
    };

    // Smazání příspěvku
    const handleDeletePost = async (postId) => {
        try {
            await api.delete(`/news/${postId}/`);
            setPosts(prevPosts => prevPosts.filter(post => post.id !== postId));
        } catch (err) {
            setError(err.message);
        }
    };

    // Přidání reakce
    const handleAddReaction = async (postId, reactionType) => {
        try {
            const requestData = {
                novinka: postId,
                typ: reactionType,
            };
            console.log('Odesílám reakci:', requestData);

            const response = await api.post('/news/reakce/', requestData);

            const updatedReaction = response.data;
            console.log('Odpověď na reakci:', updatedReaction);
            setPosts(prevPosts => 
                prevPosts.map(post => 
                    post.id === postId 
                        ? {
                            ...post,
                            reakce: post.reakce.filter(r => r.uzivatel.id !== user.id).concat([updatedReaction]),
                            moje_reakce: updatedReaction,
                            pocet_reakci: post.moje_reakce ? post.pocet_reakci : post.pocet_reakci + 1
                        }
                        : post
                )
            );
        } catch (err) {
            setError(err.message);
        }
    };

    // Odstranění reakce
    const handleRemoveReaction = async (postId) => {
        try {
            await api.delete(`/news/${postId}/reakce/`);

            setPosts(prevPosts => 
                prevPosts.map(post => 
                    post.id === postId 
                        ? {
                            ...post,
                            reakce: post.reakce.filter(r => r.uzivatel.id !== user.id),
                            moje_reakce: null,
                            pocet_reakci: Math.max(0, post.pocet_reakci - 1)
                        }
                        : post
                )
            );
        } catch (err) {
            setError(err.message);
        }
    };

    // Přidání komentáře
    const handleAddComment = async (postId, commentData) => {
        try {
            const response = await api.post(`/news/${postId}/komentare/`, {
                ...commentData,
                novinka: postId,
            });

            const newComment = response.data;
            const completeComment = {
                ...newComment,
                soubory: newComment.soubory || []
            };
            setPosts(prevPosts => 
                prevPosts.map(post => 
                    post.id === postId 
                        ? {
                            ...post,
                            komentare: [...(post.komentare || []), completeComment],
                            pocet_komentaru: (post.pocet_komentaru || 0) + 1,
                        }
                        : post
                )
            );
            return completeComment;
        } catch (err) {
            setError(err.message);
            throw err;
        }
    };

    // Načtení komentářů k příspěvku (lazy load při rozkliku)
    const handleLoadComments = async (postId) => {
        const response = await api.get(`/news/${postId}/komentare/`);
        setPosts(prevPosts =>
            prevPosts.map(post =>
                post.id === postId
                    ? { ...post, komentare: response.data }
                    : post
            )
        );
        return response.data;
    };

    // Smazání komentáře
    const handleDeleteComment = async (commentId) => {
        try {
            await api.delete(`/news/komentare/${commentId}/`);

            setPosts(prevPosts => 
                prevPosts.map(post => {
                    const hadComment = (post.komentare || []).some((c) => c.id === commentId);
                    return {
                        ...post,
                        komentare: (post.komentare || []).filter(comment => comment.id !== commentId),
                        pocet_komentaru: hadComment
                            ? Math.max(0, (post.pocet_komentaru || 0) - 1)
                            : post.pocet_komentaru,
                    };
                })
            );
        } catch (err) {
            setError(err.message);
        }
    };

    // Filtrování příspěvků podle kategorií
    const filteredPosts = posts.filter(post => {
        if (selectedCategories.length === 0) {
            return true; // Zobrazit všechny příspěvky, pokud není vybrána žádná kategorie
        }
        return post.kategorie && post.kategorie.some(category => 
            selectedCategories.includes(category.id)
        );
    });

    // Přepínání filtrů kategorií
    const handleCategoryFilter = (categoryId) => {
        setSelectedCategories(prev => {
            if (prev.includes(categoryId)) {
                return prev.filter(id => id !== categoryId);
            } else {
                return [...prev, categoryId];
            }
        });
    };

    // Vymazání všech filtrů
    const clearFilters = () => {
        setSelectedCategories([]);
    };

    if (loading) {
        return (
            <div className="news-loading">
                <div className="loading-spinner"></div>
                <p>Načítání novinek...</p>
            </div>
        );
    }

    return (
        <div className="news-module">
            <PageHeader
                title="Novinky"
                actions={(
                    <button
                        type="button"
                        className="btn btn--primary new-post-btn"
                        onClick={() => setShowPostForm(true)}
                    >
                        Nový příspěvek
                    </button>
                )}
            />

            {error && (
                <div className="error-message">
                    {error}
                    <button onClick={() => setError(null)}>✕</button>
                </div>
            )}

            {showPostForm && (
                <PostForm 
                    onSubmit={handleAddPost}
                    onCancel={() => setShowPostForm(false)}
                />
            )}

            {categories.length > 0 && (
                <div className="category-filters">
                    <div className="filters-header">
                        <h3>Filtrovat podle kategorií:</h3>
                        {selectedCategories.length > 0 && (
                            <button 
                                className="clear-filters-btn"
                                onClick={clearFilters}
                            >
                                Vymazat filtry ({selectedCategories.length})
                            </button>
                        )}
                    </div>
                    <div className="filter-categories">
                        {categories.map(category => (
                            <button
                                key={category.id}
                                className={`filter-category ${selectedCategories.includes(category.id) ? 'active' : ''}`}
                                onClick={() => handleCategoryFilter(category.id)}
                                style={{ 
                                    backgroundColor: selectedCategories.includes(category.id) 
                                        ? category.barva 
                                        : 'transparent',
                                    borderColor: category.barva,
                                    color: selectedCategories.includes(category.id) 
                                        ? 'white' 
                                        : category.barva
                                }}
                            >
                                {category.ikona && <i className={category.ikona}></i>}
                                {category.nazev}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            <PostList 
                posts={filteredPosts}
                currentUser={user}
                onDeletePost={handleDeletePost}
                onAddReaction={handleAddReaction}
                onRemoveReaction={handleRemoveReaction}
                onAddComment={handleAddComment}
                onDeleteComment={handleDeleteComment}
                onLoadComments={handleLoadComments}
            />
        </div>
    );
};

export default NewsModule; 