$(document).ready(function() {
    loadGoals();
    
    $('#add-goal-btn').click(openGoalModal);
    $('#close-goal-modal, #cancel-goal-btn').click(closeGoalModal);
    $('#goal-form').submit(handleGoalSubmit);
    
    function loadGoals() {
        $.ajax({
            url: '/api/goals',
            method: 'GET',
            success: function(data) {
                renderGoals(data.goals || []);
            },
            error: function() {
                console.log('Failed to load goals');
            }
        });
    }
    
    function renderGoals(goals) {
        const container = $('#goals-container');
        
        if (goals.length === 0) {
            container.html(`
                <div class="col-span-full text-center py-12 text-gray-500">
                    <p class="mb-4">No goals yet. Start by adding your first financial goal!</p>
                </div>
            `);
            return;
        }
        
        let html = '';
        goals.forEach(function(goal) {
            const progress = (goal.current_amount / goal.target_amount) * 100;
            const progressClamped = Math.min(progress, 100);
            const daysLeft = Math.ceil((new Date(goal.target_date) - new Date()) / (1000 * 60 * 60 * 24));
            
            let statusColor = 'text-fti-blue';
            let statusText = 'On Track';
            if (progressClamped >= 100) {
                statusColor = 'text-green-600';
                statusText = 'Completed';
            } else if (daysLeft < 0) {
                statusColor = 'text-red-600';
                statusText = 'Overdue';
            }
            
            html += `
                <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">${goal.name}</h3>
                        <button class="delete-goal text-gray-400 hover:text-red-600" data-id="${goal._id}">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                    
                    <div class="mb-4">
                        <div class="flex justify-between text-sm mb-2">
                            <span class="text-gray-600">Progress</span>
                            <span class="font-semibold ${statusColor}">${progressClamped.toFixed(0)}%</span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2">
                            <div class="bg-fti-blue h-2 rounded-full" style="width: ${progressClamped}%"></div>
                        </div>
                    </div>
                    
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-gray-600">Current</span>
                            <span class="font-semibold">$${goal.current_amount.toLocaleString()}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Target</span>
                            <span class="font-semibold">$${goal.target_amount.toLocaleString()}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Remaining</span>
                            <span class="font-semibold">$${Math.max(0, goal.target_amount - goal.current_amount).toLocaleString()}</span>
                        </div>
                        <div class="flex justify-between pt-2 border-t">
                            <span class="text-gray-600">Status</span>
                            <span class="font-semibold ${statusColor}">${statusText}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Target Date</span>
                            <span class="font-semibold">${new Date(goal.target_date).toLocaleDateString()}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.html(html);
        
        $('.delete-goal').click(function() {
            const goalId = $(this).data('id');
            if (confirm('Are you sure you want to delete this goal?')) {
                deleteGoal(goalId);
            }
        });
    }
    
    function openGoalModal() {
        $('#goal-modal').removeClass('hidden');
        $('#goal-name').focus();
    }
    
    function closeGoalModal() {
        $('#goal-modal').addClass('hidden');
        $('#goal-form')[0].reset();
        $('#goal-id').val('');
    }
    
    function handleGoalSubmit(e) {
        e.preventDefault();
        
        const formData = {
            name: $('#goal-name').val(),
            target_amount: parseFloat($('#goal-amount').val()),
            current_amount: parseFloat($('#goal-current').val()),
            target_date: $('#goal-date').val()
        };
        
        $.ajax({
            url: '/api/goals',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function() {
                closeGoalModal();
                loadGoals();
            },
            error: function() {
                alert('Failed to save goal');
            }
        });
    }
    
    function deleteGoal(goalId) {
        $.ajax({
            url: '/api/goals/' + goalId,
            method: 'DELETE',
            success: function() {
                loadGoals();
            },
            error: function() {
                alert('Failed to delete goal');
            }
        });
    }
});
