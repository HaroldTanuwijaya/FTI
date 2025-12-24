$(document).ready(function() {
    // Initialize dashboard
    loadDashboardData();
    loadCategories();
    
    // Modal controls
    $('#add-income-btn').click(() => openTransactionModal('income'));
    $('#add-expense-btn').click(() => openTransactionModal('expense'));
    $('#set-budget-btn').click(() => openBudgetModal());
    $('#export-data-btn').click(exportData);
    $('#generate-report-btn').click(generateMonthlyReport);
    $('#close-modal, #cancel-btn').click(() => closeTransactionModal());
    $('#close-budget-modal, #cancel-budget-btn').click(() => closeBudgetModal());
    
    // Form submissions
    $('#transaction-form').submit(handleTransactionSubmit);
    $('#budget-form').submit(handleBudgetSubmit);
    
    // Update FTI Score circle animation
    function updateFTIScore(score) {
        const circle = $('#score-circle');
        const scoreText = $('#fti-score');
        const circumference = 2 * Math.PI * 50;
        const offset = circumference - (score / 100) * circumference;
        
        circle.css('stroke-dashoffset', offset);
        scoreText.text(score);
        
        let status = 'At Risk';
        if (score >= 85) status = 'Excellent';
        else if (score >= 70) status = 'Healthy';
        else if (score >= 55) status = 'Needs Improvement';
        
        scoreText.next().text(status);
    }
    
    // Load dashboard data from API
    function loadDashboardData() {
        $.ajax({
            url: '/api/dashboard',
            method: 'GET',
            cache: true,  // Enable browser caching
            success: function(data) {
                updateFTIScore(data.fti_score || 0);
                $('#monthly-income').text('$' + (data.monthly_income || 0).toLocaleString());
                $('#monthly-expenses').text('$' + (data.monthly_expenses || 0).toLocaleString());
                $('#net-flow').text('$' + (data.net_flow || 0).toLocaleString());
                $('#budget-used').text((data.budget_used || 0) + '%');
                
                // Update monthly summary
                $('#total-transactions').text(data.total_transactions || 0);
                $('#avg-daily-spend').text('$' + (data.avg_daily_spend || 0).toLocaleString());
                $('#top-category').text(data.top_category || '-');
                $('#recurring-count').text(data.recurring_count || 0);
                
                loadRecentTransactions(data.recent_transactions || []);
            },
            error: function() {
                console.log('Failed to load dashboard data');
                updateFTIScore(0);
            }
        });
    }
    
    // Load categories
    function loadCategories() {
        // Check if categories are cached in localStorage
        const cachedCategories = localStorage.getItem('fti_categories');
        if (cachedCategories) {
            populateCategories(JSON.parse(cachedCategories));
            return;
        }
        
        $.ajax({
            url: '/api/categories',
            method: 'GET',
            success: function(data) {
                localStorage.setItem('fti_categories', JSON.stringify(data));
                populateCategories(data);
            }
        });
    }
    
    function populateCategories(data) {
        const categorySelect = $('#category');
        categorySelect.empty().append('<option value="">Select Category</option>');
        
        data.forEach(function(category) {
            categorySelect.append(`<option value="${category}">${category}</option>`);
        });
    }
    
    // Load recent transactions
    function loadRecentTransactions(transactions) {
        const container = $('#recent-transactions');
        
        if (transactions.length === 0) {
            container.html(`
                <div class="text-center text-gray-500 py-8">
                    <p>No transactions yet</p>
                    <button class="mt-2 bg-fti-blue text-white px-4 py-2 rounded-lg hover:bg-fti-blue-dark add-transaction-btn">
                        Add Transaction
                    </button>
                </div>
            `);
        } else {
            let html = '';
            transactions.forEach(function(transaction) {
                const isIncome = transaction.type === 'income';
                const amountClass = isIncome ? 'text-green-600' : 'text-red-600';
                const sign = isIncome ? '+' : '-';
                
                html += `
                    <div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                        <div>
                            <p class="font-medium text-gray-900">${transaction.description}</p>
                            <p class="text-sm text-gray-500">${transaction.category}</p>
                        </div>
                        <div class="text-right">
                            <p class="font-semibold ${amountClass}">${sign}$${transaction.amount.toLocaleString()}</p>
                            <p class="text-xs text-gray-500">${transaction.date}</p>
                        </div>
                    </div>
                `;
            });
            container.html(html);
        }
    }
    
    // Transaction Modal Functions
    function openTransactionModal(type) {
        $('#transaction-type').val(type);
        $('#modal-title').text(type === 'income' ? 'Add Income' : 'Add Expense');
        $('#transaction-modal').removeClass('hidden');
        $('#amount').focus();
    }
    
    function closeTransactionModal() {
        $('#transaction-modal').addClass('hidden');
        $('#transaction-form')[0].reset();
    }
    
    function handleTransactionSubmit(e) {
        e.preventDefault();
        
        const formData = {
            type: $('#transaction-type').val(),
            amount: parseFloat($('#amount').val()),
            description: $('#description').val(),
            category: $('#category').val() || 'Other'
        };
        
        $.ajax({
            url: '/api/transactions',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function() {
                closeTransactionModal();
                loadDashboardData();
                // Show success message if auto-categorized
                if (!$('#category').val() || $('#category').val() === 'Other') {
                    console.log('Transaction auto-categorized');
                }
            },
            error: function() {
                alert('Failed to add transaction');
            }
        });
    }
    
    // Budget Modal Functions
    function openBudgetModal() {
        $('#budget-modal').removeClass('hidden');
        $('#total-budget').focus();
    }
    
    function closeBudgetModal() {
        $('#budget-modal').addClass('hidden');
        $('#budget-form')[0].reset();
    }
    
    function handleBudgetSubmit(e) {
        e.preventDefault();
        
        const formData = {
            total_amount: parseFloat($('#total-budget').val()),
            month: new Date().toISOString().slice(0, 7) // YYYY-MM format
        };
        
        $.ajax({
            url: '/api/budget',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function() {
                closeBudgetModal();
                loadDashboardData();
            },
            error: function() {
                alert('Failed to save budget');
            }
        });
    }
    
    // Quick action handlers
    $(document).on('click', '.add-transaction-btn', function() {
        openTransactionModal('expense');
    });
    
    // Export Data Function
    function exportData() {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        // Create download link
        const link = document.createElement('a');
        link.href = '/api/export/csv';
        link.download = `fti_transactions_${new Date().toISOString().slice(0, 7)}.csv`;
        
        // Add authorization header via form submission
        const form = document.createElement('form');
        form.method = 'GET';
        form.action = '/api/export/csv';
        form.style.display = 'none';
        
        const tokenInput = document.createElement('input');
        tokenInput.type = 'hidden';
        tokenInput.name = 'token';
        tokenInput.value = token;
        form.appendChild(tokenInput);
        
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }
    
    // Generate Monthly Report
    function generateMonthlyReport() {
        $.ajax({
            url: '/api/reports/monthly',
            method: 'GET',
            success: function(data) {
                // Create and download PDF report
                const link = document.createElement('a');
                link.href = 'data:application/pdf;base64,' + data.pdf_data;
                link.download = `fti_monthly_report_${new Date().toISOString().slice(0, 7)}.pdf`;
                link.click();
            },
            error: function() {
                alert('Failed to generate report');
            }
        });
    }
    
    // Refresh data every 30 seconds
    let refreshInterval = setInterval(loadDashboardData, 30000);
    
    // Pause refresh when tab is not visible (performance optimization)
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            clearInterval(refreshInterval);
        } else {
            loadDashboardData();
            refreshInterval = setInterval(loadDashboardData, 30000);
        }
    });
});
