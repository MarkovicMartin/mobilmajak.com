import React from 'react';

/**
 * Komentář u tiketu: úprava jen vlastního, mazání jen admin (všechny).
 */
const TicketCommentRow = ({
    comment,
    ticketId,
    currentUserId,
    isAdmin,
    editingCommentId,
    editCommentText,
    onStartEdit,
    onEditTextChange,
    onSaveEdit,
    onCancelEdit,
    savingCommentId,
    deletingCommentId,
    onDeleteComment,
}) => {
    const isMine = currentUserId != null && Number(comment.autor_id) === Number(currentUserId);
    const canEdit = isMine;
    const canDelete = isAdmin;

    if (editingCommentId === comment.id) {
        return (
            <div className="comment-item comment-item-editing">
                <div className="comment-header">
                    <strong>{comment.autor_jmeno}</strong>
                    <span>
                        {new Date(comment.vytvoreno).toLocaleString('cs-CZ')}
                        {comment.upraveno && ' · upraveno'}
                    </span>
                </div>
                <textarea
                    className="comment-edit-textarea"
                    value={editCommentText}
                    onChange={(e) => onEditTextChange(e.target.value)}
                    rows={3}
                />
                <div className="comment-actions">
                    <button
                        type="button"
                        className="btn-comment-save"
                        onClick={() => onSaveEdit(ticketId, comment.id)}
                        disabled={savingCommentId === comment.id || !editCommentText.trim()}
                    >
                        {savingCommentId === comment.id ? 'Ukládám…' : 'Uložit'}
                    </button>
                    <button
                        type="button"
                        className="btn-comment-cancel"
                        onClick={onCancelEdit}
                        disabled={savingCommentId === comment.id}
                    >
                        Zrušit
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="comment-item">
            <div className="comment-header">
                <strong>{comment.autor_jmeno}</strong>
                <span>
                    {new Date(comment.vytvoreno).toLocaleString('cs-CZ')}
                    {comment.upraveno && (
                        <span className="comment-edited-hint">
                            {' '}
                            · upraveno {new Date(comment.upraveno).toLocaleString('cs-CZ')}
                        </span>
                    )}
                </span>
            </div>
            <p className="comment-body-text">{comment.text}</p>
            {(canEdit || canDelete) && (
                <div className="comment-actions">
                    {canEdit && (
                        <button
                            type="button"
                            className="btn-comment-edit"
                            onClick={() => onStartEdit(comment)}
                        >
                            Upravit
                        </button>
                    )}
                    {canDelete && (
                        <button
                            type="button"
                            className="btn-comment-delete"
                            onClick={() => onDeleteComment(ticketId, comment.id)}
                            disabled={deletingCommentId === comment.id}
                        >
                            {deletingCommentId === comment.id ? 'Mažu…' : 'Smazat'}
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};

export default TicketCommentRow;
