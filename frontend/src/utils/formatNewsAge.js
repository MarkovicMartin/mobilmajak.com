/** Relativní stáří novinky: hodiny jen první den, pak datum. */
export function formatNewsAge(dateString) {
    const date = new Date(dateString);
    const diffInHours = (Date.now() - date) / (1000 * 60 * 60);

    if (diffInHours < 1) {
        const diffInMinutes = Math.max(1, Math.floor((Date.now() - date) / (1000 * 60)));
        return `před ${diffInMinutes} min`;
    }
    if (diffInHours < 24) {
        return `před ${Math.floor(diffInHours)} h`;
    }
    return date.toLocaleDateString('cs-CZ');
}
