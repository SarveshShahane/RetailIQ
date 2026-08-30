import { useEffect, useState, useRef, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { fetch_user_businesses } from "../features/business/businessThunk";
import { fetchDashboardData } from "../features/dashboard/dashboardThunk";
import Chatbot from "./Chatbot/Chatbot";
const CHART_PADDING = { top: 20, right: 20, bottom: 40, left: 64 };
function shortCurrency(v) {
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${Math.round(v)}`;
}
function niceScale(maxVal, ticks = 5) {
  if (maxVal <= 0) return [0];
  const rough = maxVal / ticks;
  const mag = Math.pow(10, Math.floor(Math.log10(rough)));
  const nice = [1, 2, 2.5, 5, 10].find((n) => n * mag >= rough) * mag;
  const result = [];
  for (let v = 0; v <= maxVal + nice * 0.01; v += nice) result.push(Math.round(v * 100) / 100);
  if (result[result.length - 1] < maxVal) result.push(result[result.length - 1] + nice);
  return result;
}
function smoothPath(points) {
  if (points.length < 2) return "";
  if (points.length === 2)
    return `M${points[0].x},${points[0].y}L${points[1].x},${points[1].y}`;
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(i - 1, 0)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(i + 2, points.length - 1)];
    const tension = 0.35;
    const cp1x = p1.x + ((p2.x - p0.x) * tension);
    const cp1y = p1.y + ((p2.y - p0.y) * tension);
    const cp2x = p2.x - ((p3.x - p1.x) * tension);
    const cp2y = p2.y - ((p3.y - p1.y) * tension);
    d += `C${cp1x},${cp1y},${cp2x},${cp2y},${p2.x},${p2.y}`;
  }
  return d;
}
const RevenueTrendChart = ({ data, formatCurrency, formatDateLabel }) => {
  const svgRef = useRef(null);
  const [dims, setDims] = useState({ w: 600, h: 280 });
  const [hover, setHover] = useState(null);
  useEffect(() => {
    const el = svgRef.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width;
      setDims({ w: Math.max(w, 320), h: 280 });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  if (!data || data.length === 0) {
    return <div className="no-data-msg">No sales data available for this time range</div>;
  }
  const { w, h } = dims;
  const plotW = w - CHART_PADDING.left - CHART_PADDING.right;
  const plotH = h - CHART_PADDING.top - CHART_PADDING.bottom;
  const maxRev = Math.max(...data.map((d) => d.revenue), 1);
  const ticks = niceScale(maxRev, 5);
  const yMax = ticks[ticks.length - 1] || maxRev;
  const points = data.map((d, i) => ({
    x: CHART_PADDING.left + (data.length === 1 ? plotW / 2 : (i / (data.length - 1)) * plotW),
    y: CHART_PADDING.top + plotH - (d.revenue / yMax) * plotH,
  }));
  const linePath = smoothPath(points);
  const areaPath =
    linePath +
    `L${points[points.length - 1].x},${CHART_PADDING.top + plotH}` +
    `L${points[0].x},${CHART_PADDING.top + plotH}Z`;
  const xLabelCount = Math.min(data.length, 7);
  const xStep = Math.max(1, Math.floor((data.length - 1) / (xLabelCount - 1)));
  const xLabels = [];
  for (let i = 0; i < data.length; i += xStep) xLabels.push(i);
  if (xLabels[xLabels.length - 1] !== data.length - 1) xLabels.push(data.length - 1);
  const handleMouseMove = useCallback(
    (e) => {
      const svg = svgRef.current;
      if (!svg || data.length === 0) return;
      const rect = svg.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      let nearest = 0;
      let minDist = Infinity;
      points.forEach((p, i) => {
        const dist = Math.abs(p.x - mouseX);
        if (dist < minDist) { minDist = dist; nearest = i; }
      });
      setHover(nearest);
    },
    [data.length, points]
  );
  const handleMouseLeave = useCallback(() => setHover(null), []);
  const hoverPoint = hover !== null ? points[hover] : null;
  const hoverData = hover !== null ? data[hover] : null;
  const totalRev = data.reduce((s, d) => s + d.revenue, 0);
  const totalInv = data.reduce((s, d) => s + d.invoices, 0);
  const avgRev = data.length ? totalRev / data.length : 0;
  return (
    <div className="area-chart-container">
      { }
      <div className="area-chart-summary">
        <div className="area-chart-stat">
          <span className="area-chart-stat-label">Total</span>
          <span className="area-chart-stat-value">{formatCurrency(totalRev)}</span>
        </div>
        <div className="area-chart-stat">
          <span className="area-chart-stat-label">Invoices</span>
          <span className="area-chart-stat-value">{totalInv}</span>
        </div>
        <div className="area-chart-stat">
          <span className="area-chart-stat-label">Avg/Day</span>
          <span className="area-chart-stat-value">{formatCurrency(avgRev)}</span>
        </div>
      </div>
      <svg
        ref={svgRef}
        width="100%"
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        className="area-chart-svg"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--brand-500)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--brand-500)" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        { }
        {ticks.map((t) => {
          const y = CHART_PADDING.top + plotH - (t / yMax) * plotH;
          return (
            <g key={t}>
              <line
                x1={CHART_PADDING.left}
                y1={y}
                x2={w - CHART_PADDING.right}
                y2={y}
                stroke="var(--slate-100)"
                strokeWidth="1"
              />
              <text
                x={CHART_PADDING.left - 10}
                y={y + 4}
                textAnchor="end"
                fill="var(--slate-400)"
                fontSize="11"
                fontWeight="500"
                fontFamily="var(--font-sans)"
              >
                {shortCurrency(t)}
              </text>
            </g>
          );
        })}
        { }
        <path d={areaPath} fill="url(#areaGrad)" />
        { }
        <path
          d={linePath}
          fill="none"
          stroke="var(--brand-500)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        { }
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r={hover === i ? 5 : 3}
            fill={hover === i ? "var(--brand-600)" : "var(--brand-500)"}
            stroke="#fff"
            strokeWidth="2"
            style={{ transition: "r 0.15s ease" }}
          />
        ))}
        { }
        {hoverPoint && (
          <>
            <line
              x1={hoverPoint.x}
              y1={CHART_PADDING.top}
              x2={hoverPoint.x}
              y2={CHART_PADDING.top + plotH}
              stroke="var(--slate-300)"
              strokeWidth="1"
              strokeDasharray="4 3"
            />
            <line
              x1={CHART_PADDING.left}
              y1={hoverPoint.y}
              x2={w - CHART_PADDING.right}
              y2={hoverPoint.y}
              stroke="var(--slate-200)"
              strokeWidth="1"
              strokeDasharray="4 3"
            />
          </>
        )}
        { }
        {xLabels.map((i) => (
          <text
            key={i}
            x={points[i].x}
            y={h - 8}
            textAnchor="middle"
            fill="var(--slate-400)"
            fontSize="11"
            fontWeight="500"
            fontFamily="var(--font-sans)"
          >
            {formatDateLabel(data[i]?.date)}
          </text>
        ))}
      </svg>
      { }
      {hoverPoint && hoverData && (
        <div
          className="area-chart-tooltip"
          style={{
            left: `${Math.min(Math.max(hoverPoint.x, 80), w - 80)}px`,
            top: `${hoverPoint.y - 10}px`,
          }}
        >
          <div className="area-chart-tooltip-date">{formatDateLabel(hoverData.date)}</div>
          <div className="area-chart-tooltip-rev">{formatCurrency(hoverData.revenue)}</div>
          <div className="area-chart-tooltip-inv">{hoverData.invoices} invoice{hoverData.invoices !== 1 ? "s" : ""}</div>
        </div>
      )}
    </div>
  );
};
const KPICardSkeleton = () => (
  <div className="stat-card stat-card-skeleton">
    <div className="stat-icon skeleton-pulse" style={{ width: "44px", height: "44px" }} />
    <div className="stat-content" style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
      <div className="skeleton-pulse" style={{ width: "70px", height: "12px" }} />
      <div className="skeleton-pulse" style={{ width: "120px", height: "24px" }} />
      <div className="skeleton-pulse" style={{ width: "90px", height: "10px" }} />
    </div>
  </div>
);

const DashboardSkeleton = () => (
  <>
    <div className="stats-grid">
      <KPICardSkeleton />
      <KPICardSkeleton />
      <KPICardSkeleton />
      <KPICardSkeleton />
      <KPICardSkeleton />
    </div>
    <div className="analytics-grid-2-1">
      <div className="chart-card stat-card-skeleton" style={{ minHeight: "300px", display: "flex", flexDirection: "column", gap: "16px" }}>
        <div className="skeleton-pulse" style={{ width: "140px", height: "18px" }} />
        <div className="skeleton-pulse" style={{ width: "100%", flex: 1, borderRadius: "var(--radius-md)" }} />
      </div>
      <div className="status-breakdown-card stat-card-skeleton" style={{ minHeight: "300px", display: "flex", flexDirection: "column", gap: "16px" }}>
        <div className="skeleton-pulse" style={{ width: "160px", height: "18px" }} />
        <div className="skeleton-pulse" style={{ width: "100%", height: "44px" }} />
        <div className="skeleton-pulse" style={{ width: "100%", height: "44px" }} />
        <div className="skeleton-pulse" style={{ width: "100%", height: "44px" }} />
      </div>
    </div>
  </>
);

const Dashboard = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector((state) => state.auth);
  const { businesses, selectedBusinessId, loading } = useSelector(
    (state) => state.business
  );
  const {
    metrics,
    revenueCompare,
    topProducts,
    lowStock,
    revenueTrend,
    invoiceBreakdown,
    avgOrderValue,
    topCustomers,
    profitMargins,
    loading: analyticsLoading,
    error: analyticsError,
  } = useSelector((state) => state.dashboard);

  const [timeRange, setTimeRange] = useState("month");
  const selectedBusiness = businesses.find((b) => b.id === selectedBusinessId);
  useEffect(() => {
    if (user?.id) {
      dispatch(fetch_user_businesses(user.id));
    }
  }, [dispatch, user?.id]);
  useEffect(() => {
    if (!selectedBusinessId) return;
    dispatch(fetchDashboardData({ businessId: selectedBusinessId, timeRange }));
  }, [selectedBusinessId, timeRange, dispatch]);
  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };
  const formatCurrency = (value) => {
    const currencySymbol = selectedBusiness?.currency || "INR";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currencySymbol,
    }).format(value || 0);
  };
  const formatDateLabel = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  };
  const totalInvoicesCount = Object.values(invoiceBreakdown).reduce(
    (acc, curr) => acc + curr.count,
    0
  ) || 1;
  return (
    <div className="dashboard-page">
      <main className="dashboard-main">
        {loading && businesses.length === 0 ? (
          <>
            <div className="flex-between mb-6" style={{ flexWrap: "wrap", gap: "16px" }}>
              <div className="dashboard-header" style={{ marginBottom: 0 }}>
                <h1 className="dashboard-greeting" id="dashboard-greeting">
                  {greeting()}, {user?.name?.split(" ")[0] || "there"}!
                </h1>
                <p className="dashboard-tagline">Loading your business insights...</p>
              </div>
            </div>
            <DashboardSkeleton />
          </>
        ) : businesses.length === 0 ? (
          <div className="empty-state-card">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--slate-400)" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M9 3v18" />
              <path d="M15 3v18" />
              <path d="M3 9h18" />
              <path d="M3 15h18" />
            </svg>
            <h2 className="empty-state-title">You don't have any businesses yet</h2>
            <p className="empty-state-description">
              Create a business profile to start managing your products, inventory, sales, and invoices.
            </p>
            <button
              className="btn-primary"
              style={{ width: "auto" }}
              onClick={() => navigate("/business")}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Create Business
            </button>
          </div>
        ) : (
          <>
            <div className="flex-between mb-6" style={{ flexWrap: "wrap", gap: "16px" }}>
              <div className="dashboard-header" style={{ marginBottom: 0 }}>
                <h1 className="dashboard-greeting" id="dashboard-greeting">
                  {greeting()}, {user?.name?.split(" ")[0] || "there"}!
                </h1>
                <p className="dashboard-tagline">
                  Here is the overview for <strong>{selectedBusiness?.name}</strong>.
                </p>
              </div>
              <div className="dashboard-filters">
                <select
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="filter-select"
                  id="dashboard-time-filter"
                >
                  <option value="today">Today</option>
                  <option value="week">Last 7 Days</option>
                  <option value="month">Last 30 Days</option>
                  <option value="year">Last Year</option>
                  <option value="all">All Time</option>
                </select>
              </div>
            </div>
            {analyticsLoading && <DashboardSkeleton />}
            {analyticsError && !analyticsLoading && (
              <div style={{
                textAlign: "center",
                padding: "20px",
                backgroundColor: "var(--danger-50)",
                border: "1px solid var(--danger-100)",
                borderRadius: "var(--radius-md)",
                color: "var(--danger-700)",
                fontWeight: 500,
                marginBottom: "24px"
              }}>
                {analyticsError}
              </div>
            )}
            {!analyticsLoading && !analyticsError && (
              <>
                { }
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-icon stat-icon-revenue">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="12" y1="1" x2="12" y2="23" />
                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                      </svg>
                    </div>
                    <div className="stat-content">
                      <span className="stat-label">Total Sales</span>
                      <span className="stat-value">{formatCurrency(metrics.totalSales)}</span>
                      {revenueCompare && (
                        <span className={`stat-trend ${revenueCompare.percentageChange > 0 ? "stat-trend-up" : revenueCompare.percentageChange < 0 ? "stat-trend-down" : "stat-trend-neutral"}`}>
                          {revenueCompare.percentageChange > 0 ? "▲" : revenueCompare.percentageChange < 0 ? "▼" : "•"} {Math.abs(revenueCompare.percentageChange)}% vs last month
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon stat-icon-orders">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
                        <line x1="3" y1="6" x2="21" y2="6" />
                        <path d="M16 10a4 4 0 0 1-8 0" />
                      </svg>
                    </div>
                    <div className="stat-content">
                      <span className="stat-label">Total Invoices</span>
                      <span className="stat-value">{metrics.totalInvoices}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "6px", fontWeight: 500 }}>
                        Invoices issued
                        <Chatbot />
                      </span>
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon stat-icon-products">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                        <circle cx="9" cy="7" r="4" />
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                      </svg>
                    </div>
                    <div className="stat-content">
                      <span className="stat-label">Customers</span>
                      <span className="stat-value">{metrics.recentCustomers}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "6px", fontWeight: 500 }}>
                        Distinct buyers
                      </span>
                    </div>
                  </div>
                  {avgOrderValue && (
                    <div className="stat-card">
                      <div className="stat-icon" style={{ backgroundColor: "var(--brand-50)", color: "var(--brand-600)" }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <circle cx="12" cy="12" r="10" />
                          <path d="M12 8v4l3 3" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Avg Order Value</span>
                        <span className="stat-value">{formatCurrency(avgOrderValue.averageOrderValue)}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "6px", fontWeight: 500 }}>
                          Min: {formatCurrency(avgOrderValue.minOrderValue)} / Max: {formatCurrency(avgOrderValue.maxOrderValue)}
                        </span>
                      </div>
                    </div>
                  )}
                  {profitMargins && (
                    <div className="stat-card">
                      <div className="stat-icon" style={{ backgroundColor: "var(--success-50)", color: "var(--success-600)" }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <line x1="18" y1="20" x2="18" y2="10" />
                          <line x1="12" y1="20" x2="12" y2="4" />
                          <line x1="6" y1="20" x2="6" y2="14" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Profit Margin</span>
                        <span className="stat-value">{profitMargins.marginPercent}%</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "6px", fontWeight: 500 }}>
                          Profit: {formatCurrency(profitMargins.totalProfit)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
                { }
                <div className="analytics-grid-2-1">
                  <div className="chart-card">
                    <div className="chart-header">
                      <h3 className="chart-title">Revenue Trend</h3>
                      <span style={{ fontSize: "0.8125rem", color: "var(--slate-400)", fontWeight: 500 }}>
                        {revenueTrend.length} data points
                      </span>
                    </div>
                    <RevenueTrendChart
                      data={revenueTrend}
                      formatCurrency={formatCurrency}
                      formatDateLabel={formatDateLabel}
                    />
                  </div>
                  <div className="status-breakdown-card">
                    <h3 className="chart-title" style={{ marginBottom: "16px" }}>Invoice Breakdown</h3>
                    <div style={{ display: "flex", flexDirection: "column", gap: "14px", flex: 1, justifyContent: "center" }}>
                      {Object.entries(invoiceBreakdown).map(([status, info]) => {
                        const widthPct = `${(info.count / totalInvoicesCount) * 100}%`;
                        const statusClass = status.toLowerCase();
                        return (
                          <div key={status} className="status-row">
                            <div className="status-info">
                              <div className="status-label-group">
                                <span className={`badge badge-${statusClass === "paid" ? "success" : statusClass === "pending" ? "warning" : statusClass === "overdue" ? "danger" : "neutral"}`}>
                                  {status}
                                </span>
                                <span className="status-count">({info.count})</span>
                              </div>
                              <span className="status-amount">{formatCurrency(info.amount)}</span>
                            </div>
                            <div className="status-progress-bg">
                              <div
                                className={`status-progress-fill progress-${statusClass}`}
                                style={{ width: widthPct }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
                { }
                <div className="analytics-grid-3">
                  { }
                  {profitMargins && (
                    <div className="dashboard-list-card">
                      <div className="dashboard-list-header">
                        <h3 className="dashboard-list-title">Profit Analysis</h3>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "16px", flex: 1, justifyContent: "center" }}>
                        <div className="margin-split-container">
                          <div className="margin-split-bar">
                            <div className="margin-split-cost" style={{ width: `${100 - profitMargins.marginPercent}%` }} />
                            <div className="margin-split-profit" style={{ width: `${profitMargins.marginPercent}%` }} />
                          </div>
                          <div className="margin-legend">
                            <span className="legend-item">
                              <span className="legend-dot dot-cost" /> Cost ({Math.round(100 - profitMargins.marginPercent)}%)
                            </span>
                            <span className="legend-item">
                              <span className="legend-dot dot-profit" /> Profit ({Math.round(profitMargins.marginPercent)}%)
                            </span>
                          </div>
                        </div>
                        <div style={{ borderTop: "1px solid var(--slate-100)", paddingTop: "14px" }}>
                          <div className="flex-between mb-4">
                            <span style={{ fontSize: "0.875rem", color: "var(--slate-500)", fontWeight: 500 }}>Total Revenue</span>
                            <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--slate-900)" }}>{formatCurrency(profitMargins.totalRevenue)}</span>
                          </div>
                          <div className="flex-between mb-4">
                            <span style={{ fontSize: "0.875rem", color: "var(--slate-500)", fontWeight: 500 }}>Cost of Goods</span>
                            <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--slate-900)" }}>{formatCurrency(profitMargins.totalCost)}</span>
                          </div>
                          <div className="flex-between" style={{ borderTop: "1px dashed var(--slate-200)", paddingTop: "10px" }}>
                            <span style={{ fontSize: "0.875rem", color: "var(--slate-700)", fontWeight: 600 }}>Net Profit</span>
                            <span style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--success-600)" }}>{formatCurrency(profitMargins.totalProfit)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  { }
                  <div className="dashboard-list-card">
                    <div className="dashboard-list-header">
                      <h3 className="dashboard-list-title">Top Products</h3>
                    </div>
                    {topProducts.length === 0 ? (
                      <div className="no-data-msg" style={{ margin: "auto" }}>No sales data available</div>
                    ) : (
                      <div className="dashboard-list">
                        {topProducts.map((p, idx) => (
                          <div key={p.productId} className="dashboard-list-item">
                            <div className="item-info">
                              <span className="item-rank">#{idx + 1}</span>
                              <div className="item-details">
                                <span className="item-name">{p.name}</span>
                                <span className="item-subtitle">{p.totalQty} units sold</span>
                              </div>
                            </div>
                            <div className="item-stats">
                              <span className="item-value">{formatCurrency(p.totalRevenue)}</span>
                              <span className="item-meta">{formatCurrency(p.sellingPrice)} / unit</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  { }
                  <div className="dashboard-list-card">
                    <div className="dashboard-list-header">
                      <h3 className="dashboard-list-title">Top Customers</h3>
                    </div>
                    {topCustomers.length === 0 ? (
                      <div className="no-data-msg" style={{ margin: "auto" }}>No customer data available</div>
                    ) : (
                      <div className="dashboard-list">
                        {topCustomers.map((c, idx) => (
                          <div key={c.customerId} className="dashboard-list-item">
                            <div className="item-info">
                              <span className="item-avatar">{c.name.charAt(0).toUpperCase()}</span>
                              <div className="item-details">
                                <span className="item-name">{c.name}</span>
                                <span className="item-subtitle">{c.orderCount} orders</span>
                              </div>
                            </div>
                            <div className="item-stats">
                              <span className="item-value">{formatCurrency(c.totalSpent)}</span>
                              <span className="item-meta">{c.phone || "No phone"}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                { }
                <div className="low-stock-card mb-6">
                  <div className="dashboard-list-header">
                    <h3 className="dashboard-list-title" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ color: "var(--danger-500)" }}>
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                        <line x1="12" y1="9" x2="12" y2="13" />
                        <line x1="12" y1="17" x2="12.01" y2="17" />
                      </svg>
                      Low Stock Inventory Alerts
                    </h3>
                    <span className="badge badge-danger">Threshold &le; 10</span>
                  </div>
                  {lowStock.length === 0 ? (
                    <div className="low-stock-empty">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      All inventory stock levels are healthy!
                    </div>
                  ) : (
                    <div className="low-stock-list">
                      {lowStock.map((p) => (
                        <div key={p.productId} className="low-stock-alert">
                          <div>
                            <strong>{p.name}</strong>
                            <span style={{ fontSize: "0.75rem", opacity: 0.8, marginLeft: "8px" }}>({p.category || "General"})</span>
                          </div>
                          <span className="low-stock-badge">{p.stock} remaining</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
};
export default Dashboard;
