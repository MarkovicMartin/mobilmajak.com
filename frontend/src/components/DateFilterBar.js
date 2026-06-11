import FilterBar from './ui/FilterBar';
import '../styles/DateFilterBar.css';

/** @deprecated Použijte `ui/FilterBar` – wrapper pro zpětnou kompatibilitu. */
const DateFilterBar = (props) => <FilterBar {...props} legacy />;

export default DateFilterBar;
