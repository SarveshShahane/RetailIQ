import { createAsyncThunk } from "@reduxjs/toolkit";
import api from "../../services/api";

export const fetchDashboardData = createAsyncThunk(
  "dashboard/fetchDashboardData",
  async ({ businessId, timeRange }, { rejectWithValue }) => {
    let days = 30;
    if (timeRange === "today") days = 1;
    else if (timeRange === "week") days = 7;
    else if (timeRange === "month") days = 30;
    else if (timeRange === "year") days = 365;
    else if (timeRange === "all") days = 3650;

    try {
      const [
        metricsRes,
        revenueRes,
        topProductsRes,
        lowStockRes,
        revenueTrendRes,
        invoiceBreakdownRes,
        avgOrderValueRes,
        topCustomersRes,
        profitMarginsRes,
      ] = await Promise.all([
        api.get("/dashboard", {
          params: { business_id: businessId, time: timeRange },
        }),
        api.get("/dashboard/revenue", {
          params: { business_id: businessId },
        }),
        api.get("/dashboard/top-products", {
          params: { business_id: businessId, limit: 5, days },
        }),
        api.get("/dashboard/low-stock", {
          params: { business_id: businessId, threshold: 10 },
        }),
        api.get("/dashboard/revenue-trend", {
          params: { business_id: businessId, days },
        }),
        api.get("/dashboard/invoice-breakdown", {
          params: { business_id: businessId },
        }),
        api.get("/dashboard/avg-order-value", {
          params: { business_id: businessId, days },
        }),
        api.get("/dashboard/top-customers", {
          params: { business_id: businessId, limit: 5, days },
        }),
        api.get("/dashboard/profit-margins", {
          params: { business_id: businessId, days },
        }),
      ]);

      return {
        metrics: metricsRes.data,
        revenueCompare: revenueRes.data,
        topProducts: topProductsRes.data,
        lowStock: lowStockRes.data,
        revenueTrend: revenueTrendRes.data,
        invoiceBreakdown: invoiceBreakdownRes.data,
        avgOrderValue: avgOrderValueRes.data,
        topCustomers: topCustomersRes.data,
        profitMargins: profitMarginsRes.data,
      };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message || "Failed to fetch dashboard metrics.");
    }
  }
);
