import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useLocation, useNavigate } from "react-router-dom";
import { fetchProducts, postProduct, updateProduct, deleteProduct } from "../../features/product/productThunk";
import { validateField, validateForm, hasErrors, PRODUCT_ADD_RULES, PRODUCT_EDIT_RULES } from "../../utils/formValidation";

const Products = () => {
  const dispatch = useDispatch();
  const location = useLocation();
  const navigate = useNavigate();
  const { selectedBusinessId, businesses } = useSelector((state) => state.business);
  const { data: products, loading, error } = useSelector((state) => state.products);
  const selectedBusiness = businesses.find((b) => b.id === selectedBusinessId);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState({
    name: "",
    original_price: "",
    selling_price: "",
    stock: "",
    sku: "",
    barcode: "",
    category: "",
    description: "",
  });
  const [addErrors, setAddErrors] = useState({});
  const [addTouched, setAddTouched] = useState({});
  const [editingProduct, setEditingProduct] = useState(null);
  const [editErrors, setEditErrors] = useState({});
  const [editTouched, setEditTouched] = useState({});
  useEffect(() => {
    if (location.state?.showAddForm) {
      const timer = setTimeout(() => {
        setShowAddForm(true);
        window.history.replaceState({}, document.title);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [location.state]);
  useEffect(() => {
    if (selectedBusinessId) {
      dispatch(fetchProducts(selectedBusinessId));
    }
  }, [dispatch, selectedBusinessId]);
  useEffect(() => {
    if (!showAddForm) {
      setAddErrors({});
      setAddTouched({});
    }
  }, [showAddForm]);
  useEffect(() => {
    if (!editingProduct) {
      setEditErrors({});
      setEditTouched({});
    }
  }, [editingProduct]);
  const handleInputChange = (e, formType = "add") => {
    const { name, value } = e.target;
    if (formType === "add") {
      setAddForm((prev) => ({ ...prev, [name]: value }));
      if (addTouched[name]) {
        const fieldError = validateField(value, PRODUCT_ADD_RULES[name]);
        setAddErrors((prev) => {
          const next = { ...prev };
          if (fieldError) next[name] = fieldError;
          else delete next[name];
          return next;
        });
      }
    } else {
      setEditingProduct((prev) => ({ ...prev, [name]: value }));
      if (editTouched[name]) {
        const fieldError = validateField(value, PRODUCT_EDIT_RULES[name]);
        setEditErrors((prev) => {
          const next = { ...prev };
          if (fieldError) next[name] = fieldError;
          else delete next[name];
          return next;
        });
      }
    }
  };
  const handleBlur = (e, formType = "add") => {
    const { name, value } = e.target;
    if (formType === "add") {
      setAddTouched((prev) => ({ ...prev, [name]: true }));
      const fieldError = validateField(value, PRODUCT_ADD_RULES[name]);
      setAddErrors((prev) => {
        const next = { ...prev };
        if (fieldError) next[name] = fieldError;
        else delete next[name];
        return next;
      });
    } else {
      setEditTouched((prev) => ({ ...prev, [name]: true }));
      const fieldError = validateField(value, PRODUCT_EDIT_RULES[name]);
      setEditErrors((prev) => {
        const next = { ...prev };
        if (fieldError) next[name] = fieldError;
        else delete next[name];
        return next;
      });
    }
  };
  const handleAddSubmit = async (e) => {
    e.preventDefault();
    if (!selectedBusinessId) return;
    const allTouched = {};
    Object.keys(PRODUCT_ADD_RULES).forEach((k) => (allTouched[k] = true));
    setAddTouched(allTouched);
    const formErrors = validateForm(addForm, PRODUCT_ADD_RULES);
    setAddErrors(formErrors);
    if (hasErrors(formErrors)) return;
    const payload = {
      ...addForm,
      business_id: selectedBusinessId,
      original_price: parseFloat(addForm.original_price),
      selling_price: parseFloat(addForm.selling_price),
      stock: parseInt(addForm.stock) || 0,
    };
    const result = await dispatch(postProduct(payload));
    if (!result.error) {
      setShowAddForm(false);
      setAddForm({
        name: "",
        original_price: "",
        selling_price: "",
        stock: "",
        sku: "",
        barcode: "",
        category: "",
        description: "",
      });
    }
  };
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!editingProduct) return;
    const allTouched = {};
    Object.keys(PRODUCT_EDIT_RULES).forEach((k) => (allTouched[k] = true));
    setEditTouched(allTouched);
    const formErrors = validateForm(editingProduct, PRODUCT_EDIT_RULES);
    setEditErrors(formErrors);
    if (hasErrors(formErrors)) return;
    const payload = {
      productId: editingProduct.id,
      data: {
        name: editingProduct.name,
        original_price: parseFloat(editingProduct.original_price),
        selling_price: parseFloat(editingProduct.selling_price),
        stock: parseInt(editingProduct.stock) || 0,
        sku: editingProduct.sku || null,
        barcode: editingProduct.barcode || null,
        category: editingProduct.category || null,
        description: editingProduct.description || null,
      },
    };
    const result = await dispatch(updateProduct(payload));
    if (!result.error) {
      setEditingProduct(null);
    }
  };
  const handleDelete = (productId) => {
    if (window.confirm("Are you sure you want to delete this product?")) {
      dispatch(deleteProduct(productId));
    }
  };
  const formatCurrency = (value) => {
    const currencySymbol = selectedBusiness?.currency || "INR";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currencySymbol,
    }).format(value);
  };
  const filteredProducts = products.filter((p) => {
    const query = searchQuery.toLowerCase();
    return (
      p.name.toLowerCase().includes(query) ||
      (p.sku && p.sku.toLowerCase().includes(query)) ||
      (p.barcode && p.barcode.toLowerCase().includes(query)) ||
      (p.category && p.category.toLowerCase().includes(query))
    );
  });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedBusinessId]);
  const totalPages = Math.ceil(filteredProducts.length / itemsPerPage);
  const indexOfLastProduct = currentPage * itemsPerPage;
  const indexOfFirstProduct = indexOfLastProduct - itemsPerPage;
  const currentProducts = filteredProducts.slice(indexOfFirstProduct, indexOfLastProduct);
  const renderError = (fieldName, formType = "add") => {
    const errs = formType === "add" ? addErrors : editErrors;
    const tch = formType === "add" ? addTouched : editTouched;
    return tch[fieldName] && errs[fieldName] ? (
      <span className="field-error">{errs[fieldName]}</span>
    ) : null;
  };

  const totalProducts = products?.length || 0;
  const totalStock = products?.reduce((acc, p) => acc + (Number(p.stock) || 0), 0) || 0;
  const totalInventoryValue = products?.reduce(
    (acc, p) => acc + (Number(p.stock) || 0) * (Number(p.selling_price) || 0),
    0
  ) || 0;
  const lowStockCount = products?.filter((p) => (Number(p.stock) || 0) <= 10).length || 0;
  const outOfStockCount = products?.filter((p) => (Number(p.stock) || 0) === 0).length || 0;

  const inputClass = (fieldName, formType = "add", base = "form-input") => {
    const errs = formType === "add" ? addErrors : editErrors;
    const tch = formType === "add" ? addTouched : editTouched;
    return `${base}${tch[fieldName] && errs[fieldName] ? " invalid" : ""}`;
  };
  const activeFormType = showAddForm ? "add" : "edit";
  return (
    <div className="dashboard-page">
      <main className="dashboard-main">
        {!selectedBusinessId ? (
          <div className="empty-state-card">
            <h2 className="empty-state-title">No Active Business Selected</h2>
            <p className="empty-state-description">
              Please create or select a business from the top menu to view products.
            </p>
            <button className="btn-primary" style={{ width: "auto" }} onClick={() => navigate("/business")}>
              Create Business
            </button>
          </div>
        ) : (
          <>
            { }
            <div className="dashboard-header flex-between">
              <div>
                <h1 className="dashboard-greeting">Product Catalog</h1>
                <p className="dashboard-tagline">
                  Manage inventory, pricing, and stock levels for <strong>{selectedBusiness?.name}</strong>.
                </p>
              </div>
              {!showAddForm && !editingProduct && (
                <button
                  className="btn-primary"
                  style={{ width: "auto" }}
                  onClick={() => setShowAddForm(true)}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  Add Product
                </button>
              )}
            </div>

            {/* KPI Cards Section */}
            {!showAddForm && !editingProduct && (
              <div className="stats-grid">
                {loading && products.length === 0 ? (
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
                      <div className="stat-icon stat-icon-products">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                          <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                          <line x1="12" y1="22.08" x2="12" y2="12" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Total Products</span>
                        <span className="stat-value">{totalProducts}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          Distinct catalog items
                        </span>
                      </div>
                    </div>

                    <div className="stat-card">
                      <div className="stat-icon stat-icon-orders">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polygon points="12 2 2 7 12 12 22 7 12 2" />
                          <polyline points="2 17 12 22 22 17" />
                          <polyline points="2 12 12 17 22 12" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Total Stock</span>
                        <span className="stat-value">{totalStock.toLocaleString("en-IN")}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          Units in inventory
                        </span>
                      </div>
                    </div>

                    <div className="stat-card">
                      <div className="stat-icon stat-icon-revenue">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <line x1="12" y1="1" x2="12" y2="23" />
                          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Inventory Value</span>
                        <span className="stat-value">{formatCurrency(totalInventoryValue)}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          Total retail stock value
                        </span>
                      </div>
                    </div>

                    <div className="stat-card">
                      <div className="stat-icon" style={{ backgroundColor: lowStockCount > 0 ? "var(--danger-50)" : "var(--success-50)", color: lowStockCount > 0 ? "var(--danger-600)" : "var(--success-600)" }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                          <line x1="12" y1="9" x2="12" y2="13" />
                          <line x1="12" y1="17" x2="12.01" y2="17" />
                        </svg>
                      </div>
                      <div className="stat-content">
                        <span className="stat-label">Low Stock</span>
                        <span className="stat-value" style={{ color: lowStockCount > 0 ? "var(--danger-600)" : "inherit" }}>
                          {lowStockCount}
                        </span>
                        <span style={{ fontSize: "0.75rem", color: lowStockCount > 0 ? "var(--danger-500)" : "var(--slate-400)", marginTop: "4px", fontWeight: 500 }}>
                          {outOfStockCount > 0 ? `${outOfStockCount} out of stock` : "Threshold ≤ 10 units"}
                        </span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
            { }
            {error && (
              <div className="auth-error mb-4">
                <span>{typeof error === "string" ? error : "An error occurred with products management."}</span>
              </div>
            )}
            { }
            {(showAddForm || editingProduct) && (
              <div className="auth-card mb-6" style={{ maxWidth: "none" }}>
                <h3 className="mb-4" style={{ borderBottom: "1px solid var(--slate-200)", paddingBottom: "8px", color: "var(--slate-800)" }}>
                  {showAddForm ? "Add New Product" : `Edit Product: ${editingProduct?.name}`}
                </h3>
                <form onSubmit={showAddForm ? handleAddSubmit : handleEditSubmit} className="standard-form">
                  <div className="grid-2">
                    <div className="form-group">
                      <label className="form-label">Product Name *</label>
                      <input
                        className={inputClass("name", activeFormType)}
                        type="text"
                        name="name"
                        required
                        minLength={2}
                        maxLength={50}
                        placeholder="E.g., Milk Packet 1L"
                        value={showAddForm ? addForm.name : editingProduct?.name || ""}
                        onChange={(e) => handleInputChange(e, activeFormType)}
                        onBlur={(e) => handleBlur(e, activeFormType)}
                      />
                      {renderError("name", activeFormType)}
                      <span className="field-hint">2–50 characters</span>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Category</label>
                      <input
                        className={inputClass("category", activeFormType)}
                        type="text"
                        name="category"
                        minLength={2}
                        maxLength={100}
                        placeholder="E.g., Dairy"
                        value={showAddForm ? addForm.category : editingProduct?.category || ""}
                        onChange={(e) => handleInputChange(e, activeFormType)}
                        onBlur={(e) => handleBlur(e, activeFormType)}
                      />
                      {renderError("category", activeFormType)}
                      <span className="field-hint">2–100 characters (optional)</span>
                    </div>
                  </div>
                  <div className="grid-3">
                    <div className="form-group">
                      <label className="form-label">MRP (Original Price) *</label>
                      <input
                        className={inputClass("original_price", activeFormType)}
                        type="number"
                        step="0.01"
                        min="0.01"
                        name="original_price"
                        required
                        placeholder="0.00"
                        value={showAddForm ? addForm.original_price : editingProduct?.original_price || ""}
                        onChange={(e) => handleInputChange(e, activeFormType)}
                        onBlur={(e) => handleBlur(e, activeFormType)}
                      />
                      {renderError("original_price", activeFormType)}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Selling Price *</label>
                      <input
                        className={inputClass("selling_price", activeFormType)}
                        type="number"
                        step="0.01"
                        min="0.01"
                        name="selling_price"
                        required
                        placeholder="0.00"
                        value={showAddForm ? addForm.selling_price : editingProduct?.selling_price || ""}
                        onChange={(e) => handleInputChange(e, activeFormType)}
                        onBlur={(e) => handleBlur(e, activeFormType)}
                      />
                      {renderError("selling_price", activeFormType)}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Stock Quantity *</label>
                      <input
                        className={inputClass("stock", activeFormType)}
                        type="number"
                        min="0"
                        step="1"
                        name="stock"
                        required
                        placeholder="0"
                        value={showAddForm ? addForm.stock : editingProduct?.stock || ""}
                        onChange={(e) => handleInputChange(e, activeFormType)}
                        onBlur={(e) => handleBlur(e, activeFormType)}
                      />
                      {renderError("stock", activeFormType)}
                    </div>
                  </div>
                  <div className="grid-2">
                    <div className="form-group">
                      <label className="form-label">SKU (Stock Keeping Unit)</label>
                      <input
                        className={inputClass("sku", activeFormType)}
                        type="text"
                        name="sku"
                        maxLength={50}
                        placeholder="E.g., DAIRY-MILK-1L"
                        value={showAddForm ? addForm.sku : editingProduct?.sku || ""}
                        onChange={(e) => handleInputChange(e, activeFormType)}
                        onBlur={(e) => handleBlur(e, activeFormType)}
                      />
                      {renderError("sku", activeFormType)}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Barcode</label>
                      <input
                        className={inputClass("barcode", activeFormType)}
                        type="text"
                        name="barcode"
                        maxLength={100}
                        placeholder="Scan or type barcode"
                        value={showAddForm ? addForm.barcode : editingProduct?.barcode || ""}
                        onChange={(e) => handleInputChange(e, activeFormType)}
                        onBlur={(e) => handleBlur(e, activeFormType)}
                      />
                      {renderError("barcode", activeFormType)}
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Description</label>
                    <textarea
                      className={`${inputClass("description", activeFormType)}`}
                      style={{ minHeight: "80px", resize: "vertical" }}
                      name="description"
                      maxLength={500}
                      placeholder="Product details, package info, etc."
                      value={showAddForm ? addForm.description : editingProduct?.description || ""}
                      onChange={(e) => handleInputChange(e, activeFormType)}
                      onBlur={(e) => handleBlur(e, activeFormType)}
                    />
                    {renderError("description", activeFormType)}
                    <span className="field-hint">
                      {(showAddForm ? addForm.description : editingProduct?.description || "").length}/500 characters
                    </span>
                  </div>
                  <div className="flex-gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => {
                        setShowAddForm(false);
                        setEditingProduct(null);
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn-primary"
                      style={{ width: "auto" }}
                      disabled={loading}
                    >
                      {showAddForm ? "Add Product" : "Save Changes"}
                    </button>
                  </div>
                </form>
              </div>
            )}
            { }
            {!showAddForm && !editingProduct && (
              <>
                { }
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
                      placeholder="Search inventory by product name, SKU, category, or barcode..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
                { }
                <div className="retail-table-container">
                  {loading && products.length === 0 ? (
                    <div style={{ textAlign: "center", padding: "40px" }}>
                      <span className="spinner" style={{ display: "inline-block" }} />
                      <p style={{ marginTop: "12px", color: "var(--slate-500)" }}>Loading products...</p>
                    </div>
                  ) : filteredProducts.length === 0 ? (
                    <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--slate-500)" }}>
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--slate-300)" strokeWidth="1.5" style={{ marginBottom: "12px" }}>
                        <rect x="3" y="3" width="18" height="18" rx="2" />
                        <line x1="9" y1="9" x2="15" y2="9" />
                        <line x1="9" y1="13" x2="15" y2="13" />
                        <line x1="9" y1="17" x2="13" y2="17" />
                      </svg>
                      <h3>No Products Found</h3>
                      <p style={{ fontSize: "0.875rem" }}>
                        {searchQuery ? "Try refining your search terms." : "Get started by adding products to your catalog."}
                      </p>
                    </div>
                  ) : (
                    <>
                      <table className="retail-table">
                        <thead>
                          <tr>
                            <th>Product Name</th>
                            <th>SKU</th>
                            <th>Category</th>
                            <th style={{ textAlign: "right" }}>MRP</th>
                            <th style={{ textAlign: "right" }}>Selling Price</th>
                            <th style={{ textAlign: "center" }}>Stock</th>
                            <th style={{ textAlign: "center" }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentProducts.map((product) => {
                            const isLowStock = product.stock === 0;
                            return (
                              <tr key={product.id}>
                                <td style={{ fontWeight: "600", color: "var(--slate-900)" }}>
                                  {product.name}
                                  {product.description && (
                                    <div style={{ fontWeight: "normal", fontSize: "0.75rem", color: "var(--slate-400)", marginTop: "2px" }}>
                                      {product.description}
                                    </div>
                                  )}
                                </td>
                                <td style={{ fontFamily: "monospace", fontSize: "0.8125rem" }}>
                                  {product.sku || "—"}
                                  </td>
                                <td>
                                  {product.category ? (
                                    <span className="badge badge-neutral">{product.category}</span>
                                  ) : (
                                    "—"
                                  )}
                                </td>
                                <td style={{ textAlign: "right", color: "var(--slate-400)" }}>
                                  {formatCurrency(product.original_price)}
                                </td>
                                <td style={{ textAlign: "right", fontWeight: "600", color: "var(--slate-900)" }}>
                                  {formatCurrency(product.selling_price)}
                                </td>
                                <td style={{ textAlign: "center" }}>
                                  <span className={`badge ${isLowStock ? "badge-danger" : "badge-success"}`}>
                                    {product.stock} in stock
                                  </span>
                                </td>
                                <td style={{ textAlign: "center" }}>
                                  <div className="flex-gap-2" style={{ justifyContent: "center" }}>
                                    <button
                                      className="btn-secondary"
                                      style={{ padding: "6px 10px", fontSize: "0.75rem" }}
                                      onClick={() => setEditingProduct(product)}
                                    >
                                      Edit
                                    </button>
                                    <button
                                      className="btn-danger"
                                      style={{ padding: "6px 10px", fontSize: "0.75rem", background: "none", border: "1px solid var(--danger-100)", color: "var(--danger-600)" }}
                                      onClick={() => handleDelete(product.id)}
                                    >
                                      Delete
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      {totalPages > 1 && (
                        <div className="flex-between" style={{ marginTop: "16px", padding: "12px 16px", borderTop: "1px solid var(--slate-100)" }}>
                          <span style={{ fontSize: "0.875rem", color: "var(--slate-500)" }}>
                            Showing <strong>{indexOfFirstProduct + 1}</strong> to <strong>{Math.min(indexOfLastProduct, filteredProducts.length)}</strong> of <strong>{filteredProducts.length}</strong> products
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
export default Products;
