// Farm Expense Tracker - Main JavaScript
// State management
let currentUser = null;
let expenses = [];
let revenues = [];
let livestock = [];
let budget = {
  total: 0,
  remaining: 0
};

// API Client
let apiClient = null;

// DOM elements
const pages = {
  landing: document.getElementById('landing-page'),
  login: document.getElementById('login-page'),
  signup: document.getElementById('signup-page'),
  dashboard: document.getElementById('dashboard-page'),
  livestock: document.getElementById('livestock-page'),
  settings: document.getElementById('settings-page')
};

// Initialize app
document.addEventListener('DOMContentLoaded', async function() {
  apiClient = new FarmAPIClient();
  setupEventListeners();
  
  // Check if user is logged in via API
  try {
    const response = await farmAPI.getCurrentUser();
    if (response.success) {
      currentUser = response.user;
      await loadUserData();
      showPage('dashboard');
      document.getElementById('user-nav').style.display = 'flex';
      document.getElementById('auth-nav').style.display = 'none';
      document.getElementById('user-greeting').textContent = `Welcome, ${currentUser.username}`;
      updateUI();
    } else {
      showPage('landing');
    }
  } catch (error) {
    showPage('landing');
  }
});

// Load user data from API
async function loadUserData() {
  if (!currentUser) return;
  
  try {
    // Load expenses
    const expResponse = await farmAPI.getExpenses();
    if (expResponse.success) {
      expenses = expResponse.expenses || [];
    }
    
    // Load revenues
    const revResponse = await farmAPI.getRevenues();
    if (revResponse.success) {
      revenues = revResponse.revenues || [];
    }
    
    // Load livestock
    const liveResponse = await farmAPI.getLivestock();
    if (liveResponse.success) {
      livestock = liveResponse.livestock || [];
    }
    
    // Load budget
    const budgetResponse = await farmAPI.getBudget();
    if (budgetResponse.success && budgetResponse.budget) {
      budget = budgetResponse.budget;
    }
    
    updateUI();
  } catch (error) {
    console.error('Error loading data:', error);
    showNotification('Error loading data', 'error');
  }
}

// Event listeners setup
function setupEventListeners() {
  // Navigation
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', handleNavigation);
  });

  // Forgot password link
  document.getElementById('forgot-password-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    alert('Password reset feature coming soon!\n\nFor now, contact your administrator or create a new account.');
  });

  // Theme toggle
  document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

  // Auth forms
  document.getElementById('login-form').addEventListener('submit', handleLogin);
  document.getElementById('signup-form').addEventListener('submit', handleSignup);

  // Expense form
  document.getElementById('expense-form').addEventListener('submit', handleExpenseSubmit);

  // Revenue form
  document.getElementById('revenue-form').addEventListener('submit', handleRevenueSubmit);

  // Livestock form
  document.getElementById('livestock-form').addEventListener('submit', handleLivestockSubmit);

  // Budget settings
  document.getElementById('budget-form').addEventListener('submit', handleBudgetUpdate);

  // Settings
  document.getElementById('settings-form')?.addEventListener('submit', handleSettingsUpdate);

  // Logout
  document.getElementById('logout-btn').addEventListener('click', handleLogout);

  // Modal close
  document.querySelectorAll('.close-btn').forEach(btn => {
    btn.addEventListener('click', () => closeModal());
  });

  // Click outside modal
  document.getElementById('expense-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'expense-modal') closeModal('expense-modal');
  });

  document.getElementById('revenue-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'revenue-modal') closeModal('revenue-modal');
  });

  document.getElementById('livestock-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'livestock-modal') closeModal('livestock-modal');
  });

  document.getElementById('edit-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'edit-modal') closeModal('edit-modal');
  });

  document.getElementById('edit-revenue-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'edit-revenue-modal') closeModal('edit-revenue-modal');
  });

  document.getElementById('edit-livestock-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'edit-livestock-modal') closeModal('edit-livestock-modal');
  });

  // Edit form submissions
  document.getElementById('edit-expense-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    updateExpense();
  });

  document.getElementById('edit-revenue-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    updateRevenue();
  });

  document.getElementById('edit-livestock-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    updateLivestock();
  });

  // Modal triggers
  document.querySelectorAll('[data-modal]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modalId = e.target.closest('[data-modal]').dataset.modal;
      openModal(modalId);
    });
  });

  // Set default dates
  const today = new Date().toISOString().split('T')[0];
  if (document.getElementById('expense-date')) {
    document.getElementById('expense-date').value = today;
  }
  if (document.getElementById('revenue-date')) {
    document.getElementById('revenue-date').value = today;
  }
  if (document.getElementById('livestock-purchase-date')) {
    document.getElementById('livestock-purchase-date').value = today;
  }
  // Additional logout buttons
document.getElementById('logout-btn-livestock')?.addEventListener('click', handleLogout);
document.getElementById('logout-btn-settings')?.addEventListener('click', handleLogout);

// CTA buttons
document.querySelectorAll('.cta-btn').forEach(btn => {
  btn.addEventListener('click', handleNavigation);
});
}

// Navigation
function handleNavigation(e) {
  const target = e.target.dataset.page;
  if (target) {
    showPage(target);
  }
}

function showPage(pageName) {
  // Hide all pages
  Object.values(pages).forEach(page => {
    if (page) page.classList.remove('active');
  });

  // Show target page
  if (pages[pageName]) {
    pages[pageName].classList.add('active');
  }

  // Update navigation active state
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelector(`[data-page="${pageName}"]`)?.classList.add('active');
}

// Theme toggle
function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

  html.setAttribute('data-theme', newTheme);

  // Update theme toggle icon
  const icon = document.querySelector('#theme-toggle i');
  if (icon) {
    icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
  }
}

// Authentication
async function handleLogin(e) {
  e.preventDefault();

  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;

  if (!email || !password) {
    showNotification('Please fill in all fields', 'error');
    return;
  }

  try {
    // Use email as username (backend expects username)
    const response = await farmAPI.login(email, password);
    
    if (response.success) {
      showNotification('Login successful!', 'success');
      currentUser = response.user;
      
      // Load user data from backend
      await loadUserData();
      
      // Show dashboard
      showPage('dashboard');
      document.getElementById('user-nav').style.display = 'flex';
      document.getElementById('auth-nav').style.display = 'none';
      document.getElementById('user-greeting').textContent = `Welcome, ${currentUser.username}`;
      
      // Clear form
      e.target.reset();
    }
  } catch (error) {
    showNotification('Login failed: ' + error.message, 'error');
  }
}

async function handleSignup(e) {
  e.preventDefault();

  const name = document.getElementById('signup-name').value;
  const email = document.getElementById('signup-email').value;
  const farmName = document.getElementById('signup-farm')?.value || 'My Farm';
  const password = document.getElementById('signup-password').value;

  if (!name || !email || !password) {
    showNotification('Please fill in all fields', 'error');
    return;
  }

  if (password.length < 6) {
    showNotification('Password must be at least 6 characters', 'error');
    return;
  }

  try {
    // Register with backend API
    const response = await farmAPI.register(name, email, password);
    
    if (response.success) {
      showNotification('Account created successfully!', 'success');
      currentUser = response.user;
      
      // Initialize empty data
      expenses = [];
      revenues = [];
      livestock = [];
      budget = { total: 0, remaining: 0 };
      
      // Show dashboard
      showPage('dashboard');
      document.getElementById('user-nav').style.display = 'flex';
      document.getElementById('auth-nav').style.display = 'none';
      document.getElementById('user-greeting').textContent = `Welcome, ${currentUser.username}`;
      
      updateUI();
      
      // Clear form
      e.target.reset();
    }
  } catch (error) {
    showNotification('Registration failed: ' + error.message, 'error');
  }
}

async function handleLogout() {
  try {
    await farmAPI.logout();
    
    currentUser = null;
    expenses = [];
    revenues = [];
    livestock = [];
    budget = { total: 0, remaining: 0 };
    
    showPage('landing');
    document.getElementById('user-nav').style.display = 'none';
    document.getElementById('auth-nav').style.display = 'flex';
    
    showNotification('Logged out successfully', 'success');
  } catch (error) {
    console.error('Logout error:', error);
    // Force logout even if API call fails
    currentUser = null;
    showPage('landing');
    document.getElementById('user-nav').style.display = 'none';
    document.getElementById('auth-nav').style.display = 'flex';
  }
}

// Expense management
async function handleExpenseSubmit(e) {
  e.preventDefault();

  const formData = new FormData(e.target);
  const expenseData = {
    category: formData.get('category'),
    amount: parseFloat(formData.get('amount')),
    date: formData.get('date'),
    description: formData.get('description') || ''
  };

  // Validation
  if (!expenseData.category || !expenseData.amount || !expenseData.date) {
    showNotification('Please fill in all required fields', 'error');
    return;
  }

  if (expenseData.amount <= 0) {
    showNotification('Amount must be greater than 0', 'error');
    return;
  }

  try {
    const response = await farmAPI.createExpense(expenseData);
    
    if (response.success) {
      showNotification('Expense added successfully!', 'success');
      
      // Reload all data from backend
      await loadUserData();
      
      // Reset form
      e.target.reset();
      document.getElementById('expense-date').value = new Date().toISOString().split('T')[0];
      
      // Close modal
      closeModal('expense-modal');
    }
  } catch (error) {
    showNotification('Failed to save expense: ' + error.message, 'error');
  }
}

// Revenue management
async function handleRevenueSubmit(e) {
  e.preventDefault();

  const formData = new FormData(e.target);
  const revenueData = {
    source: formData.get('category'), // Backend expects 'source'
    amount: parseFloat(formData.get('amount')),
    date: formData.get('date'),
    description: formData.get('description') || ''
  };

  // Validation
  if (!revenueData.source || !revenueData.amount || !revenueData.date) {
    showNotification('Please fill in all required fields', 'error');
    return;
  }

  if (revenueData.amount <= 0) {
    showNotification('Amount must be greater than 0', 'error');
    return;
  }

  try {
    const response = await farmAPI.createRevenue(revenueData);
    
    if (response.success) {
      showNotification('Revenue added successfully!', 'success');
      
      // Reload all data
      await loadUserData();
      
      // Reset form
      e.target.reset();
      document.getElementById('revenue-date').value = new Date().toISOString().split('T')[0];
      
      // Close modal
      closeModal('revenue-modal');
    }
  } catch (error) {
    showNotification('Failed to save revenue: ' + error.message, 'error');
  }
}

// Livestock management
async function handleLivestockSubmit(e) {
  e.preventDefault();

  const formData = new FormData(e.target);
  const livestockData = {
    type: formData.get('type'),
    breed: formData.get('breed') || '',
    quantity: parseInt(formData.get('quantity')),
    age_months: parseInt(formData.get('age')) || null,
    weight_kg: parseFloat(formData.get('weight')) || null,
    purchase_date: formData.get('purchase_date'),
    purchase_price: parseFloat(formData.get('purchase_price')),
    notes: formData.get('notes') || ''
  };

  // Validation
  if (!livestockData.type || !livestockData.quantity || !livestockData.purchase_date) {
    showNotification('Please fill in all required fields', 'error');
    return;
  }

  if (livestockData.quantity <= 0) {
    showNotification('Quantity must be greater than 0', 'error');
    return;
  }

  try {
    const response = await farmAPI.createLivestock(livestockData);
    
    if (response.success) {
      showNotification('Livestock added successfully!', 'success');
      
      // Reload all data
      await loadUserData();
      
      // Reset form
      e.target.reset();
      document.getElementById('livestock-purchase-date').value = new Date().toISOString().split('T')[0];
    }
  } catch (error) {
    showNotification('Failed to save livestock: ' + error.message, 'error');
  }
}

// Edit functions
function editExpense(id) {
  const expense = expenses.find(e => e.id === id);
  if (!expense) return;

  document.getElementById('edit-id').value = expense.id;
  document.getElementById('edit-category').value = expense.category;
  document.getElementById('edit-amount').value = expense.amount;
  document.getElementById('edit-date').value = expense.date;
  document.getElementById('edit-description').value = expense.description || '';

  document.getElementById('edit-modal').classList.add('show');
}

function editRevenue(id) {
  const revenue = revenues.find(r => r.id === id);
  if (!revenue) return;

  document.getElementById('edit-revenue-id').value = revenue.id;
  document.getElementById('edit-revenue-category').value = revenue.source;
  document.getElementById('edit-revenue-amount').value = revenue.amount;
  document.getElementById('edit-revenue-date').value = revenue.date;
  document.getElementById('edit-revenue-description').value = revenue.description || '';

  document.getElementById('edit-revenue-modal').classList.add('show');
}

function editLivestock(id) {
  const animal = livestock.find(l => l.id === id);
  if (!animal) return;

  document.getElementById('edit-livestock-id').value = animal.id;
  document.getElementById('edit-livestock-type').value = animal.type;
  document.getElementById('edit-livestock-breed').value = animal.breed || '';
  document.getElementById('edit-livestock-quantity').value = animal.quantity;
  document.getElementById('edit-livestock-age').value = animal.age_months || '';
  document.getElementById('edit-livestock-weight').value = animal.weight_kg || '';
  document.getElementById('edit-livestock-purchase-date').value = animal.purchase_date;
  document.getElementById('edit-livestock-purchase-price').value = animal.purchase_price;
  document.getElementById('edit-livestock-notes').value = animal.notes || '';

  document.getElementById('edit-livestock-modal').classList.add('show');
}

async function updateExpense() {
  const id = parseInt(document.getElementById('edit-id').value);
  const category = document.getElementById('edit-category').value;
  const amount = parseFloat(document.getElementById('edit-amount').value);
  const date = document.getElementById('edit-date').value;
  const description = document.getElementById('edit-description').value;

  if (!category || !amount || !date) {
    showNotification('Please fill in all required fields', 'error');
    return;
  }

  if (amount <= 0) {
    showNotification('Amount must be greater than 0', 'error');
    return;
  }

  try {
    const response = await farmAPI.updateExpense(id, { category, amount, date, description });
    if (response.success) {
      await loadUserData();
      closeModal();
      showNotification('Expense updated successfully!', 'success');
    }
  } catch (error) {
    showNotification('Failed to update expense: ' + error.message, 'error');
  }
}

async function updateRevenue() {
  const id = parseInt(document.getElementById('edit-revenue-id').value);
  const source = document.getElementById('edit-revenue-category').value;
  const amount = parseFloat(document.getElementById('edit-revenue-amount').value);
  const date = document.getElementById('edit-revenue-date').value;
  const description = document.getElementById('edit-revenue-description').value;

  if (!source || !amount || !date) {
    showNotification('Please fill in all required fields', 'error');
    return;
  }

  if (amount <= 0) {
    showNotification('Amount must be greater than 0', 'error');
    return;
  }

  try {
    const response = await farmAPI.updateRevenue(id, { source, amount, date, description });
    if (response.success) {
      await loadUserData();
      closeModal();
      showNotification('Revenue updated successfully!', 'success');
    }
  } catch (error) {
    showNotification('Failed to update revenue: ' + error.message, 'error');
  }
}

function updateLivestock() {
  // This would need an API endpoint that doesn't exist yet
  showNotification('Livestock update feature coming soon!', 'info');
  closeModal();
}

async function deleteExpense(id) {
  if (confirm('Are you sure you want to delete this expense?')) {
    try {
      const response = await farmAPI.deleteExpense(id);
      if (response.success) {
        await loadUserData();
        showNotification('Expense deleted successfully!', 'success');
      }
    } catch (error) {
      showNotification('Failed to delete expense: ' + error.message, 'error');
    }
  }
}

async function deleteRevenue(id) {
  if (confirm('Are you sure you want to delete this revenue?')) {
    try {
      const response = await farmAPI.deleteRevenue(id);
      if (response.success) {
        await loadUserData();
        showNotification('Revenue deleted successfully!', 'success');
      }
    } catch (error) {
      showNotification('Failed to delete revenue: ' + error.message, 'error');
    }
  }
}

function deleteLivestock(id) {
  // This would need an API endpoint
  showNotification('Livestock delete feature coming soon!', 'info');
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('show');
  }
}

function closeModal(modalId) {
  if (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('show');
    }
  } else {
    // Close all modals
    document.querySelectorAll('.modal').forEach(modal => {
      modal.classList.remove('show');
    });
  }
}

// Budget management
async function handleBudgetUpdate(e) {
  e.preventDefault();

  const totalBudget = parseFloat(document.getElementById('total-budget').value);

  if (!totalBudget || totalBudget <= 0) {
    showNotification('Please enter a valid budget amount', 'error');
    return;
  }

  try {
    const response = await farmAPI.createBudget({ total_budget: totalBudget, period: 'monthly' });
    if (response.success) {
      await loadUserData();
      showNotification('Budget updated successfully!', 'success');
    }
  } catch (error) {
    showNotification('Failed to update budget: ' + error.message, 'error');
  }
}

// Settings
function handleSettingsUpdate(e) {
  e.preventDefault();
  showNotification('Settings update feature coming soon!', 'info');
}

// UI updates
function updateUI() {
  if (currentUser) {
    // Update header
    const userGreeting = document.getElementById('user-greeting');
    if (userGreeting) {
      userGreeting.textContent = `Welcome, ${currentUser.username || currentUser.name}`;
    }

    // Update stats
    updateStats();

    // Update transactions table
    updateTransactionsTable();

    // Update livestock table
    updateLivestockTable();

    // Update charts
    updateCharts();
  }

  // Update navigation visibility
  updateNavigation();
}

function updateNavigation() {
  const authNav = document.getElementById('auth-nav');
  const userNav = document.getElementById('user-nav');

  if (currentUser) {
    if (authNav) authNav.style.display = 'none';
    if (userNav) userNav.style.display = 'flex';
  } else {
    if (authNav) authNav.style.display = 'flex';
    if (userNav) userNav.style.display = 'none';
  }
}

function updateStats() {
  const totalExpenses = expenses.reduce((sum, expense) => sum + (parseFloat(expense.amount) || 0), 0);
  const totalRevenues = revenues.reduce((sum, revenue) => sum + (parseFloat(revenue.amount) || 0), 0);
  const monthlyExpenses = getMonthlyExpenses();
  const profitLoss = totalRevenues - totalExpenses;
  const totalLivestockHeads = livestock.reduce((sum, animal) => sum + (parseInt(animal.quantity) || 0), 0);
  const costPerHead = totalLivestockHeads > 0 ? totalExpenses / totalLivestockHeads : 0;

  const budgetTotal = budget.total_budget || 0;
  const budgetRemaining = budgetTotal - totalExpenses;

  // Update stat elements if they exist
  if (document.getElementById('total-budget-stat')) {
    document.getElementById('total-budget-stat').textContent = `$${budgetTotal.toLocaleString()}`;
  }
  if (document.getElementById('used-budget-stat')) {
    document.getElementById('used-budget-stat').textContent = `$${totalExpenses.toLocaleString()}`;
  }
  if (document.getElementById('remaining-budget-stat')) {
    document.getElementById('remaining-budget-stat').textContent = `$${budgetRemaining.toLocaleString()}`;
  }
  if (document.getElementById('monthly-expenses-stat')) {
    document.getElementById('monthly-expenses-stat').textContent = `$${monthlyExpenses.toLocaleString()}`;
  }
  if (document.getElementById('net-margin-stat')) {
    document.getElementById('net-margin-stat').textContent = `${profitLoss >= 0 ? '+' : ''}$${profitLoss.toLocaleString()}`;
  }
  if (document.getElementById('cost-per-head-stat')) {
    document.getElementById('cost-per-head-stat').textContent = `$${costPerHead.toFixed(2)}`;
  }
}

function getMonthlyExpenses() {
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();

  return expenses
    .filter(expense => {
      const expenseDate = new Date(expense.date);
      return expenseDate.getMonth() === currentMonth && expenseDate.getFullYear() === currentYear;
    })
    .reduce((sum, expense) => sum + (parseFloat(expense.amount) || 0), 0);
}

function updateTransactionsTable() {
  const tbody = document.querySelector('.expenses-table tbody');
  if (!tbody) return;

  tbody.innerHTML = '';

  // Combine expenses and revenues
  const allTransactions = [
    ...expenses.map(e => ({ ...e, type: 'expense', category: e.category })),
    ...revenues.map(r => ({ ...r, type: 'revenue', category: r.source }))
  ];

  // Sort by date (newest first)
  const sortedTransactions = allTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));

  sortedTransactions.slice(0, 10).forEach(transaction => {
    const row = document.createElement('tr');

    const date = new Date(transaction.date).toLocaleDateString();
    const amount = Math.abs(parseFloat(transaction.amount) || 0).toLocaleString();
    const amountClass = transaction.type === 'revenue' ? 'positive' : 'negative';
    const amountPrefix = transaction.type === 'revenue' ? '+' : '-';

    row.innerHTML = `
      <td>${date}</td>
      <td>${transaction.category || 'N/A'}</td>
      <td class="amount-cell ${amountClass}">${amountPrefix}$${amount}</td>
      <td>${transaction.description || '-'}</td>
      <td>
        <button class="action-btn" onclick="edit${transaction.type.charAt(0).toUpperCase() + transaction.type.slice(1)}(${transaction.id})">
          <i class="fas fa-edit"></i>
        </button>
        <button class="action-btn" onclick="delete${transaction.type.charAt(0).toUpperCase() + transaction.type.slice(1)}(${transaction.id})">
          <i class="fas fa-trash"></i>
        </button>
      </td>
    `;

    tbody.appendChild(row);
  });
}

function updateLivestockTable() {
  const tbody = document.querySelector('.livestock-table tbody');
  if (!tbody) return;

  tbody.innerHTML = '';

  livestock.forEach(animal => {
    const row = document.createElement('tr');

    const purchaseDate = animal.purchase_date ? new Date(animal.purchase_date).toLocaleDateString() : 'N/A';
    const purchasePrice = parseFloat(animal.purchase_price) || 0;
    const quantity = parseInt(animal.quantity) || 0;
    const totalValue = (purchasePrice * quantity).toLocaleString();

    row.innerHTML = `
      <td>${animal.type || 'N/A'}</td>
      <td>${animal.breed || '-'}</td>
      <td>${quantity}</td>
      <td>${animal.age_months || '-'} months</td>
      <td>${animal.weight_kg || '-'} kg</td>
      <td>${purchaseDate}</td>
      <td>$${purchasePrice.toLocaleString()}</td>
      <td>$${totalValue}</td>
      <td>
        <button class="action-btn" onclick="editLivestock(${animal.id})">
          <i class="fas fa-edit"></i>
        </button>
        <button class="action-btn" onclick="deleteLivestock(${animal.id})">
          <i class="fas fa-trash"></i>
        </button>
      </td>
    `;

    tbody.appendChild(row);
  });
}

function updateCharts() {
  updateExpenseChart();
  updateCategoryChart();
}

function updateExpenseChart() {
  const ctx = document.getElementById('expense-chart');
  if (!ctx) return;

  // Group expenses by month
  const monthlyData = {};
  expenses.forEach(expense => {
    const date = new Date(expense.date);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    monthlyData[key] = (monthlyData[key] || 0) + (parseFloat(expense.amount) || 0);
  });

  const labels = Object.keys(monthlyData).sort();
  const data = labels.map(label => monthlyData[label]);

  if (window.expenseChart) {
    window.expenseChart.destroy();
  }

  window.expenseChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Monthly Expenses',
        data: data,
        borderColor: '#f44336',
        backgroundColor: 'rgba(244, 67, 54, 0.1)',
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return '$' + value.toLocaleString();
            }
          }
        }
      }
    }
  });
}

function updateCategoryChart() {
  const ctx = document.getElementById('category-chart');
  if (!ctx) return;

  // Group expenses by category
  const categoryData = {};
  expenses.forEach(expense => {
    const cat = expense.category || 'Other';
    categoryData[cat] = (categoryData[cat] || 0) + (parseFloat(expense.amount) || 0);
  });

  const labels = Object.keys(categoryData);
  const data = Object.values(categoryData);

  if (window.categoryChart) {
    window.categoryChart.destroy();
  }

  window.categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: [
          '#f44336',
          '#fb8c00',
          '#ffb74d',
          '#ff9800',
          '#e65100',
          '#bf360c'
        ]
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom'
        }
      }
    }
  });
}

// Notifications
function showNotification(message, type = 'success') {
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;

  const container = document.getElementById('notification-container') || document.body;
  container.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 3000);
}

// Export CSV
function exportCSV() {
  showNotification('Export feature coming soon!', 'info');
}