import Tabs from './ui/Tabs';
import '../styles/ModuleSubnav.css';

/** @deprecated Použijte `ui/Tabs` – wrapper pro zpětnou kompatibilitu. */
const ModuleSubnav = (props) => <Tabs {...props} legacy />;

export default ModuleSubnav;
