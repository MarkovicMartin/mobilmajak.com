import { registerLocale } from 'react-datepicker';
import { cs } from 'date-fns/locale';
import { format, parseISO, isValid } from 'date-fns';
import { isValidISODate } from '../../utils/analyticsDateRange';
import 'react-datepicker/dist/react-datepicker.css';

registerLocale('cs', cs);

export const UI_DATE_INPUT_CLASS = 'ui-date-picker__input';

export const isoFromDate = (d) => format(d, 'yyyy-MM-dd');

export const dateFromIso = (iso) => {
    if (!iso || !isValidISODate(iso)) return null;
    const parsed = parseISO(iso);
    return isValid(parsed) ? parsed : null;
};
