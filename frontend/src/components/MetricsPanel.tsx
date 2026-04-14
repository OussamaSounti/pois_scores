import type { ScoreResponse } from '../api';
import { ACC_META, CAT_ICONS, SCORE_TOOLTIPS } from '../constants';
import Tooltip from './Tooltip';

export type PoiFilterSection = 'category_density' | 'accessibility' | 'nearest' | null;

export type PoiFilterItem = { section: PoiFilterSection; value: string } | null;

type Props = {
  data: ScoreResponse | null;
  activeFilter?: PoiFilterItem;
  onItemClick?: (section: 'category_density' | 'accessibility' | 'nearest', value: string) => void;
  onClearFilter?: () => void;
};

export default function MetricsPanel({ data, activeFilter, onItemClick, onClearFilter }: Props) {
  if (!data) {
    return (
      <div className="metrics-panel">
        <div className="empty-state">
          <div className="icon">📍</div>
          <p>
            Double‑click the map or enter coordinates and click Run to compute spatial indicators.
          </p>
        </div>
      </div>
    );
  }

  const s = data.scores;
  const byCat = Object.entries(s.by_category).sort((a, b) => b[1] - a[1]);
  const maxD = Math.max(1, ...byCat.map(([, v]) => v));
  const nearest = Object.entries(s.nearest_km).sort((a, b) => a[1] - b[1]);

  // ── Coastal proximity helpers ──────────────────────────────────
  const distCoast = s.dist_coast_km;
  const landFrac  = s.land_buffer_fraction_1km ?? 1.0;
  const oceanFrac = 1.0 - landFrac;
  // Show the card only when there is real coastal information:
  // either we have a measured coastline distance, OR the buffer is partially in the ocean.
  const showCoastal = distCoast != null || (s.land_buffer_fraction_1km != null && landFrac < 0.999);
  // Donut ring geometry
  const R = 26, CX = 34, CY = 34;
  const circ = 2 * Math.PI * R;
  // Proximity category
  const coastBadge =
    distCoast == null       ? null
    : distCoast < 0.2      ? { label: 'Beachfront', cls: 'beachfront' }
    : distCoast < 0.5      ? { label: 'Seafront',   cls: 'seafront'   }
    : distCoast < 1.0      ? { label: 'Near Sea',   cls: 'near-sea'   }
    :                        { label: 'Coastal',    cls: 'coastal'    };
  // Human-friendly distance display (m when < 1 km)
  const distDisplay = distCoast != null
    ? (distCoast < 1
        ? { val: Math.round(distCoast * 1000).toString(), unit: 'm' }
        : { val: distCoast.toFixed(2), unit: 'km' })
    : null;

  const filterLabel =
    activeFilter?.section === 'accessibility'
      ? (ACC_META[activeFilter.value]?.label ?? activeFilter.value)
      : (activeFilter?.value ?? '');

  return (
    <div className="metrics-panel">
      {activeFilter && onClearFilter && (
        <div className="metric-filter-bar">
          <span className="metric-filter-label">Showing: {filterLabel}</span>
          <button
            type="button"
            className="metric-filter-clear"
            onClick={onClearFilter}
            title="Show all POIs on the map"
          >
            Show all
          </button>
        </div>
      )}
      <div className="metric-group" style={{ animationDelay: '0s' }}>
        <div className="metric-group-title">Overview · 1 km radius</div>
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">
              POIs (1 km)
              <Tooltip text={SCORE_TOOLTIPS.poi_count_1km} />
            </div>
            <div className="kpi-value">{s.poi_count_1km}</div>
            <div className="kpi-sub">within 1 km</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">
              POIs (400 m)
              <Tooltip text={SCORE_TOOLTIPS.poi_count_400m} />
            </div>
            <div className="kpi-value">{s.poi_count_400m}</div>
            <div className="kpi-sub">within 400 m</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">
              Categories
              <Tooltip text={SCORE_TOOLTIPS.n_categories} />
            </div>
            <div className="kpi-value small">{s.n_categories}</div>
            <div className="kpi-sub">active</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">
              POI types
              <Tooltip text={SCORE_TOOLTIPS.n_poi_types} />
            </div>
            <div className="kpi-value small">{s.n_poi_types}</div>
            <div className="kpi-sub">unique fclass</div>
          </div>
        </div>
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">
              Entropy (category)
              <Tooltip text={SCORE_TOOLTIPS.entropy} />
            </div>
            <div className="kpi-value small">{s.entropy.toFixed(2)}</div>
            <div className="kpi-sub">Shannon</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">
              Entropy (type)
              <Tooltip text={SCORE_TOOLTIPS.entropy_fclass} />
            </div>
            <div className="kpi-value small">{s.entropy_fclass.toFixed(2)}</div>
            <div className="kpi-sub">Shannon</div>
          </div>
          {s.aggregate_score != null && (
            <div className="kpi-card">
              <div className="kpi-label">
                Aggregate
                <Tooltip text={SCORE_TOOLTIPS.aggregate_score} />
              </div>
              <div className="kpi-value">{s.aggregate_score}</div>
              <div className="kpi-sub">0–100</div>
            </div>
          )}
        </div>
      </div>

      {byCat.length > 0 && (
        <div className="metric-group" style={{ animationDelay: '0.07s' }}>
          <div className="metric-group-title">
            Category density · 1 km
            <Tooltip text={SCORE_TOOLTIPS.by_category} />
          </div>
          {byCat.map(([cat, count]) => (
            <div
              key={cat}
              className={`cat-row ${onItemClick ? 'metric-row-clickable' : ''} ${activeFilter?.section === 'category_density' && activeFilter?.value === cat ? 'metric-row-active' : ''}`}
              role={onItemClick ? 'button' : undefined}
              tabIndex={onItemClick ? 0 : undefined}
              onClick={onItemClick ? () => onItemClick('category_density', cat) : undefined}
              onKeyDown={
                onItemClick
                  ? (e) => e.key === 'Enter' && onItemClick('category_density', cat)
                  : undefined
              }
              title={onItemClick ? `Click to show only ${cat} POIs on the map` : undefined}
            >
              <div className="cat-name">
                {CAT_ICONS[cat] ?? '📍'} {cat}
              </div>
              <div className="cat-bar-wrap">
                <div className="cat-bar" style={{ width: `${(count / maxD) * 100}%` }} />
              </div>
              <div className="cat-count">{count}</div>
            </div>
          ))}
        </div>
      )}

      <div className="metric-group" style={{ animationDelay: '0.14s' }}>
        <div className="metric-group-title">
          Accessibility · 400 m walk
          <Tooltip text={SCORE_TOOLTIPS.accessibility_400m} />
        </div>
        <div className="acc-grid">
          {Object.entries(s.accessibility_400m).map(([key, val]) => {
            const meta = ACC_META[key] ?? { icon: '📍', label: key };
            return (
              <div
                key={key}
                className={`acc-item ${val ? 'yes' : 'no'} ${onItemClick ? 'metric-row-clickable' : ''} ${activeFilter?.section === 'accessibility' && activeFilter?.value === key ? 'metric-row-active' : ''}`}
                role={onItemClick ? 'button' : undefined}
                tabIndex={onItemClick ? 0 : undefined}
                onClick={onItemClick ? () => onItemClick('accessibility', key) : undefined}
                onKeyDown={
                  onItemClick
                    ? (e) => e.key === 'Enter' && onItemClick('accessibility', key)
                    : undefined
                }
                title={onItemClick ? `Click to show only ${meta.label} POIs on the map` : key}
              >
                <div className="acc-icon">{meta.icon}</div>
                <span className="acc-label">{meta.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {nearest.length > 0 && (
        <div className="metric-group" style={{ animationDelay: '0.21s' }}>
          <div className="metric-group-title">
            Nearest · by category
            <Tooltip text={SCORE_TOOLTIPS.nearest_km} />
          </div>
          {nearest.map(([cat, dist]) => (
            <div
              key={cat}
              className={`nearest-row ${onItemClick ? 'metric-row-clickable' : ''} ${activeFilter?.section === 'nearest' && activeFilter?.value === cat ? 'metric-row-active' : ''}`}
              role={onItemClick ? 'button' : undefined}
              tabIndex={onItemClick ? 0 : undefined}
              onClick={onItemClick ? () => onItemClick('nearest', cat) : undefined}
              onKeyDown={
                onItemClick ? (e) => e.key === 'Enter' && onItemClick('nearest', cat) : undefined
              }
              title={onItemClick ? `Click to show only ${cat} POIs on the map` : undefined}
            >
              <div className="nearest-name">
                {CAT_ICONS[cat] ?? '📍'} {cat}
              </div>
              <div className="nearest-dist">{dist} km</div>
            </div>
          ))}
        </div>
      )}

      {showCoastal && (
        <div className="coastal-card">
          {/* ── Wave header with proximity badge ── */}
          <div className="coastal-wave-header">
            <span className="coastal-wave-title">🌊 Coastal proximity</span>
            {coastBadge && (
              <span className={`coastal-badge ${coastBadge.cls}`}>{coastBadge.label}</span>
            )}
          </div>

          {/* ── Body: donut ring + distance stats ── */}
          <div className="coastal-body">
            {/* SVG donut — land vs ocean fraction */}
            <div className="coastal-ring-wrap">
              <svg width="68" height="68" viewBox="0 0 68 68" aria-hidden="true">
                {/* track */}
                <circle cx={CX} cy={CY} r={R} fill="none" stroke="#dde2ef" strokeWidth="8" />
                {/* ocean arc */}
                {oceanFrac > 0.001 && (
                  <circle
                    cx={CX} cy={CY} r={R}
                    fill="none"
                    stroke="#1a7fa8"
                    strokeWidth="8"
                    strokeDasharray={`${oceanFrac * circ} ${circ}`}
                    strokeDashoffset={0}
                    strokeLinecap="butt"
                    transform={`rotate(-90 ${CX} ${CY})`}
                  />
                )}
                {/* land arc */}
                <circle
                  cx={CX} cy={CY} r={R}
                  fill="none"
                  stroke="#1e9d65"
                  strokeWidth="8"
                  strokeDasharray={`${landFrac * circ} ${circ}`}
                  strokeDashoffset={-(oceanFrac * circ)}
                  strokeLinecap="butt"
                  transform={`rotate(-90 ${CX} ${CY})`}
                />
                {/* centre label */}
                <text
                  x={CX} y={CY - 4}
                  textAnchor="middle"
                  fill="#1e9d65"
                  fontSize="13"
                  fontWeight="600"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {(landFrac * 100).toFixed(0)}%
                </text>
                <text
                  x={CX} y={CY + 9}
                  textAnchor="middle"
                  fill="#8a93b2"
                  fontSize="7"
                  fontFamily="Syne, sans-serif"
                  letterSpacing="0.5"
                >
                  LAND
                </text>
              </svg>
              <div className="coastal-ring-caption">Buffer area</div>
            </div>

            {/* Distance + correction note */}
            <div className="coastal-stats">
              {distDisplay != null ? (
                <>
                  <div className="coastal-dist-value">
                    {distDisplay.val}
                    <span className="coastal-dist-unit">{distDisplay.unit}</span>
                  </div>
                  <div className="coastal-dist-label">
                    to nearest coastline
                    <Tooltip text={SCORE_TOOLTIPS.dist_coast_km} />
                  </div>
                </>
              ) : (
                <div className="coastal-dist-label">
                  Land buffer only
                  <Tooltip text={SCORE_TOOLTIPS.land_buffer_fraction_1km} />
                </div>
              )}
              {landFrac < 0.999 && (
                <div className="coastal-correction-note">
                  <strong>{(oceanFrac * 100).toFixed(0)}%</strong> of the 1 km buffer
                  extends into the ocean — density score auto‑corrected.
                </div>
              )}
            </div>
          </div>

          {/* ── Ocean / land split bar ── */}
          <div className="coastal-split-wrap">
            <div className="coastal-split-bar">
              <div
                className="coastal-bar-ocean"
                style={{ width: `${oceanFrac * 100}%` }}
                title={`${(oceanFrac * 100).toFixed(0)}% ocean`}
              />
              <div
                className="coastal-bar-land"
                title={`${(landFrac * 100).toFixed(0)}% land`}
              />
            </div>
            <div className="coastal-split-labels">
              <span className="coastal-lbl-ocean">
                🌊 {(oceanFrac * 100).toFixed(0)}% ocean
              </span>
              <span className="coastal-lbl-land">
                🏡 {(landFrac * 100).toFixed(0)}% land
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
