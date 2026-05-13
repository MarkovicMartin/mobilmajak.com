/**
 * Utility funkce pro bezpečné kopírování textu do schránky
 * Obsahuje fallback metodu pro starší prohlížeče nebo když clipboard API není dostupné
 */

export const copyToClipboard = async (text) => {
    try {
        // Pokusíme se použít moderní Clipboard API
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return { success: true, method: 'modern' };
        } else {
            // Fallback metoda pro starší prohlížeče
            return fallbackCopyTextToClipboard(text);
        }
    } catch (err) {
        console.warn('Clipboard API selhalo, zkouším fallback metodu:', err);
        // Pokud moderní API selže, zkusíme fallback
        return fallbackCopyTextToClipboard(text);
    }
};

const fallbackCopyTextToClipboard = (text) => {
    try {
        // Vytvoříme dočasný textarea element
        const textArea = document.createElement("textarea");
        textArea.value = text;
        
        // Zajistíme, že element nebude viditelný
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        textArea.setAttribute('readonly', '');
        textArea.style.opacity = '0';
        
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        // Zkusíme zkopírovat pomocí execCommand
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        
        if (successful) {
            return { success: true, method: 'fallback' };
        } else {
            return { success: false, error: 'execCommand copy selhalo' };
        }
    } catch (err) {
        return { success: false, error: err.message };
    }
};

export const showCopySuccess = (text, method = 'clipboard') => {
    // Můžeme přidat toast notifikaci nebo jiný způsob oznámení
    const message = method === 'modern' 
        ? `✅ ${text} zkopírováno do schránky`
        : `✅ ${text} zkopírováno do schránky (kompatibilní režim)`;
    
    // Pro teď použijeme alert, ale můžeme nahradit toast notifikací
    alert(message);
};

export const showCopyError = (error) => {
    console.error('Chyba při kopírování:', error);
    alert('❌ Nepodařilo se zkopírovat do schránky. Zkopírujte text ručně.');
}; 