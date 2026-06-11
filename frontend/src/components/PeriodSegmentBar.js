import SegmentControl from './ui/SegmentControl';
import '../styles/PeriodSegmentBar.css';

/** @deprecated Použijte `ui/SegmentControl` – wrapper pro zpětnou kompatibilitu. */
const PeriodSegmentBar = (props) => <SegmentControl {...props} legacy />;

export default PeriodSegmentBar;
