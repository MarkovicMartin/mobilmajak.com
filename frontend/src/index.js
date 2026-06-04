import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

/** Po deployi starý JS může odkazovat na smazaný chunk – jednou obnovit stránku. */
const CHUNK_RELOAD_KEY = 'mm-chunk-reload';
window.addEventListener('error', (event) => {
    const msg = event.message || '';
    if (!/loading (css )?chunk/i.test(msg)) return;
    if (sessionStorage.getItem(CHUNK_RELOAD_KEY)) return;
    sessionStorage.setItem(CHUNK_RELOAD_KEY, '1');
    window.location.reload();
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
