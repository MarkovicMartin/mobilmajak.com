import Select from './ui/Select';
import './CustomDropdown.css';

/** @deprecated Použijte `ui/Select` – wrapper pro zpětnou kompatibilitu. */
const CustomDropdown = (props) => <Select {...props} legacy />;

export default CustomDropdown;
