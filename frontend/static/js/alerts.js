$(document).ready(function() {
    // Check authentication
    const token = localStorage.getItem('fti_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    // Setup AJAX defaults with token
    $.ajaxSetup({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('Authorization', 'Bearer ' + token);
        },
        error: function(xhr) {
            if (xhr.status === 401) {
                localStorage.removeItem('fti_token');
                window.location.href = '/login';
            }
        }
    });
    
    loadAlerts();
    loadAlertSettings();
    
    // Toggle handlers
    $('#budget-alert, #large-transaction-alert, #goal-alert, #recurring-alert').change(function() {
        saveAlertSettings();
    });
    
    function loadAlerts() {
        $.ajax({
            url: '/api/alerts',
            method: 'GET',
            success: function(data) {
                renderAlerts(data.alerts || []);
            },
            error: function() {
                console.log('Failed to load alerts');
            }
        });
    }
    
    function renderAlerts(alerts) {
        const container = $('#alerts-container');
        
        if (alerts.length === 0) {
            container.html(`
                <div class="text-center py-8 text-gray-500">
                    <p>No alerts yet</p>
                </div>
            `);
            return;
        }
        
        let html = '';
        alerts.forEach(function(alert) {
            let iconColor = 'text-fti-blue';
            let bgColor = 'bg-blue-50';
            
            if (alert.type === 'warning') {
                iconColor = 'text-yellow-600';
                bgColor = 'bg-yellow-50';
            } else if (alert.type === 'danger') {
                iconColor = 'text-red-600';
                bgColor = 'bg-red-50';
            } else if (alert.type === 'success') {
                iconColor = 'text-green-600';
                bgColor = 'bg-green-50';
            }
            
            html += `
                <div class="flex items-start p-4 ${bgColor} rounded-lg">
                    <div class="flex-shrink-0">
                        <svg class="w-6 h-6 ${iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                    <div class="ml-3 flex-1">
                        <p class="font-medium text-gray-900">${alert.title}</p>
                        <p class="text-sm text-gray-600 mt-1">${alert.message}</p>
                        <p class="text-xs text-gray-500 mt-2">${new Date(alert.created_at).toLocaleString()}</p>
                    </div>
                </div>
            `;
        });
        
        container.html(html);
    }
    
    function loadAlertSettings() {
        $.ajax({
            url: '/api/alerts/settings',
            method: 'GET',
            success: function(data) {
                $('#budget-alert').prop('checked', data.budget_alert !== false);
                $('#large-transaction-alert').prop('checked', data.large_transaction_alert !== false);
                $('#goal-alert').prop('checked', data.goal_alert !== false);
                $('#recurring-alert').prop('checked', data.recurring_alert !== false);
            }
        });
    }
    
    function saveAlertSettings() {
        const settings = {
            budget_alert: $('#budget-alert').is(':checked'),
            large_transaction_alert: $('#large-transaction-alert').is(':checked'),
            goal_alert: $('#goal-alert').is(':checked'),
            recurring_alert: $('#recurring-alert').is(':checked')
        };
        
        $.ajax({
            url: '/api/alerts/settings',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(settings),
            success: function() {
                console.log('Alert settings saved');
            }
        });
    }
});
