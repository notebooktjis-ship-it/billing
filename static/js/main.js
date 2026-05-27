document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initAlerts();
    initDropdowns();
    initSearch();
    initRoomCards();
    initForms();
    initModals();
});

function initSidebar() {
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
        
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }
}

function initAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
}

function initDropdowns() {
    const dropdowns = document.querySelectorAll('.user-dropdown');
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
            const menu = dropdown.querySelector('.dropdown-menu');
            if (menu) {
                menu.classList.toggle('show');
            }
        });
    });
    
    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    });
}

function initSearch() {
    const searchInputs = document.querySelectorAll('.search-input input[type="text"]');
    searchInputs.forEach(searchInput => {
        let timeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const form = searchInput.closest('form');
                if (form) {
                    form.submit();
                }
            }, 500);
        });
    });
}

function initRoomCards() {
    const roomCards = document.querySelectorAll('.room-card[data-room-id]');
    roomCards.forEach(card => {
        card.addEventListener('click', () => {
            const roomId = card.dataset.roomId;
            window.location.href = `/rooms/${roomId}`;
        });
    });
}

function initForms() {
    const forms = document.querySelectorAll('form[data-ajax]');
    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
    });
    
    const deleteForms = document.querySelectorAll('form[data-delete]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading">Processing...</span>';
    
    try {
        const response = await fetch(form.action, {
            method: form.method,
            body: new FormData(form)
        });
        
        if (response.redirected) {
            window.location.href = response.url;
        } else if (response.ok) {
            location.reload();
        } else {
            throw new Error('Request failed');
        }
    } catch (error) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
        showToast('An error occurred. Please try again.', 'error');
    }
}

function initModals() {
    const modalTriggers = document.querySelectorAll('[data-modal]');
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', () => {
            const modalId = trigger.dataset.modal;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('active');
            }
        });
    });
    
    const modalCloses = document.querySelectorAll('.modal-close, .modal-overlay');
    modalCloses.forEach(el => {
        el.addEventListener('click', (e) => {
            if (e.target === el) {
                el.closest('.modal-overlay').classList.remove('active');
            }
        });
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}-circle"></i> ${message}`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

function updateRoomStatus(roomId, status) {
    fetch(`/rooms/${roomId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            showToast(data.error || 'Failed to update room status', 'error');
        }
    })
    .catch(error => {
        showToast('An error occurred', 'error');
    });
}

function cancelBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking?')) return;
    
    fetch(`/bookings/${bookingId}/cancel`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Booking cancelled successfully', 'success');
            location.reload();
        } else {
            showToast(data.error || 'Failed to cancel booking', 'error');
        }
    });
}

function deleteCharge(chargeId) {
    if (!confirm('Delete this charge?')) return;
    
    fetch(`/api/charges/${chargeId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}

function toggleStaff(staffId) {
    fetch(`/staff/${staffId}/toggle`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(`Staff ${data.is_active ? 'activated' : 'deactivated'}`, 'success');
            location.reload();
        } else {
            showToast(data.error, 'error');
        }
    });
}

function searchCustomers(query) {
    if (query.length < 2) return;
    
    fetch(`/api/customers/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('customer-results');
            if (container) {
                container.innerHTML = data.map(c => `
                    <div class="customer-result" onclick="selectCustomer(${c.id})">
                        <strong>${c.name}</strong> - ${c.phone}
                        <span class="badge">${c.total_stays} stays</span>
                    </div>
                `).join('');
            }
        });
}

function selectCustomer(customerId) {
    const select = document.querySelector('select[name="customer_id"]');
    if (select) {
        select.value = customerId;
        document.getElementById('customer-results').innerHTML = '';
    }
}

function getAvailableRooms(checkIn, checkOut) {
    fetch(`/api/rooms/available?check_in=${checkIn}&check_out=${checkOut}`)
        .then(response => response.json())
        .then(data => {
            const select = document.querySelector('select[name="room_id"]');
            if (select) {
                select.innerHTML = data.map(r => 
                    `<option value="${r.id}">${r.room_number} - ${r.room_type} (Rs. ${r.price}/night)</option>`
                ).join('');
            }
        });
}

function calculateBill() {
    const checkIn = document.querySelector('[name="check_in"]')?.value;
    const checkOut = document.querySelector('[name="check_out"]')?.value;
    const roomSelect = document.querySelector('[name="room_id"]');
    
    if (checkIn && checkOut && roomSelect) {
        const checkInDate = new Date(checkIn);
        const checkOutDate = new Date(checkOut);
        const nights = Math.ceil((checkOutDate - checkInDate) / (1000 * 60 * 60 * 24));
        
        const selectedOption = roomSelect.options[roomSelect.selectedIndex];
        const priceText = selectedOption?.text || '';
        const price = parseFloat(priceText.match(/Rs\.\s*([\d,]+)/)?.[1]?.replace(',', '') || 0);
        
        const total = nights * price;
        
        const summary = document.getElementById('booking-summary');
        if (summary) {
            summary.innerHTML = `
                <div class="alert alert-info">
                    <strong>Nights:</strong> ${nights}<br>
                    <strong>Rate:</strong> Rs. ${price.toLocaleString()}/night<br>
                    <strong>Total Room Charge:</strong> Rs. ${total.toLocaleString()}
                </div>
            `;
        }
    }
}

document.addEventListener('change', (e) => {
    if (e.target.name === 'check_in' || e.target.name === 'check_out') {
        calculateBill();
    }
});

function updateClock() {
    const clock = document.getElementById('current-time');
    if (clock) {
        const now = new Date();
        clock.textContent = now.toLocaleString('en-IN', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

if (document.getElementById('current-time')) {
    updateClock();
    setInterval(updateClock, 1000);
}

function exportReport(type) {
    const now = new Date();
    const month = now.getMonth() + 1;
    const year = now.getFullYear();
    window.location.href = `/api/reports/export?type=${type}&month=${month}&year=${year}`;
}

function printInvoice() {
    window.print();
}
