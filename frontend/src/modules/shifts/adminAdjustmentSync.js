/** Sdílená invalidace cache po admin úpravách dovolené / průměru (DV5). */

export const ADMIN_ADJUSTMENT_EVENT = 'mobilmajak:admin-adjustment-saved';

function currentPayrollMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

export function payrollMonthsToInvalidate({ rok, mesic } = {}) {
    const months = [currentPayrollMonth()];
    if (rok && mesic) {
        months.push(`${rok}-${String(mesic).padStart(2, '0')}`);
    }
    return [...new Set(months)];
}

export function dispatchAdminAdjustmentSaved({ rok, mesic } = {}) {
    const months = payrollMonthsToInvalidate({ rok, mesic });
    window.dispatchEvent(new CustomEvent(ADMIN_ADJUSTMENT_EVENT, {
        detail: { months },
    }));
}
