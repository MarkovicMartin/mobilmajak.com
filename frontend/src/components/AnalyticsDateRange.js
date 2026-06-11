import DateRangePicker from './ui/DateRangePicker';
import DatePicker from './ui/DatePicker';
import './AnalyticsDatePicker.css';
import './ui/DateRangePicker.css';

const VARIANT_MAP = {
    'filter-group': 'labeled',
    inline: 'inline',
    bare: 'bare',
};

/** @deprecated Použijte `ui/DateRangePicker` – wrapper pro zpětnou kompatibilitu. */
const AnalyticsDateRange = ({
    variant = 'filter-group',
    ...props
}) => (
    <DateRangePicker
        {...props}
        variant={VARIANT_MAP[variant] || variant}
        legacy
    />
);

export default AnalyticsDateRange;

/** @deprecated Použijte `ui/DatePicker` – wrapper pro zpětnou kompatibilitu. */
export const AnalyticsDateInput = (props) => <DatePicker {...props} legacy />;

export {
    isValidISODate,
    normalizeDateRange,
    INVALID_DATE_MESSAGE,
} from '../utils/analyticsDateRange';
