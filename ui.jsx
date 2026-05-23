// ui.jsx — shared UI primitives for NHL Tracker wireframes
// Editorial light theme. Exports to window for cross-file usage.

const { useState, useMemo, useRef, useEffect } = React;

// ───────────────────────── Annotations ─────────────────────────
// Editorial-style margin annotation, used to call out wireframe intent.
function MarginNote({ children, side = "right" }) {
  return (
    <aside className={`margin-note margin-note--${side}`} aria-hidden="true">
      <span className="margin-note__rule" />
      <span className="margin-note__text">{children}</span>
    </aside>
  );
}

// Inline mono-caps wireframe descriptor: [ DESCRIPTOR ]
function WFLabel({ children }) {
  return <span className="wf-label">[ {children} ]</span>;
}

// Dashed placeholder box — for images/charts that aren't drawn yet
function Placeholder({ children, h = 80, style = {} }) {
  return (
    <div className="wf-placeholder" style={{ minHeight: h, ...style }}>
      <span className="wf-placeholder__text">{children}</span>
    </div>
  );
}

// ───────────────────────── Score visualization ─────────────────────────
// Horizontal score bar 0–100. Editorial: hairline track + filled segment.
function ScoreBar({ value, width = 56, showNumber = true, mono = true }) {
  const pct = Math.max(0, Math.min(100, value));
  const tone =
    pct >= 90 ? "score--elite" :
    pct >= 75 ? "score--high"  :
    pct >= 60 ? "score--mid"   :
    pct >= 45 ? "score--low"   : "score--bottom";
  return (
    <span className={`score ${tone}`}>
      {showNumber && <span className={`score__num ${mono ? "score__num--mono" : ""}`}>{Math.round(pct)}</span>}
      <span className="score__track" style={{ width }}>
        <span className="score__fill" style={{ width: `${pct}%` }} />
      </span>
    </span>
  );
}

// Sparkline: 5-yr trajectory mini chart
function Sparkline({ values, width = 56, height = 18 }) {
  if (!values || !values.length) return null;
  const min = Math.min(...values) - 2;
  const max = Math.max(...values) + 2;
  const range = max - min || 1;
  const stepX = width / (values.length - 1);
  const points = values
    .map((v, i) => `${i * stepX},${height - ((v - min) / range) * height}`)
    .join(" ");
  return (
    <svg className="sparkline" width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1" />
      <circle
        cx={width}
        cy={height - ((values[values.length - 1] - min) / range) * height}
        r="1.6"
        fill="currentColor"
      />
    </svg>
  );
}

// Progress bar with a threshold marker (red vertical line at threshold%)
function ThresholdBar({ value, threshold, width = 160 }) {
  const pct = Math.max(0, Math.min(100, value));
  const markPct = Math.max(0, Math.min(100, threshold));
  return (
    <span className="threshold-bar" style={{ width }}>
      <span className="threshold-bar__fill" style={{ width: `${pct}%` }} />
      <span className="threshold-bar__mark" style={{ left: `${markPct}%` }} title={`Top-10 threshold: ${threshold}`} />
    </span>
  );
}

// ───────────────────────── Sortable Table ─────────────────────────
// Columns: [{ key, label, render?, align?, sort?: (a,b)=>n, w?: cssWidth, numeric? }]
function SortableTable({ columns, rows, defaultSort, onRowClick, rowKey, dense = false }) {
  const [sortKey, setSortKey] = useState(defaultSort?.key || null);
  const [sortDir, setSortDir] = useState(defaultSort?.dir || "desc");

  const sorted = useMemo(() => {
    if (!sortKey) return rows;
    const col = columns.find(c => c.key === sortKey);
    if (!col) return rows;
    const cmp = col.sort || ((a, b) => {
      const av = col.value ? col.value(a) : a[sortKey];
      const bv = col.value ? col.value(b) : b[sortKey];
      if (typeof av === "number" && typeof bv === "number") return av - bv;
      return String(av).localeCompare(String(bv));
    });
    const arr = [...rows].sort(cmp);
    return sortDir === "desc" ? arr.reverse() : arr;
  }, [rows, columns, sortKey, sortDir]);

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  return (
    <table className={`table ${dense ? "table--dense" : ""}`}>
      <thead>
        <tr>
          {columns.map(c => (
            <th
              key={c.key}
              className={`table__th ${c.numeric ? "table__th--num" : ""} ${c.sortable === false ? "" : "table__th--sortable"}`}
              style={c.w ? { width: c.w } : undefined}
              onClick={c.sortable === false ? undefined : () => toggleSort(c.key)}
              aria-sort={sortKey === c.key ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
            >
              <span className="table__th-label">{c.label}</span>
              {sortKey === c.key && (
                <span className="table__th-arrow">{sortDir === "desc" ? "▾" : "▴"}</span>
              )}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sorted.map((r, i) => (
          <tr
            key={rowKey ? rowKey(r) : i}
            className={onRowClick ? "table__row table__row--clickable" : "table__row"}
            onClick={onRowClick ? () => onRowClick(r) : undefined}
          >
            {columns.map(c => (
              <td
                key={c.key}
                className={`table__td ${c.numeric ? "table__td--num" : ""}`}
              >
                {c.render ? c.render(r, i) : r[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ───────────────────────── Position badge ─────────────────────────
function PosBadge({ pos }) {
  return <span className={`pos-badge pos-badge--${pos}`}>{pos}</span>;
}

function TeamSwatch({ colors, code }) {
  const primary = colors?.primary || "#666";
  return (
    <span
      className="team-swatch"
      title={code}
      style={{ background: primary }}
      aria-hidden="true"
    >
      {code && (
        <img
          src={`https://assets.nhle.com/logos/nhl/svg/${code}_light.svg`}
          alt=""
          className="team-swatch__logo"
          onError={e => { e.target.style.display = "none"; }}
        />
      )}
    </span>
  );
}

function StatusBadge({ active }) {
  return <span className={`status-badge ${active ? "status-badge--active" : ""}`}>{active ? "Active" : "Legend"}</span>;
}

// Confidence-tier badge for historic data
function TierBadge({ tier }) {
  return (
    <span className={`tier-badge tier-badge--${tier}`} title={`Confidence tier ${tier}`}>
      {tier}
    </span>
  );
}

// ───────────────────────── Section header ─────────────────────────
function SectionHead({ kicker, title, sub, right }) {
  return (
    <header className="section-head">
      <div className="section-head__left">
        {kicker && <div className="section-head__kicker">{kicker}</div>}
        <h2 className="section-head__title">{title}</h2>
        {sub && <p className="section-head__sub">{sub}</p>}
      </div>
      {right && <div className="section-head__right">{right}</div>}
    </header>
  );
}

// ───────────────────────── Methodology overlay ─────────────────────────
function MethodologyOverlay({ open, onClose, data }) {
  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose(); }
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="overlay__sheet" onClick={e => e.stopPropagation()}>
        <header className="overlay__head">
          <div className="overlay__kicker">Methodology</div>
          <h2 className="overlay__title">How the scores are calculated</h2>
          <button className="overlay__close" onClick={onClose} aria-label="Close">×</button>
        </header>

        <div className="overlay__body">
          <section className="method-block">
            <h3 className="method-block__title">Player Score 0–100</h3>
            <p className="method-block__formula">{data.player.formula}</p>
            <ul className="method-block__list">
              {data.player.bullets.map((b, i) => <li key={i}>{b}</li>)}
            </ul>
          </section>

          <section className="method-block">
            <h3 className="method-block__title">Team Score 0–100</h3>
            <p className="method-block__formula">{data.team.formula}</p>
            <ul className="method-block__list">
              {data.team.bullets.map((b, i) => <li key={i}>{b}</li>)}
            </ul>
          </section>

          <section className="method-block">
            <h3 className="method-block__title">Data confidence by era</h3>
            <table className="method-table">
              <thead>
                <tr>
                  <th>Tier</th>
                  <th>Years</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {data.confidence.map(c => (
                  <tr key={c.tier}>
                    <td><TierBadge tier={c.tier} /></td>
                    <td className="mono">{c.years}</td>
                    <td>{c.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  MarginNote, WFLabel, Placeholder,
  ScoreBar, Sparkline, ThresholdBar,
  SortableTable,
  PosBadge, TeamSwatch, StatusBadge, TierBadge,
  SectionHead,
  MethodologyOverlay,
});
