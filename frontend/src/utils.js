/**
 * Sanitizes strings to prevent XSS attacks when embedding user/API content into HTML.
 */
export function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export function formatDate(dtStr) {
    if (!dtStr) return 'N/A';
    try {
        const dt = new Date(dtStr);
        return dt.toLocaleString();
    } catch (e) {
        return dtStr;
    }
}
