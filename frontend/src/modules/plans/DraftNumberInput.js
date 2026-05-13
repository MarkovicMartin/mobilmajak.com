import React, { useEffect, useRef, useState } from 'react';

/**
 * Text-based number input with a local draft state.
 *
 * Klíčové vlastnosti:
 * - `type="text"` + `inputMode="decimal"` – nepřepisuje text za uživatelem.
 * - Při focusu drží lokální draft a NEsynchronizuje z props, dokud není blur.
 * - `onChange` propaguje hodnotu parentovi jen když parsovaná hodnota je validní
 *   a nekončí tečkou/čárkou (povoluje tedy mezistavy jako "35," nebo "35.").
 * - `onBlur` parsuje, ořízne na min/max a zformátuje na `decimals` desetinných míst.
 * - Enter → blur; mouse wheel → blur (aby scrollování nehýbalo hodnotou).
 */
export default function DraftNumberInput({
  value,
  onChange,
  decimals = 0,
  min,
  max,
  step,
  disabled = false,
  className = '',
  placeholder = '',
  title,
  onFocus,
  onBlur,
  ...rest
}) {
  const inputRef = useRef(null);
  const [isFocused, setIsFocused] = useState(false);

  const formatFromProps = (v) => {
    if (v == null || v === '') return '';
    const n = Number(v);
    if (!Number.isFinite(n)) return '';
    return n.toLocaleString('cs-CZ', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      useGrouping: false,
    });
  };

  const [draft, setDraft] = useState(() => formatFromProps(value));

  useEffect(() => {
    if (!isFocused) {
      setDraft(formatFromProps(value));
    }
  }, [value, isFocused, decimals]); // eslint-disable-line react-hooks/exhaustive-deps

  const parseDraft = (s) => {
    if (s == null) return NaN;
    const cleaned = String(s).trim().replace(/\s/g, '').replace(',', '.');
    if (cleaned === '' || cleaned === '-' || cleaned === '.') return NaN;
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : NaN;
  };

  const clampAndFormat = (n) => {
    let x = n;
    if (!Number.isFinite(x)) return '';
    if (min != null && x < Number(min)) x = Number(min);
    if (max != null && x > Number(max)) x = Number(max);
    return x.toLocaleString('cs-CZ', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      useGrouping: false,
    });
  };

  const handleChange = (e) => {
    const next = e.target.value;
    // Povol pouze čísla, jedno desetinné oddělovač (,.) a volitelně minus na začátku
    if (next !== '' && next !== '-' && !/^-?\d*[.,]?\d*$/.test(next)) {
      return;
    }
    setDraft(next);

    // Mezistav (končí ,/.) – neposílej hodnotu dál, čekej
    if (next === '' || next === '-' || /[,.]$/.test(next)) return;

    const n = parseDraft(next);
    if (!Number.isFinite(n)) return;
    // Neclampuj za živa, jen předej
    onChange && onChange(n);
  };

  const handleFocus = (e) => {
    setIsFocused(true);
    if (onFocus) onFocus(e);
    // Označ vše pro pohodlnou editaci
    try { e.target.select(); } catch (_) { /* noop */ }
  };

  const handleBlur = (e) => {
    setIsFocused(false);
    const n = parseDraft(draft);
    if (Number.isFinite(n)) {
      const formatted = clampAndFormat(n);
      setDraft(formatted);
      onChange && onChange(Number(formatted.replace(',', '.')));
    } else {
      setDraft(formatFromProps(value));
    }
    if (onBlur) onBlur(e);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (inputRef.current) inputRef.current.blur();
    }
  };

  const handleWheel = (e) => {
    if (document.activeElement === e.currentTarget) {
      e.currentTarget.blur();
    }
  };

  return (
    <input
      ref={inputRef}
      type="text"
      inputMode="decimal"
      autoComplete="off"
      value={draft}
      onChange={handleChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      onWheel={handleWheel}
      disabled={disabled}
      className={className}
      placeholder={placeholder}
      title={title}
      step={step}
      {...rest}
    />
  );
}
