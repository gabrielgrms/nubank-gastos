const API_URL = window.location.hostname === "localhost" ? "http://localhost:8000/api" : "/api";

let token = localStorage.getItem("token");
let monthlyChart;
let annualChart;
let categoriesCache = [];

const authView = document.getElementById("auth-view");
const appView = document.getElementById("app-view");
const authMessage = document.getElementById("auth-message");
const linkMessage = document.getElementById("link-message");

const showLoginBtn = document.getElementById("show-login");
const showRegisterBtn = document.getElementById("show-register");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

const menuButtons = document.querySelectorAll(".menu-btn");
const pages = document.querySelectorAll(".page");
const logoutBtn = document.getElementById("logout-btn");
const linkStatus = document.getElementById("link-status");
const goLinkPageButton = document.getElementById("go-link-page");
const linkAccountButton = document.getElementById("link-account-btn");
const averageCard = document.getElementById("average-card");
const futureExpensesBody = document.getElementById("future-expenses");
const expensesTable = document.getElementById("expenses-table");

const categoryModal = document.getElementById("category-modal");
const openCategoryModal = document.getElementById("open-category-modal");
const cancelCategoryModal = document.getElementById("cancel-category-modal");
const newCategoryForm = document.getElementById("new-category-form");

function setAuthMode(mode) {
  showLoginBtn.classList.toggle("active", mode === "login");
  showRegisterBtn.classList.toggle("active", mode === "register");
  loginForm.classList.toggle("active", mode === "login");
  registerForm.classList.toggle("active", mode === "register");
}

function showPage(page) {
  pages.forEach((el) => el.classList.toggle("active", el.id === `${page}-page`));
  menuButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.page === page));
}

function currency(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: "Erro inesperado" }));
    throw new Error(data.detail || "Erro inesperado");
  }
  if (response.status === 204) return null;
  return response.json();
}

function renderMonthlyChart(items) {
  const ctx = document.getElementById("monthly-chart");
  if (monthlyChart) monthlyChart.destroy();
  monthlyChart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: items.map((item) => item.category),
      datasets: [{ data: items.map((item) => item.total), backgroundColor: ["#820ad1", "#9e2ee8", "#ba4df8", "#d982ff", "#e9b8ff"] }],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });
}

function renderAnnualChart(items) {
  const ctx = document.getElementById("annual-chart");
  if (annualChart) annualChart.destroy();
  annualChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map((item) => `Mês ${item.month}`),
      datasets: [{ label: "Total", data: items.map((item) => item.total), backgroundColor: "#820ad1" }],
    },
  });
}

async function loadDashboard() {
  const me = await api("/me");
  linkStatus.textContent = me.has_nubank_link
    ? "Conta Nubank vinculada"
    : "Conta Nubank não vinculada. Os gráficos ficam em branco até a vinculação.";

  const [monthly, annual, average, future] = await Promise.all([
    api("/dashboard/monthly"),
    api("/dashboard/annual"),
    api("/dashboard/average"),
    api("/dashboard/future"),
  ]);

  renderMonthlyChart(monthly.data);
  renderAnnualChart(annual.data);
  averageCard.textContent = average.average_last_6_months === null ? "R$ 0,00" : currency(average.average_last_6_months);

  futureExpensesBody.innerHTML = future.data.length
    ? future.data
        .map(
          (item) => `<tr><td>${item.description}</td><td>${item.installment_label || "-"}</td><td>${item.due_date}</td><td>${currency(item.amount)}</td></tr>`
        )
        .join("")
    : `<tr><td colspan="4">Sem gastos futuros.</td></tr>`;
}

async function loadCategories() {
  categoriesCache = await api("/categories");
  return categoriesCache;
}

function categorySelect(expense) {
  const options = categoriesCache
    .map((category) => `<option value="${category.id}" ${category.id === expense.category_id ? "selected" : ""}>${category.name}</option>`)
    .join("");
  return `<select data-expense-id="${expense.id}" class="expense-category-select"><option value="">Sem categoria</option>${options}</select>`;
}

async function loadCategorization() {
  await loadCategories();
  const expenses = await api("/expenses");
  expensesTable.innerHTML = expenses.length
    ? expenses
        .map(
          (expense) => `<tr><td>${expense.description}</td><td>${expense.due_date}</td><td>${currency(expense.amount)}</td><td>${categorySelect(expense)}</td></tr>`
        )
        .join("")
    : `<tr><td colspan="4">Sem gastos para categorizar.</td></tr>`;
}

showLoginBtn.addEventListener("click", () => setAuthMode("login"));
showRegisterBtn.addEventListener("click", () => setAuthMode("register"));

goLinkPageButton.addEventListener("click", () => showPage("link"));

menuButtons.forEach((btn) => {
  btn.addEventListener("click", async () => {
    showPage(btn.dataset.page);
    if (btn.dataset.page === "dashboard") await loadDashboard();
    if (btn.dataset.page === "categorization") await loadCategorization();
  });
});

logoutBtn.addEventListener("click", () => {
  token = null;
  localStorage.removeItem("token");
  authView.classList.remove("hidden");
  appView.classList.add("hidden");
  setAuthMode("login");
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("login-email").value,
        password: document.getElementById("login-password").value,
      }),
    });
    token = data.access_token;
    localStorage.setItem("token", token);
    authView.classList.add("hidden");
    appView.classList.remove("hidden");
    showPage("dashboard");
    await loadDashboard();
  } catch (error) {
    authMessage.textContent = error.message;
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("register-email").value,
        password: document.getElementById("register-password").value,
      }),
    });
    authMessage.textContent = result.message;
    setAuthMode("login");
  } catch (error) {
    authMessage.textContent = error.message;
  }
});

linkAccountButton.addEventListener("click", async () => {
  try {
    const result = await api("/nubank/link", { method: "POST", body: "{}" });
    linkMessage.textContent = result.message;
    await loadDashboard();
    await loadCategorization();
  } catch (error) {
    linkMessage.textContent = error.message;
  }
});

expensesTable.addEventListener("change", async (event) => {
  if (!event.target.classList.contains("expense-category-select")) return;
  const expenseId = event.target.dataset.expenseId;
  try {
    await api(`/expenses/${expenseId}/category`, {
      method: "PATCH",
      body: JSON.stringify({ category_id: event.target.value ? Number(event.target.value) : null }),
    });
  } catch (error) {
    alert(error.message);
  }
});

openCategoryModal.addEventListener("click", () => categoryModal.showModal());
cancelCategoryModal.addEventListener("click", () => categoryModal.close());

newCategoryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/categories", {
      method: "POST",
      body: JSON.stringify({ name: document.getElementById("new-category-name").value }),
    });
    document.getElementById("new-category-name").value = "";
    categoryModal.close();
    await loadCategorization();
  } catch (error) {
    alert(error.message);
  }
});

async function bootstrap() {
  if (!token) {
    authView.classList.remove("hidden");
    appView.classList.add("hidden");
    return;
  }
  try {
    await api("/me");
    authView.classList.add("hidden");
    appView.classList.remove("hidden");
    showPage("dashboard");
    await loadDashboard();
  } catch {
    token = null;
    localStorage.removeItem("token");
    authView.classList.remove("hidden");
    appView.classList.add("hidden");
  }
}

bootstrap();
