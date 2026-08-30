import { useEffect, useState, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  fetchInvoices,
  fetchCustomers,
  createInvoice,
  updateInvoice,
} from "../../features/invoice/invoiceThunk";
import { fetchProducts } from "../../features/product/productThunk";
import { clearSelectedInvoice, clearInvoiceError } from "../../features/invoice/invoiceSlice";

const SearchableSelect = ({
  options,
  value,
  onChange,
  placeholder,
  required = false,
  emptyMessage = "No results found"
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef(null);

  const selectedOption = options.find((opt) => String(opt.id) === String(value));

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter((opt) =>
    opt.label.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="searchable-select-container" ref={containerRef} style={{ position: "relative", width: "100%" }}>
      <div
        className="form-select"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
          userSelect: "none"
        }}
        onClick={() => {
          setIsOpen(!isOpen);
          setSearch("");
        }}
      >
        <span style={{ color: selectedOption ? "var(--slate-900)" : "var(--slate-400)", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          style={{ transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s", opacity: 0.6 }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>

      {isOpen && (
        <div
          className="searchable-select-dropdown"
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            zIndex: 999,
            marginTop: "4px",
            background: "var(--slate-50)",
            border: "1px solid var(--slate-200)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-md)",
            padding: "6px",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            maxHeight: "260px"
          }}
        >
          <input
            type="text"
            className="form-input"
            placeholder="Type to search..."
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ padding: "6px 8px", fontSize: "0.875rem" }}
          />
          <div style={{ overflowY: "auto", display: "flex", flexDirection: "column" }}>
            {filteredOptions.length === 0 ? (
              <div style={{ padding: "8px", fontSize: "0.875rem", color: "var(--slate-400)", textAlign: "center" }}>
                {emptyMessage}
              </div>
            ) : (
              filteredOptions.map((opt) => (
                <div
                  key={opt.id}
                  onClick={() => {
                    onChange(opt.id);
                    setIsOpen(false);
                  }}
                  style={{
                    padding: "8px",
                    fontSize: "0.875rem",
                    cursor: "pointer",
                    borderRadius: "var(--radius-sm)",
                    background: String(opt.id) === String(value) ? "var(--brand-50)" : "transparent",
                    color: String(opt.id) === String(value) ? "var(--brand-600)" : "var(--slate-700)",
                    fontWeight: String(opt.id) === String(value) ? "600" : "500",
                    transition: "background 0.15s"
                  }}
                  onMouseEnter={(e) => {
                    if (String(opt.id) !== String(value)) {
                      e.currentTarget.style.background = "var(--slate-100)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (String(opt.id) !== String(value)) {
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                >
                  {opt.label}
                </div>
              ))
            )}
          </div>
        </div>
      )}
      
      <input
        type="text"
        tabIndex={-1}
        value={value || ""}
        onChange={() => {}}
        required={required}
        style={{
          opacity: 0,
          position: "absolute",
          top: 0,
          left: 0,
          height: "100%",
          width: "100%",
          pointerEvents: "none"
        }}
      />
    </div>
  );
};

const Invoices = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();


  const { selectedBusinessId, businesses } = useSelector((state) => state.business);
  const { data: invoices, customers, loading, error } = useSelector((state) => state.invoices);
  const { data: products } = useSelector((state) => state.products);
  const selectedBusiness = businesses.find((b) => b.id === selectedBusinessId);

  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [viewingInvoice, setViewingInvoice] = useState(null);

  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState("");

  const [isNewCustomer, setIsNewCustomer] = useState(false);
  const [formData, setFormData] = useState({
    customerId: "",
    newCustomer: {
      name: "",
      phone_number: "",
      email: "",
    },
    status: "PENDING",
    notes: "",
    discount: "0",
    taxRate: "18",
  });
  const [selectedItems, setSelectedItems] = useState([]);
  const [currentItem, setCurrentItem] = useState({
    product_id: "",
    quantity: "1",
  });
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (selectedBusinessId) {
      dispatch(fetchInvoices(selectedBusinessId));
      dispatch(fetchCustomers(selectedBusinessId));
      dispatch(fetchProducts(selectedBusinessId));
    }
  }, [dispatch, selectedBusinessId]);

  useEffect(() => {
    if (!showCreateForm) {
      setFormError("");
      setSelectedItems([]);
      setFormData({
        customerId: "",
        newCustomer: { name: "", phone_number: "", email: "" },
        status: "PENDING",
        notes: "",
        discount: "0",
        taxRate: "18",
      });
      setCurrentItem({ product_id: "", quantity: "1" });
    }
  }, [showCreateForm]);

  const formatCurrency = (value) => {
    const currencySymbol = selectedBusiness?.currency || "INR";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currencySymbol,
    }).format(value || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleString("en-IN", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const renderNotes = (notes) => {
    if (!notes) return null;
    return (
      <p style={{ fontSize: "0.8125rem", color: "var(--slate-500)", marginTop: "4px", whiteSpace: "pre-line" }}>
        {notes}
      </p>
    );
  };

  const subtotal = selectedItems.reduce((sum, item) => {
    return sum + (item.product?.selling_price || 0) * parseInt(item.quantity || 1);
  }, 0);

  const tax = subtotal * (parseFloat(formData.taxRate) / 100);
  const discountVal = parseFloat(formData.discount) || 0;
  const total = subtotal + tax - discountVal;

  const handleAddItem = () => {
    if (!currentItem.product_id) {
      setFormError("Please select a product first.");
      return;
    }
    const quantity = parseInt(currentItem.quantity);
    if (isNaN(quantity) || quantity <= 0) {
      setFormError("Quantity must be at least 1.");
      return;
    }

    const matchedProduct = products.find((p) => p.id === parseInt(currentItem.product_id));
    if (!matchedProduct) return;

    const existingIndex = selectedItems.findIndex(
      (item) => item.product_id === matchedProduct.id
    );

    if (existingIndex !== -1) {
      const updated = [...selectedItems];
      updated[existingIndex].quantity = (
        parseInt(updated[existingIndex].quantity) + quantity
      ).toString();
      setSelectedItems(updated);
    } else {
      setSelectedItems([
        ...selectedItems,
        {
          product_id: matchedProduct.id,
          quantity: currentItem.quantity,
          product: matchedProduct,
        },
      ]);
    }

    setCurrentItem({ product_id: "", quantity: "1" });
    setFormError("");
  };

  const handleRemoveItem = (index) => {
    setSelectedItems(selectedItems.filter((_, i) => i !== index));
  };

  const handleSubmitInvoice = async (e) => {
    e.preventDefault();
    setFormError("");

    if (!selectedBusinessId) return;

    if (selectedItems.length === 0) {
      setFormError("Please add at least one product line item.");
      return;
    }

    if (isNewCustomer) {
      if (!formData.newCustomer.name || !formData.newCustomer.phone_number) {
        setFormError("Customer Name and Phone Number are required for new customers.");
        return;
      }
    } else {
      if (!formData.customerId) {
        setFormError("Please select an existing customer or toggle New Customer.");
        return;
      }
    }

    const payload = {
      business_id: parseInt(selectedBusinessId),
      status: formData.status,
      notes: formData.notes || null,
      subtotal: parseFloat(subtotal.toFixed(2)),
      tax: parseFloat(tax.toFixed(2)),
      discount: parseFloat(discountVal.toFixed(2)),
      total: parseFloat(total.toFixed(2)),
      items: selectedItems.map((item) => ({
        product_id: item.product_id,
        quantity: parseInt(item.quantity),
      })),
    };

    if (isNewCustomer) {
      payload.customer = {
        name: formData.newCustomer.name,
        phone_number: formData.newCustomer.phone_number,
        email: formData.newCustomer.email || null,
      };
    } else {
      payload.customer_id = parseInt(formData.customerId);
    }

    const result = await dispatch(createInvoice(payload));
    if (!result.error) {
      setShowCreateForm(false);
      dispatch(fetchInvoices(selectedBusinessId));
      dispatch(fetchCustomers(selectedBusinessId));
    } else {
      const errMessage = result.payload?.detail || result.payload?.error || (typeof result.payload === "string" ? result.payload : "Failed to create invoice.");
      setFormError(errMessage);
    }
  };



  const handleUpdateStatus = async (newStatus) => {
    if (!viewingInvoice) return;
    setStatusLoading(true);
    setStatusError("");
    try {
      const result = await dispatch(
        updateInvoice({
          invoiceId: viewingInvoice.id,
          data: { status: newStatus },
        })
      );
      if (!result.error) {
        setViewingInvoice(result.payload);
        if (selectedBusinessId) {
          dispatch(fetchInvoices(selectedBusinessId));
        }
      } else {
        const errMessage =
          result.payload?.detail ||
          result.payload?.error ||
          (typeof result.payload === "string" ? result.payload : "Failed to update status.");
        setStatusError(errMessage);
      }
    } catch (err) {
      setStatusError("An unexpected error occurred.");
    } finally {
      setStatusLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const s = status ? status.toUpperCase() : "PENDING";
    if (s === "PAID") return <span className="badge badge-success">Paid</span>;
    if (s === "PENDING") return <span className="badge badge-warning">Pending</span>;
    if (s === "DRAFT") return <span className="badge badge-neutral">Draft</span>;
    if (s === "CANCELLED" || s === "REFUNDED") return <span className="badge badge-danger">{status}</span>;
    return <span className="badge badge-neutral">{status}</span>;
  };

  const handlePrint = () => {
    window.print();
  };

  const filteredInvoices = invoices.filter((inv) => {
    const customerName = inv.customer?.name?.toLowerCase() || "";
    const invId = `inv-${inv.id}`;
    return (
      customerName.includes(searchQuery.toLowerCase()) ||
      invId.includes(searchQuery.toLowerCase())
    );
  });

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedBusinessId]);

  const totalInvoicesCount = invoices?.length || 0;
  const totalInvoicedAmount = invoices?.reduce(
    (acc, inv) => acc + (Number(inv.total) || 0),
    0
  ) || 0;
  const paidInvoices = invoices?.filter(
    (inv) => (inv.status || "").toUpperCase() === "PAID"
  ) || [];
  const paidAmount = paidInvoices.reduce(
    (acc, inv) => acc + (Number(inv.total) || 0),
    0
  );
  const pendingInvoices = invoices?.filter(
    (inv) => (inv.status || "").toUpperCase() === "PENDING"
  ) || [];
  const pendingAmount = pendingInvoices.reduce(
    (acc, inv) => acc + (Number(inv.total) || 0),
    0
  );

  const totalPages = Math.ceil(filteredInvoices.length / itemsPerPage);
  const indexOfLastInvoice = currentPage * itemsPerPage;
  const indexOfFirstInvoice = indexOfLastInvoice - itemsPerPage;
  const currentInvoices = filteredInvoices.slice(indexOfFirstInvoice, indexOfLastInvoice);

  return (
    <div className="dashboard-page">
      <main className="dashboard-main">
        {!selectedBusinessId ? (
          <div className="empty-state-card">
            <h2 className="empty-state-title">No Active Business Selected</h2>
            <p className="empty-state-description">
              Please create or select a business to manage your invoices.
            </p>
            <button className="btn-primary" style={{ width: "auto" }} onClick={() => navigate("/business")}>
              Create Business
            </button>
          </div>
        ) : (
          <>
            <div className="dashboard-header flex-between flex-wrap gap-4">
              <div>
                <h1 className="dashboard-greeting">Invoices</h1>
                <p className="dashboard-tagline">
                  Generate manual bills and track billing status for <strong>{selectedBusiness?.name}</strong>.
                </p>
              </div>
              {!showCreateForm && !viewingInvoice && (
                <div className="flex-gap-2">
                  <button className="btn-primary" style={{ width: "auto" }} onClick={() => setShowCreateForm(true)}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ marginRight: "4px" }}>
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    New Invoice
                  </button>
                </div>
              )}
            </div>

            {/* KPI Cards Section */}
            {!showCreateForm && !viewingInvoice && (
              <div className="stats-grid">
                {loading && invoices.length === 0 ? (
                  <>
                    <div className="stat-card stat-card-skeleton">
                      <div className="stat-icon skeleton-pulse" style={{ width: "44px", height: "44px" }} />
                      <div className="stat-content" style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div className="skeleton-pulse" style={{ width: "70px", height: "12px" }} />
                        <div className="skeleton-pulse" style={{ width: "100px", height: "24px" }} />
                        <div className="skeleton-pulse" style={{ width: "80px", height: "10px" }} />
                      </div>
                    </div>
                    <div className="stat-card stat-card-skeleton">
                      <div className="stat-icon skeleton-pulse" style={{ width: "44px", height: "44px" }} />
                      <div className="stat-content" style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div className="skeleton-pulse" style={{ width: "70px", height: "12px" }} />
                        <div className="skeleton-pulse" style={{ width: "100px", height: "24px" }} />
                        <div className="skeleton-pulse" style={{ width: "80px", height: "10px" }} />
                      </div>
                    </div>
                    <div className="stat-card stat-card-skeleton">
                      <div className="stat-icon skeleton-pulse" style={{ width: "44px", height: "44px" }} />
                      <div className="stat-content" style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div className="skeleton-pulse" style={{ width: "70px", height: "12px" }} />
                        <div className="skeleton-pulse" style={{ width: "100px", height: "24px" }} />
                        <div className="skeleton-pulse" style={{ width: "80px", height: "10px" }} />
                      </div>
                    </div>
                    <div className="stat-card stat-card-skeleton">
                      <div className="stat-icon skeleton-pulse" style={{ width: "44px", height: "44px" }} />
                      <div className="stat-content" style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div className="skeleton-pulse" style={{ width: "70px", height: "12px" }} />
                        <div className="skeleton-pulse" style={{ width: "100px", height: "24px" }} />
                        <div className="skeleton-pulse" style={{ width: "80px", height: "10px" }} />
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="stat-card">
                      <div className="stat-icon stat-icon-orders">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                          <line x1="16" y1="13" x2="8" y2="13" />
                          <line x1="16" y1="17" x2="8" y2="17" />
                          <polyline points="10 9 9 9 8 9" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Total Invoiced</span>
                        <span className="stat-value">{formatCurrency(totalInvoicedAmount)}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          {totalInvoicesCount} total invoice{totalInvoicesCount !== 1 ? "s" : ""}
                        </span>
                      </div>
                    </div>

                    <div className="stat-card">
                      <div className="stat-icon stat-icon-revenue">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                          <polyline points="22 4 12 14.01 9 11.01" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Paid Revenue</span>
                        <span className="stat-value">{formatCurrency(paidAmount)}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          {paidInvoices.length} paid &amp; settled
                        </span>
                      </div>
                    </div>

                    <div className="stat-card">
                      <div className="stat-icon" style={{ backgroundColor: pendingAmount > 0 ? "var(--warning-50)" : "var(--slate-100)", color: pendingAmount > 0 ? "var(--warning-600)" : "var(--slate-500)" }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <circle cx="12" cy="12" r="10" />
                          <polyline points="12 6 12 12 16 14" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Pending</span>
                        <span className="stat-value" style={{ color: pendingAmount > 0 ? "var(--warning-600)" : "inherit" }}>
                          {formatCurrency(pendingAmount)}
                        </span>
                        <span style={{ fontSize: "0.75rem", color: pendingAmount > 0 ? "var(--warning-500)" : "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          {pendingInvoices.length} awaiting payment
                        </span>
                      </div>
                    </div>

                    <div className="stat-card">
                      <div className="stat-icon" style={{ backgroundColor: "var(--brand-50)", color: "var(--brand-600)" }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <line x1="19" y1="5" x2="5" y2="19" />
                          <circle cx="6.5" cy="6.5" r="2.5" />
                          <circle cx="17.5" cy="17.5" r="2.5" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Collection Rate</span>
                        <span className="stat-value">
                          {totalInvoicedAmount > 0 ? Math.round((paidAmount / totalInvoicedAmount) * 100) : 0}%
                        </span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          Settled vs total billing
                        </span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}


            {error && (
              <div className="auth-error mb-4">
                <span>{typeof error === "string" ? error : "Something went wrong fetching invoices."}</span>
              </div>
            )}

            {showCreateForm && (
              <div className="auth-card mb-6" style={{ maxWidth: "none" }}>
                <h3 className="mb-4" style={{ borderBottom: "1px solid var(--slate-200)", paddingBottom: "8px", color: "var(--slate-800)" }}>
                  Create Customer Invoice
                </h3>
                {formError && (
                  <div className="auth-error mb-4">
                    <span>{formError}</span>
                  </div>
                )}
                <form onSubmit={handleSubmitInvoice} className="standard-form">
                  <div className="grid-2">
                    <div className="form-group border-b border-slate-100 pb-4 md:border-b-0 md:pb-0 md:border-r md:pr-4">
                      <div className="flex-between mb-2">
                        <label className="form-label" style={{ marginBottom: 0 }}>Customer Info *</label>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ padding: "2px 8px", fontSize: "0.75rem" }}
                          onClick={() => setIsNewCustomer(!isNewCustomer)}
                        >
                          {isNewCustomer ? "Select Existing" : "+ Add New Customer"}
                        </button>
                      </div>

                      {isNewCustomer ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                          <input
                            className="form-input"
                            type="text"
                            placeholder="Full Name *"
                            required
                            value={formData.newCustomer.name}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                newCustomer: { ...formData.newCustomer, name: e.target.value },
                              })
                            }
                          />
                          <input
                            className="form-input"
                            type="tel"
                            placeholder="Phone Number *"
                            required
                            value={formData.newCustomer.phone_number}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                newCustomer: {
                                  ...formData.newCustomer,
                                  phone_number: e.target.value,
                                },
                              })
                            }
                          />
                          <input
                            className="form-input"
                            type="email"
                            placeholder="Email Address"
                            value={formData.newCustomer.email}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                newCustomer: { ...formData.newCustomer, email: e.target.value },
                              })
                            }
                          />
                        </div>
                      ) : (
                        <SearchableSelect
                          options={customers.map((c) => ({ id: c.id, label: `${c.name} (${c.phone_number})` }))}
                          value={formData.customerId}
                          onChange={(val) => setFormData({ ...formData, customerId: val })}
                          placeholder="-- Select Customer --"
                          required
                          emptyMessage="No customers found"
                        />
                      )}
                    </div>

                    <div className="form-group">
                      <label className="form-label">Invoice Details</label>
                      <div className="grid-2 mb-2" style={{ gap: "10px" }}>
                        <div>
                          <label className="field-hint">Billing Status</label>
                          <select
                            className="form-select"
                            value={formData.status}
                            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                          >
                            <option value="PENDING">Pending</option>
                            <option value="DRAFT">Draft</option>
                            <option value="PAID">Paid</option>
                          </select>
                        </div>
                        <div>
                          <label className="field-hint">GST Rate (%)</label>
                          <select
                            className="form-select"
                            value={formData.taxRate}
                            onChange={(e) => setFormData({ ...formData, taxRate: e.target.value })}
                          >
                            <option value="0">0%</option>
                            <option value="5">5%</option>
                            <option value="12">12%</option>
                            <option value="18">18%</option>
                            <option value="28">28%</option>
                          </select>
                        </div>
                      </div>
                      <textarea
                        className="form-textarea"
                        placeholder="Additional billing notes or terms..."
                        style={{ minHeight: "68px", resize: "none" }}
                        value={formData.notes}
                        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      />
                    </div>
                  </div>

                  <div style={{ borderTop: "1px solid var(--slate-100)", paddingTop: "16px", marginTop: "8px" }}>
                    <h4 className="mb-4" style={{ color: "var(--slate-800)", fontWeight: 600 }}>Line Items</h4>
                    <div className="flex-gap-2 mb-4 flex-wrap">
                      <div style={{ flex: 1, minWidth: "200px" }}>
                        <SearchableSelect
                          options={products.map((p) => ({
                            id: p.id,
                            label: `${p.name} (${formatCurrency(p.selling_price)} - Stock: ${p.stock})`
                          }))}
                          value={currentItem.product_id}
                          onChange={(val) =>
                            setCurrentItem({ ...currentItem, product_id: val })
                          }
                          placeholder="-- Add Product --"
                          emptyMessage="No products found"
                        />
                      </div>
                      <input
                        className="form-input"
                        type="number"
                        min="1"
                        placeholder="Qty"
                        style={{ width: "90px" }}
                        value={currentItem.quantity}
                        onChange={(e) =>
                          setCurrentItem({ ...currentItem, quantity: e.target.value })
                        }
                      />
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ width: "auto" }}
                        onClick={handleAddItem}
                      >
                        Add Item
                      </button>
                    </div>

                    {selectedItems.length > 0 && (
                      <div className="retail-table-container mb-4">
                        <table className="retail-table">
                          <thead>
                            <tr>
                              <th>Product</th>
                              <th style={{ textAlign: "right" }}>Price</th>
                              <th style={{ textAlign: "center" }}>Qty</th>
                              <th style={{ textAlign: "right" }}>Total</th>
                              <th style={{ textAlign: "center" }}>Remove</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedItems.map((item, idx) => (
                              <tr key={idx}>
                                <td>{item.product?.name}</td>
                                <td style={{ textAlign: "right" }}>
                                  {formatCurrency(item.product?.selling_price)}
                                </td>
                                <td style={{ textAlign: "center" }}>{item.quantity}</td>
                                <td style={{ textAlign: "right", fontWeight: "600" }}>
                                  {formatCurrency(item.product?.selling_price * parseInt(item.quantity))}
                                </td>
                                <td style={{ textAlign: "center" }}>
                                  <button
                                    type="button"
                                    onClick={() => handleRemoveItem(idx)}
                                    style={{
                                      background: "none",
                                      border: "none",
                                      color: "var(--danger-500)",
                                      cursor: "pointer",
                                    }}
                                  >
                                    ✕
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  <div
                    style={{
                      borderTop: "1px solid var(--slate-100)",
                      paddingTop: "16px",
                      display: "flex",
                      justifyContent: "flex-end",
                    }}
                  >
                    <div style={{ width: "320px", display: "flex", flexDirection: "column", gap: "10px" }}>
                      <div className="flex-between">
                        <span style={{ color: "var(--slate-500)", fontSize: "0.875rem" }}>Subtotal:</span>
                        <span style={{ fontWeight: 600 }}>{formatCurrency(subtotal)}</span>
                      </div>
                      <div className="flex-between">
                        <span style={{ color: "var(--slate-500)", fontSize: "0.875rem" }}>
                          Tax ({formData.taxRate}%):
                        </span>
                        <span style={{ fontWeight: 600 }}>{formatCurrency(tax)}</span>
                      </div>
                      <div className="flex-between" style={{ alignItems: "center" }}>
                        <span style={{ color: "var(--slate-500)", fontSize: "0.875rem" }}>Discount Amount:</span>
                        <input
                          className="form-input"
                          type="number"
                          min="0"
                          step="0.01"
                          style={{ width: "120px", padding: "4px 8px", textAlign: "right" }}
                          value={formData.discount}
                          onChange={(e) => setFormData({ ...formData, discount: e.target.value })}
                        />
                      </div>
                      <div
                        className="flex-between"
                        style={{ borderTop: "1px dashed var(--slate-200)", paddingTop: "10px", marginTop: "4px" }}
                      >
                        <span style={{ fontWeight: "700", color: "var(--slate-800)" }}>Total Amount:</span>
                        <span style={{ fontWeight: "800", color: "var(--brand-500)", fontSize: "1.125rem" }}>
                          {formatCurrency(total)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex-gap-2 mt-4" style={{ justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setShowCreateForm(false)}
                      disabled={loading}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn-primary"
                      style={{ width: "auto" }}
                      disabled={loading}
                    >
                      {loading ? "Creating..." : "Save Invoice"}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {viewingInvoice && (
              <div className="auth-card mb-6" style={{ maxWidth: "800px", margin: "0 auto", padding: "40px" }} id="printable-invoice">
                {statusError && (
                  <div className="auth-error mb-4 no-print">
                    <span>{statusError}</span>
                  </div>
                )}
                <style>{`
                  @media print {
                    body * {
                      visibility: hidden !important;
                    }
                    #printable-invoice, #printable-invoice * {
                      visibility: visible !important;
                    }
                    #printable-invoice {
                      position: absolute !important;
                      left: 0 !important;
                      top: 0 !important;
                      width: 100% !important;
                      border: none !important;
                      box-shadow: none !important;
                      padding: 24px !important;
                      margin: 0 !important;
                      background: white !important;
                      color: black !important;
                    }
                    html, body, #root, .app-layout, .app-body, .app-content-main, .dashboard-page, .dashboard-main {
                      height: auto !important;
                      min-height: 0 !important;
                      max-height: none !important;
                      overflow: visible !important;
                      position: static !important;
                      margin: 0 !important;
                      padding: 0 !important;
                    }
                    .sidebar, .navbar, .chatbot-container, .no-print {
                      display: none !important;
                    }
                    h1, h2, h3, h4, span, td, th, p {
                      color: #000000 !important;
                    }
                    tr {
                      page-break-inside: avoid !important;
                    }
                  }
                `}</style>

                {/* Business Name Header with line */}
                <div style={{ textAlign: "center", borderBottom: "3px solid #000", paddingBottom: "16px", marginBottom: "20px" }}>
                  <h2 style={{ fontSize: "2rem", fontWeight: "800", color: "var(--slate-800)", margin: 0 }}>
                    {selectedBusiness?.name}
                  </h2>
                  <p style={{ fontSize: "0.875rem", color: "var(--slate-500)", marginTop: "6px", marginBottom: 0 }}>
                    {selectedBusiness?.address && `${selectedBusiness.address}, `}
                    {selectedBusiness?.city && `${selectedBusiness.city}, `}
                    {selectedBusiness?.state && `${selectedBusiness.state}`}
                    {selectedBusiness?.gst_number && ` | GSTIN: ${selectedBusiness.gst_number}`}
                  </p>
                </div>

                {/* Customer Name Header with line */}
                <div className="invoice-header-flex">
                  <div>
                    <span style={{ color: "var(--slate-400)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: "700" }}>
                      Bill To
                    </span>
                    <h3 style={{ fontSize: "1.25rem", fontWeight: "700", color: "var(--slate-800)", margin: "4px 0 0 0" }}>
                      {viewingInvoice.customer?.name || "Cash Customer"}
                    </h3>
                    <p style={{ fontSize: "0.875rem", color: "var(--slate-500)", margin: "2px 0 0 0" }}>
                      {viewingInvoice.customer?.phone_number && `Phone: ${viewingInvoice.customer.phone_number}`}
                      {viewingInvoice.customer?.email && ` | Email: ${viewingInvoice.customer.email}`}
                    </p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ fontSize: "0.875rem", color: "var(--slate-500)", margin: 0 }}>
                      Invoice: <strong>#{selectedBusiness?.invoice_prefix || "INV"}-{viewingInvoice.id}</strong>
                    </p>
                    <p style={{ fontSize: "0.875rem", color: "var(--slate-500)", margin: "4px 0 0 0" }}>
                      Date: <strong>{formatDate(viewingInvoice.created_at)}</strong>
                    </p>
                  </div>
                </div>

                {/* Item Table with Total at Last Row */}
                <div className="retail-table-container mb-6" style={{ border: "1px solid var(--slate-200)", borderRadius: "6px", overflow: "hidden" }}>
                  <table className="retail-table">
                    <thead>
                      <tr>
                        <th>Product / Item</th>
                        <th style={{ textAlign: "right" }}>Unit Price</th>
                        <th style={{ textAlign: "center" }}>Qty</th>
                        <th style={{ textAlign: "right" }}>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {viewingInvoice.items?.map((item, index) => (
                        <tr key={index}>
                          <td style={{ fontWeight: 600 }}>{item.product?.name || "Product"}</td>
                          <td style={{ textAlign: "right" }}>
                            {formatCurrency(item.product?.selling_price || 0)}
                          </td>
                          <td style={{ textAlign: "center" }}>{item.quantity}</td>
                          <td style={{ textAlign: "right", fontWeight: 600 }}>
                            {formatCurrency((item.product?.selling_price || 0) * item.quantity)}
                          </td>
                        </tr>
                      ))}
                      <tr style={{ borderTop: "2px solid var(--slate-200)", backgroundColor: "var(--slate-50)" }}>
                        <td colSpan="3" style={{ textAlign: "right", fontWeight: "700", color: "var(--slate-800)", padding: "12px 16px" }}>
                          Total Amount:
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "800", color: "var(--brand-600)", fontSize: "1.1rem", padding: "12px 16px" }}>
                          {formatCurrency(viewingInvoice.total)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Bottom area: Stacked values on left; RetailIQ branding on right */}
                <div className="invoice-footer-flex">
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <p style={{ fontSize: "0.875rem", color: "var(--slate-500)", margin: 0 }}>
                      Subtotal: <strong style={{ color: "var(--slate-800)" }}>{formatCurrency(viewingInvoice.subtotal)}</strong>
                    </p>
                    <p style={{ fontSize: "0.875rem", color: "var(--slate-500)", margin: 0 }}>
                      Tax (GST): <strong style={{ color: "var(--slate-800)" }}>{formatCurrency(viewingInvoice.tax)}</strong>
                    </p>
                    <p style={{ fontSize: "0.875rem", color: "var(--slate-500)", margin: 0 }}>
                      Discount: <strong style={{ color: "var(--slate-800)" }}>-{formatCurrency(viewingInvoice.discount)}</strong>
                    </p>
                    {viewingInvoice.notes && (
                      <p style={{ fontSize: "0.8125rem", color: "var(--slate-400)", marginTop: "10px", maxWidth: "400px", fontStyle: "italic", margin: "10px 0 0 0" }}>
                        Notes: {viewingInvoice.notes}
                      </p>
                    )}
                  </div>
                  <div style={{
                    border: "2px solid var(--slate-800)",
                    padding: "8px 16px",
                    fontWeight: "800",
                    fontSize: "1.125rem",
                    borderRadius: "6px",
                    color: "var(--slate-800)",
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    backgroundColor: "var(--indigo-100)"
                  }}>
                    RetailIQ
                  </div>
                </div>

                <div className="flex-gap-2 mt-6 no-print" style={{ justifyContent: "flex-end", flexWrap: "wrap", borderTop: "1px solid var(--slate-100)", paddingTop: "16px" }}>
                  {(viewingInvoice.status === "PENDING" || viewingInvoice.status === "DRAFT") && (
                    <>
                      <button
                        className="btn-primary"
                        style={{ width: "auto" }}
                        onClick={() => handleUpdateStatus("PAID")}
                        disabled={statusLoading}
                      >
                        {statusLoading ? "Updating..." : "Mark as Paid"}
                      </button>
                      <button
                        className="btn-danger"
                        style={{ width: "auto" }}
                        onClick={() => handleUpdateStatus("CANCELLED")}
                        disabled={statusLoading}
                      >
                        {statusLoading ? "Updating..." : "Cancel Invoice"}
                      </button>
                    </>
                  )}
                  {viewingInvoice.status === "PAID" && (
                    <>
                      <button
                        className="btn-danger"
                        style={{ width: "auto" }}
                        onClick={() => handleUpdateStatus("REFUNDED")}
                        disabled={statusLoading}
                      >
                        {statusLoading ? "Updating..." : "Refund Invoice"}
                      </button>
                      <button
                        className="btn-danger"
                        style={{ width: "auto" }}
                        onClick={() => handleUpdateStatus("CANCELLED")}
                        disabled={statusLoading}
                      >
                        {statusLoading ? "Updating..." : "Cancel Invoice"}
                      </button>
                    </>
                  )}
                  <button
                    className="btn-secondary"
                    onClick={() => {
                      setViewingInvoice(null);
                      setStatusError("");
                    }}
                    disabled={statusLoading}
                  >
                    Close Invoice
                  </button>
                  <button
                    className="btn-primary"
                    style={{ width: "auto" }}
                    onClick={handlePrint}
                    disabled={statusLoading}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ marginRight: "4px" }}>
                      <polyline points="6 9 6 2 18 2 18 9" />
                      <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                      <rect x="6" y="14" width="12" height="8" />
                    </svg>
                    Print / Print PDF
                  </button>
                </div>
              </div>
            )}

            {!showCreateForm && !viewingInvoice && (
              <>
                <div style={{ display: "flex", gap: "16px", marginBottom: "20px" }}>
                  <div className="input-wrapper" style={{ flex: 1 }}>
                    <svg
                      className="input-icon"
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      className="form-input"
                      type="text"
                      placeholder="Search invoices by customer name or invoice number (e.g. inv-3)..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>

                <div className="retail-table-container">
                  {loading && invoices.length === 0 ? (
                    <div style={{ textAlign: "center", padding: "40px" }}>
                      <span className="spinner" style={{ display: "inline-block" }} />
                      <p style={{ marginTop: "12px", color: "var(--slate-500)" }}>Loading invoices...</p>
                    </div>
                  ) : filteredInvoices.length === 0 ? (
                    <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--slate-500)" }}>
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--slate-300)" strokeWidth="1.5" style={{ marginBottom: "12px" }}>
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                      </svg>
                      <h3>No Invoices Found</h3>
                      <p style={{ fontSize: "0.875rem" }}>
                        {searchQuery ? "Try refining your search terms." : "Create your first customer invoice manually."}
                      </p>
                    </div>
                  ) : (
                    <>
                      <table className="retail-table">
                        <thead>
                          <tr>
                            <th>Invoice ID</th>
                            <th>Customer</th>
                            <th>Date</th>
                            <th>Source</th>
                            <th style={{ textAlign: "right" }}>Total Amount</th>
                            <th style={{ textAlign: "center" }}>Status</th>
                            <th style={{ textAlign: "center" }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentInvoices.map((invoice) => (
                            <tr key={invoice.id}>
                              <td style={{ fontFamily: "monospace", fontWeight: "600", fontSize: "0.8125rem" }}>
                                #{selectedBusiness?.invoice_prefix || "INV"}-{invoice.id}
                              </td>
                              <td style={{ fontWeight: "600", color: "var(--slate-900)" }}>
                                {invoice.customer?.name || "Cash Customer"}
                              </td>
                              <td style={{ color: "var(--slate-500)", fontSize: "0.8125rem" }}>
                                {formatDate(invoice.created_at)}
                              </td>
                              <td>
                                <span className="badge badge-neutral" style={{ fontSize: "0.6875rem", padding: "2px 6px" }}>
                                  {invoice.source}
                                </span>
                              </td>
                              <td style={{ textAlign: "right", fontWeight: "700", color: "var(--slate-900)" }}>
                                {formatCurrency(invoice.total)}
                              </td>
                              <td style={{ textAlign: "center" }}>
                                {getStatusBadge(invoice.status)}
                              </td>
                              <td style={{ textAlign: "center" }}>
                                <button
                                  className="btn-secondary"
                                  style={{ padding: "6px 10px", fontSize: "0.75rem" }}
                                  onClick={() => {
                                    setViewingInvoice(invoice);
                                    setStatusError("");
                                  }}
                                >
                                  View Details
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {totalPages > 1 && (
                        <div className="flex-between" style={{ marginTop: "16px", padding: "12px 16px", borderTop: "1px solid var(--slate-100)" }}>
                          <span style={{ fontSize: "0.875rem", color: "var(--slate-500)" }}>
                            Showing <strong>{indexOfFirstInvoice + 1}</strong> to <strong>{Math.min(indexOfLastInvoice, filteredInvoices.length)}</strong> of <strong>{filteredInvoices.length}</strong> invoices
                          </span>
                          <div className="flex-gap-2">
                            <button
                              className="btn-secondary"
                              style={{ padding: "6px 12px", fontSize: "0.875rem" }}
                              disabled={currentPage === 1}
                              onClick={() => setCurrentPage(prev => prev - 1)}
                            >
                              Previous
                            </button>
                            <span style={{ fontSize: "0.875rem", color: "var(--slate-700)", alignSelf: "center", margin: "0 8px" }}>
                              Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
                            </span>
                            <button
                              className="btn-secondary"
                              style={{ padding: "6px 12px", fontSize: "0.875rem" }}
                              disabled={currentPage === totalPages}
                              onClick={() => setCurrentPage(prev => prev + 1)}
                            >
                              Next
                            </button>
                          </div>
                        </div>
                      )}
                    </>
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

export default Invoices;
