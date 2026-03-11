import type { ScoreResponse } from "../api";
import { ACC_META, CAT_ICONS, SCORE_TOOLTIPS } from "../constants";
import Tooltip from "./Tooltip";

type Props = { data: ScoreResponse | null };

export default function MetricsPanel({ data }: Props) {
  if (!data) {
    return (
      <div className="metrics-panel">
        <div className="empty-state">
          <div className="icon">📍</div>
          <p>
            Double‑click the map or enter coordinates and click Run to compute
            spatial indicators.
          </p>
        </div>
      </div>
    );
  }

  const s = data.scores;
  const byCat = Object.entries(s.by_category).sort((a, b) => b[1] - a[1]);
  const maxD = Math.max(1, ...byCat.map(([, v]) => v));
  const nearest = Object.entries(s.nearest_km).sort((a, b) => a[1] - b[1]);

  return (
    <div className="metrics-panel">
      <div className="metric-group" style={{ animationDelay: "0s" }}>
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
        <div className="metric-group" style={{ animationDelay: "0.07s" }}>
          <div className="metric-group-title">
            Category density · 1 km
            <Tooltip text={SCORE_TOOLTIPS.by_category} />
          </div>
          {byCat.map(([cat, count]) => (
            <div key={cat} className="cat-row">
              <div className="cat-name">
                {CAT_ICONS[cat] ?? "📍"} {cat}
              </div>
              <div className="cat-bar-wrap">
                <div
                  className="cat-bar"
                  style={{ width: `${(count / maxD) * 100}%` }}
                />
              </div>
              <div className="cat-count">{count}</div>
            </div>
          ))}
        </div>
      )}

      <div className="metric-group" style={{ animationDelay: "0.14s" }}>
        <div className="metric-group-title">
          Accessibility · 400 m walk
          <Tooltip text={SCORE_TOOLTIPS.accessibility_400m} />
        </div>
        <div className="acc-grid">
          {Object.entries(s.accessibility_400m).map(([key, val]) => {
            const meta = ACC_META[key] ?? { icon: "📍", label: key };
            return (
              <div
                key={key}
                className={`acc-item ${val ? "yes" : "no"}`}
                title={key}
              >
                <div className="acc-icon">{meta.icon}</div>
                <span className="acc-label">{meta.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {nearest.length > 0 && (
        <div className="metric-group" style={{ animationDelay: "0.21s" }}>
          <div className="metric-group-title">
            Nearest · by category
            <Tooltip text={SCORE_TOOLTIPS.nearest_km} />
          </div>
          {nearest.map(([cat, dist]) => (
            <div key={cat} className="nearest-row">
              <div className="nearest-name">
                {CAT_ICONS[cat] ?? "📍"} {cat}
              </div>
              <div className="nearest-dist">{dist} km</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
