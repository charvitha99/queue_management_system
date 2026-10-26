
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000/api";

async function getJSON(path) {
  const response = await fetch(`${API}${path}`);
  if (!response.ok) {
    throw new Error(`${path} returned HTTP ${response.status}`);
  }
  return response.json();
}

function MetricCard({ label, value, subtitle, icon, color }) {
  return (
    <article className={`metric-card ${color}`}>
      <div className="metric-top">
        <span>{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-subtitle">{subtitle}</div>
    </article>
  );
}

function Section({ title, subtitle, children }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

export default function App() {
  const [queues, setQueues] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const refreshDashboard = useCallback(async () => {
    try {
      const results = await Promise.allSettled([
        getJSON("/queue-status/"),
        getJSON("/cameras/"),
        getJSON("/analytics/peak-hours/"),
        getJSON("/counter-recommendations/"),
      ]);

      const [queueResult, cameraResult, analyticsResult, recommendationResult] =
        results;

      if (queueResult.status === "fulfilled") {
        setQueues(Array.isArray(queueResult.value) ? queueResult.value : []);
      }

      if (cameraResult.status === "fulfilled") {
        setCameras(Array.isArray(cameraResult.value) ? cameraResult.value : []);
      }

      if (analyticsResult.status === "fulfilled") {
        setAnalytics(analyticsResult.value);
      }

      if (recommendationResult.status === "fulfilled") {
        setRecommendations(recommendationResult.value);
      }

      const failed = results.filter((result) => result.status === "rejected");

      if (failed.length === results.length) {
        setError("Unable to connect to the backend. Check Django is running.");
      } else if (failed.length > 0) {
        setError("Some dashboard data could not be refreshed. Check Django logs.");
      } else {
        setError("");
        setLastUpdated(new Date());
      }
    } catch {
      setError("Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshDashboard();
    const timer = setInterval(refreshDashboard, 3000);
    return () => clearInterval(timer);
  }, [refreshDashboard]);

  const totalQueue = queues.reduce(
    (sum, item) => sum + Number(item.current_queue_count || 0),
    0
  );

  const totalEntries = queues.reduce(
    (sum, item) => sum + Number(item.total_entries || 0),
    0
  );

  const dailyEntries = queues.reduce(
    (sum, item) => sum + Number(item.daily_entries || 0),
    0
  );

  const highAlerts = queues.filter((item) => item.alert_level === "HIGH").length;
  const mediumAlerts = queues.filter(
    (item) => item.alert_level === "MEDIUM"
  ).length;

  const onlineCameras = cameras.filter(
    (camera) => camera.health_status === "ONLINE"
  ).length;

  const activeCounters = queues.filter(
    (item) => item.counter_status === "ACTIVE"
  ).length;

  const peakHour = analytics?.peak_hour;

  return (
    <main className="dashboard">
      <header className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="live-dot" />
            LIVE MONITORING
          </div>
          <h1>Queue Intelligence</h1>
          <p>Smart queue management and counter analytics</p>
        </div>

        <div className="hero-status">
          <span className="status-indicator" />
          Auto-refresh · 3 seconds
          <button onClick={refreshDashboard} className="refresh-button">
            ↻ Refresh
          </button>
        </div>
      </header>

      {error && <div className="error-banner">⚠ {error}</div>}

      <section className="metrics-grid">
        <MetricCard
          label="People in Queue"
          value={totalQueue}
          subtitle="Current detected queue"
          icon="♟"
          color="purple"
        />
        <MetricCard
          label="Today's Entries"
          value={dailyEntries}
          subtitle="Recorded entry events"
          icon="↗"
          color="blue"
        />
        <MetricCard
          label="Total Entries"
          value={totalEntries}
          subtitle="Lifetime recorded entries"
          icon="⇧"
          color="orange"
        />
        <MetricCard
          label="Active Counters"
          value={activeCounters}
          subtitle="Counters marked active"
          icon="▦"
          color="green"
        />
      </section>

      <section className="feature-grid">
        <Section
          title="Smart Queue Alerts"
          subtitle="Alerts based on the configured queue threshold"
        >
          {queues.length === 0 ? (
            <p className="empty-state">
              {loading ? "Loading queue data..." : "No queue status found."}
            </p>
          ) : (
            <div className="alert-list">
              {queues.map((item) => (
                <div className="alert-row" key={item.id}>
                  <div className="alert-main">
                    <strong>{item.counter}</strong>
                    <span>{item.alert_message || "Queue status available"}</span>
                  </div>
                  <span
                    className={`pill ${
                      item.alert_level === "HIGH"
                        ? "pill-red"
                        : item.alert_level === "MEDIUM"
                        ? "pill-amber"
                        : "pill-green"
                    }`}
                  >
                    {item.alert_level || "NORMAL"}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="alert-summary">
            <span>High alerts: <strong>{highAlerts}</strong></span>
            <span>Medium alerts: <strong>{mediumAlerts}</strong></span>
          </div>
        </Section>

        <Section
          title="Camera Health"
          subtitle="Detector heartbeat status"
        >
          {cameras.length === 0 ? (
            <p className="empty-state">No cameras registered.</p>
          ) : (
            <div className="camera-list">
              {cameras.map((camera) => (
                <div className="camera-row" key={camera.id}>
                  <div className="camera-symbol">◉</div>
                  <div className="camera-details">
                    <strong>{camera.name}</strong>
                    <span>
                      {camera.is_enabled ? "Enabled" : "Disabled"} · ID{" "}
                      {camera.id}
                    </span>
                    {camera.last_heartbeat && (
                      <span>
                        Last heartbeat:{" "}
                        {new Date(camera.last_heartbeat).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <span
                    className={`pill ${
                      camera.health_status === "ONLINE"
                        ? "pill-green"
                        : camera.health_status === "DISABLED"
                        ? "pill-gray"
                        : "pill-red"
                    }`}
                  >
                    {camera.health_status || "UNKNOWN"}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="panel-footnote">
            {onlineCameras} of {cameras.length} camera detectors reporting online
          </div>
        </Section>

        <Section
          title="Peak-Hour Analytics"
          subtitle="Average queue count grouped by hour today"
        >
          {analytics?.hours?.length ? (
            <>
              <div className="peak-highlight">
                <div>
                  <span className="muted-label">Busiest recorded hour</span>
                  <strong>{peakHour?.label || "Not available"}</strong>
                </div>
                <div className="peak-number">
                  {peakHour?.average_queue ?? "—"}
                  <span> avg. people</span>
                </div>
              </div>
              <div className="hour-chart">
                {analytics.hours.map((hour) => {
                  const maximum = Math.max(
                    ...analytics.hours.map((entry) => entry.average_queue),
                    1
                  );
                  const width = Math.max(
                    4,
                    (hour.average_queue / maximum) * 100
                  );

                  return (
                    <div className="hour-row" key={hour.hour}>
                      <span className="hour-label">{hour.label}</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{ width: `${width}%` }}
                        />
                      </div>
                      <strong>{hour.average_queue}</strong>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <p className="empty-state">
              {analytics?.message || "Waiting for analytics data..."}
            </p>
          )}
        </Section>

        <Section
          title="Smart Counter Recommendations"
          subtitle="Suggestions based on combined queue size"
        >
          {recommendations ? (
            <>
              <div
                className={`recommendation-card ${
                  recommendations.should_open_counter
                    ? "recommendation-warning"
                    : "recommendation-normal"
                }`}
              >
                <div className="recommendation-icon">
                  {recommendations.should_open_counter ? "⚡" : "✓"}
                </div>
                <div>
                  <strong>
                    {recommendations.should_open_counter
                      ? "Consider opening another counter"
                      : "Current counter allocation"}
                  </strong>
                  <p>{recommendations.message}</p>
                </div>
              </div>
              <div className="recommendation-stats">
                <div>
                  <span>Combined queue</span>
                  <strong>{recommendations.total_queue_count}</strong>
                </div>
                <div>
                  <span>Alert threshold</span>
                  <strong>{recommendations.alert_threshold}</strong>
                </div>
                <div>
                  <span>Available counters</span>
                  <strong>
                    {recommendations.available_counters?.length || 0}
                  </strong>
                </div>
              </div>
            </>
          ) : (
            <p className="empty-state">Loading counter recommendations...</p>
          )}
        </Section>
      </section>

      <Section
        title="Counter Queue Details"
        subtitle="Live counts and recorded customer entries"
      >
        <div className="table-wrap">
          <table className="queue-table">
            <thead>
              <tr>
                <th>Counter</th>
                <th>Status</th>
                <th>Queue</th>
                <th>Today's Entries</th>
                <th>Total Entries</th>
                <th>Alert</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {queues.map((item) => (
                <tr key={item.id}>
                  <td className="counter-name">{item.counter}</td>
                  <td>
                    <span
                      className={`pill ${
                        item.counter_status === "ACTIVE"
                          ? "pill-green"
                          : item.counter_status === "AVAILABLE"
                          ? "pill-blue"
                          : "pill-gray"
                      }`}
                    >
                      {item.counter_status}
                    </span>
                  </td>
                  <td className="queue-number">
                    {item.current_queue_count}
                  </td>
                  <td>{item.daily_entries ?? 0}</td>
                  <td>{item.total_entries ?? 0}</td>
                  <td>
                    <span
                      className={`pill ${
                        item.alert_level === "HIGH"
                          ? "pill-red"
                          : item.alert_level === "MEDIUM"
                          ? "pill-amber"
                          : "pill-green"
                      }`}
                    >
                      {item.alert_level || "NORMAL"}
                    </span>
                  </td>
                  <td>
                    {item.updated_at
                      ? new Date(item.updated_at).toLocaleTimeString()
                      : "—"}
                  </td>
                </tr>
              ))}
              {queues.length === 0 && (
                <tr>
                  <td colSpan="7" className="empty-table">
                    {loading ? "Loading..." : "No queue data available."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Entry & Exit Tracking"
        subtitle="Recorded events and integration readiness"
      >
        <div className="entry-exit-card">
          <div className="entry-exit-icon">↔</div>
          <div className="entry-exit-copy">
            <strong>Entry/exit event API is available</strong>
            <p>
              Recorded entries are shown above. Automatic exit totals are not
              stored separately yet. Calibrate and verify the video crossing
              line before enabling automatic event counting.
            </p>
          </div>
          <span className="pill pill-amber">Calibration required</span>
        </div>
      </Section>

      <footer className="dashboard-footer">
        <span>QSR Queue Management System</span>
        <span>
          {lastUpdated
            ? `Last refreshed ${lastUpdated.toLocaleTimeString()}`
            : "Connecting to backend..."}
        </span>
      </footer>
    </main>
  );
}
