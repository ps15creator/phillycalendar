// Philadelphia Events Calendar - JavaScript

const API_BASE = '';  // Same origin
let allEvents = [];
let filteredEvents = [];
let currentCategory = 'all';
let currentMonth = 'all';
let currentSource = 'all';
let bookmarkedIds = new Set(); // Track bookmarked event IDs

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadEvents();
    loadBookmarks();
    checkForUpdates();
});

// (No resize re-render needed — unified day-grouped view works at all sizes)

// Setup event listeners
function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('input', handleSearch);
    document.getElementById('refreshBtn').addEventListener('click', refreshEvents);
    document.getElementById('addEventBtn').addEventListener('click', openAddEventModal);
    document.getElementById('bookmarksBtn').addEventListener('click', showBookmarks);
    document.getElementById('monthSelect').addEventListener('change', handleMonthFilter);
    document.getElementById('sourceSelect').addEventListener('change', handleSourceFilter);

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => handleFilter(e.target.dataset.category));
    });

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    document.getElementById('closeAddEventModal').addEventListener('click', closeAddEventModal);
    document.getElementById('cancelEventForm').addEventListener('click', closeAddEventModal);
    document.getElementById('eventForm').addEventListener('submit', handleEventFormSubmit);

    window.addEventListener('click', (e) => {
        if (e.target.id === 'eventModal') closeModal();
        if (e.target.id === 'addEventModal') closeAddEventModal();
    });
}

// Load events from API
async function loadEvents() {
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/events/upcoming`);
        const data = await response.json();

        if (data.success) {
            allEvents = data.events;
            filteredEvents = allEvents;
            populateMonthFilter();
            populateSourceFilter();
            renderEvents();
            updateStats();
        }
    } catch (error) {
        console.error('Error loading events:', error);
        showEmptyState();
    } finally {
        showLoading(false);
    }
}

// Refresh events
async function refreshEvents() {
    await loadEvents();
    showNotification('Events refreshed!');
}

// Scrape new events
async function scrapeNewEvents() {
    const btn = document.getElementById('scrapeBtn');
    btn.disabled = true;
    btn.textContent = '🤖 Scraping...';

    try {
        const response = await fetch(`${API_BASE}/scrape`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            showNotification(`✅ Scraped ${data.total_added} new events!`);
            await loadEvents();
        }
    } catch (error) {
        console.error('Error scraping:', error);
        showNotification('❌ Scraping failed', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🤖 Scrape New Events';
    }
}

// Handle category filter
function handleFilter(category) {
    currentCategory = category;

    // Update button states
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.category === category) {
            btn.classList.add('active');
        }
    });

    applyFilters();
}

// Handle month filter
function handleMonthFilter(e) {
    currentMonth = e.target.value;
    applyFilters();
}

// Handle source filter
function handleSourceFilter(e) {
    currentSource = e.target.value;
    applyFilters();
}

// Apply all filters
function applyFilters() {
    filteredEvents = allEvents.filter(event => {
        const matchesCategory = currentCategory === 'all' || event.category === currentCategory;

        let matchesMonth = true;
        if (currentMonth !== 'all') {
            const eventDate = parseLocalDate(event.start_date);
            const eventMonthYear = `${eventDate.getFullYear()}-${String(eventDate.getMonth() + 1).padStart(2, '0')}`;
            matchesMonth = eventMonthYear === currentMonth;
        }

        const matchesSource = currentSource === 'all' || event.source === currentSource;

        return matchesCategory && matchesMonth && matchesSource;
    });

    renderEvents();
}

// Populate month filter dropdown
function populateMonthFilter() {
    const monthSelect = document.getElementById('monthSelect');
    const months = new Set();

    allEvents.forEach(event => {
        const date = parseLocalDate(event.start_date);
        const monthYear = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        months.add(monthYear);
    });

    const sortedMonths = Array.from(months).sort();

    // Clear existing options except "All Months"
    monthSelect.innerHTML = '<option value="all">All Months</option>';

    // Add month options
    sortedMonths.forEach(monthYear => {
        const [year, month] = monthYear.split('-');
        const date = new Date(year, parseInt(month) - 1, 1);
        const monthName = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

        const option = document.createElement('option');
        option.value = monthYear;
        option.textContent = monthName;
        monthSelect.appendChild(option);
    });
}

// Populate source filter dropdown
function populateSourceFilter() {
    const sourceSelect = document.getElementById('sourceSelect');
    const sources = new Set();

    allEvents.forEach(event => {
        sources.add(event.source);
    });

    const sortedSources = Array.from(sources).sort();

    // Clear existing options except "All Sources"
    sourceSelect.innerHTML = '<option value="all">All Sources</option>';

    // Add source options
    sortedSources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        sourceSelect.appendChild(option);
    });
}

// Handle search
function handleSearch(e) {
    const query = e.target.value.toLowerCase();

    filteredEvents = allEvents.filter(event => {
        const matchesCategory = currentCategory === 'all' || event.category === currentCategory;

        let matchesMonth = true;
        if (currentMonth !== 'all') {
            const eventDate = parseLocalDate(event.start_date);
            const eventMonthYear = `${eventDate.getFullYear()}-${String(eventDate.getMonth() + 1).padStart(2, '0')}`;
            matchesMonth = eventMonthYear === currentMonth;
        }

        const matchesSource = currentSource === 'all' || event.source === currentSource;

        const matchesSearch = query === '' || (
            event.title.toLowerCase().includes(query) ||
            event.description.toLowerCase().includes(query) ||
            event.location.toLowerCase().includes(query)
        );

        return matchesCategory && matchesMonth && matchesSource && matchesSearch;
    });

    renderEvents();
}

// Render events to DOM — unified day-grouped view for all screen sizes
function renderEvents() {
    const container = document.getElementById('eventsContainer');
    const emptyState = document.getElementById('emptyState');

    if (filteredEvents.length === 0) {
        container.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';
    container.innerHTML = renderGroupedByDay();

    // Attach click listeners to all event rows
    document.querySelectorAll('.event-row').forEach(row => {
        row.addEventListener('click', () => {
            const idx = parseInt(row.dataset.eventIndex);
            if (!isNaN(idx) && filteredEvents[idx]) showEventDetail(filteredEvents[idx]);
        });
    });
}

// Group events by calendar day and render as a clean list
function renderGroupedByDay() {
    // Build a map: "YYYY-MM-DD" → [{event, index}, ...]
    const byDay = {};
    const dayOrder = [];

    filteredEvents.forEach((event, index) => {
        const d = parseLocalDate(event.start_date);
        const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        if (!byDay[key]) {
            byDay[key] = [];
            dayOrder.push(key);
        }
        byDay[key].push({ event, index });
    });

    dayOrder.sort();

    return dayOrder.map(key => {
        const [year, month, day] = key.split('-').map(Number);
        const d = new Date(year, month - 1, day);
        const weekday = d.toLocaleDateString('en-US', { weekday: 'long' });
        const dateStr = d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        const items = byDay[key];
        const isToday = key === todayKey();

        return `
        <div class="day-group">
            <div class="day-header">
                <div class="day-header-left">
                    <span class="day-weekday">${isToday ? '📍 Today' : weekday}</span>
                    <span class="day-date">${dateStr}</span>
                </div>
                <span class="day-count">${items.length} event${items.length !== 1 ? 's' : ''}</span>
            </div>
            ${items.map(({ event, index }) => createEventRow(event, index)).join('')}
        </div>`;
    }).join('');
}

function todayKey() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
}

// Create a single event row within a day group
function createEventRow(event, index) {
    const startDate = parseLocalDate(event.start_date);
    const hasTime = startDate.getHours() !== 0 || startDate.getMinutes() !== 0;
    const timeStr = hasTime
        ? startDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
        : '';
    const categoryClass = `category-${event.category}`;
    const categoryName = getCategoryName(event.category);
    const location = event.location || '';
    const price = event.price || '';

    return `
    <div class="event-row" data-event-index="${index}">
        <div class="event-time-col">
            ${hasTime
                ? `<span class="event-time">${timeStr}</span>`
                : `<span class="event-time-tbd">TBD</span>`}
        </div>
        <div class="event-row-divider"></div>
        <div class="event-details-col">
            <div class="event-row-top">
                <span class="event-row-title">${event.title}</span>
                <span class="event-category ${categoryClass}">${categoryName}</span>
            </div>
            <div class="event-row-meta">
                ${location ? `<span class="event-row-location">📍 ${location}</span>` : ''}
                ${price ? `<span class="event-row-price">💰 ${price}</span>` : ''}
            </div>
        </div>
        <span class="chevron">›</span>
    </div>`;
}

// Show event detail modal
function showEventDetail(event) {
    const modal = document.getElementById('eventModal');
    const modalBody = document.getElementById('modalBody');
    const startDate = parseLocalDate(event.start_date);
    const categoryName = getCategoryName(event.category);

    const isBookmarked = bookmarkedIds.has(event.id);

    modalBody.innerHTML = `
        <h2 class="modal-title">${event.title}</h2>

        <div class="modal-detail">
            <strong>📅 Date & Time</strong><br>
            ${formatDateLong(startDate)}
        </div>

        <div class="modal-detail">
            <strong>📍 Location</strong><br>
            ${event.location}
            ${event.source_url ? `<br><a href="${event.source_url}" target="_blank">🔗 View Event Website</a>` : ''}
        </div>

        <div class="modal-detail">
            <strong>🎯 Category</strong><br>
            ${categoryName}
        </div>

        ${event.price ? `
        <div class="modal-detail">
            <strong>💰 Price</strong><br>
            ${event.price}
        </div>
        ` : ''}

        ${event.registration_deadline ? `
        <div class="modal-detail">
            <strong>⏰ Registration Deadline</strong><br>
            ${parseLocalDate(event.registration_deadline).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
        ` : ''}

        ${event.description ? `
        <div class="modal-detail">
            <strong>📝 Description</strong><br>
            ${event.description}
        </div>
        ` : ''}

        <div class="modal-detail">
            <strong>ℹ️ Source</strong><br>
            ${event.source || 'Unknown'}
        </div>

        <div class="event-detail-actions">
            <button class="btn ${isBookmarked ? 'btn-warning' : 'btn-success'}" onclick="toggleBookmark(${event.id})">
                ${isBookmarked ? '⭐ Bookmarked' : '☆ Bookmark'}
            </button>
            <button class="btn btn-primary" onclick="openEditEventModal(${event.id})">
                ✏️ Edit
            </button>
            <button class="btn btn-danger" onclick="deleteEvent(${event.id})">
                🗑️ Delete
            </button>
        </div>
    `;

    modal.style.display = 'block';
}

// Close modal
function closeModal() {
    document.getElementById('eventModal').style.display = 'none';
}

// Update stats
async function updateStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        if (data.success) {
            document.getElementById('totalEvents').textContent = data.stats.total_events;
            document.getElementById('upcomingEvents').textContent = data.stats.upcoming_events;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }

    document.getElementById('lastSync').textContent = new Date().toLocaleTimeString();
}

// Check for updates periodically
function checkForUpdates() {
    setInterval(async () => {
        await loadEvents();
    }, 5 * 60 * 1000); // Check every 5 minutes
}

// Show/hide loading
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

// Show empty state
function showEmptyState() {
    document.getElementById('eventsContainer').innerHTML = '';
    document.getElementById('emptyState').style.display = 'block';
}

// Show notification
function showNotification(message, type = 'success') {
    // Simple alert for now - could be enhanced with toast notifications
    alert(message);
}

// Parse a date string from the server as LOCAL time (not UTC)
// Server stores Eastern time without timezone suffix, so we must not let
// JavaScript treat it as UTC (which would subtract 5 hours)
// Handles both ISO format ("2026-02-18T19:30:00") and
// RFC 2822 format ("Wed, 18 Feb 2026 19:30:00 GMT") returned by Flask
function parseLocalDate(dateStr) {
    if (!dateStr) return new Date();

    // Detect RFC 2822 format: "Wed, 18 Feb 2026 19:30:00 GMT"
    // Flask's jsonify serializes Python datetimes in this format
    const rfc2822 = /^[A-Za-z]{3},\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s+GMT$/;
    const m = dateStr.match(rfc2822);
    if (m) {
        const months = { Jan:0, Feb:1, Mar:2, Apr:3, May:4, Jun:5,
                         Jul:6, Aug:7, Sep:8, Oct:9, Nov:10, Dec:11 };
        const day   = parseInt(m[1], 10);
        const month = months[m[2]];
        const year  = parseInt(m[3], 10);
        const hour  = parseInt(m[4], 10);
        const min   = parseInt(m[5], 10);
        const sec   = parseInt(m[6], 10);
        // Construct as local time (ignoring GMT suffix — server stores Eastern time)
        return new Date(year, month, day, hour, min, sec);
    }

    // ISO format: "2026-02-18T19:30:00" or "2026-02-18 19:30:00"
    // Replace space separator with T, strip timezone suffix if any
    const clean = dateStr.replace(' ', 'T').split('+')[0].replace('Z', '');
    const [datePart, timePart] = clean.split('T');
    if (!datePart) return new Date(dateStr);
    const [year, month, day] = datePart.split('-').map(Number);
    if (timePart) {
        const [hour, minute, second] = timePart.split(':').map(Number);
        return new Date(year, month - 1, day, hour || 0, minute || 0, second || 0);
    }
    return new Date(year, month - 1, day);
}

// Format date
function formatDate(date) {
    // Check if event has a specific time (not midnight)
    const hasTime = date.getHours() !== 0 || date.getMinutes() !== 0;

    if (hasTime) {
        return date.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    } else {
        // Date only, no specific time
        return date.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    }
}

function formatDateLong(date) {
    // Check if event has a specific time (not midnight)
    const hasTime = date.getHours() !== 0 || date.getMinutes() !== 0;

    if (hasTime) {
        return date.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    } else {
        // Date only, no specific time
        return date.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }) + ' (Time TBD)';
    }
}

// Get category display name
function getCategoryName(category) {
    const names = {
        'running': '🏃 Running',
        'artsAndCulture': '🎨 Arts & Culture',
        'music': '🎵 Music & Nightlife',
        'foodAndDrink': '🍽️ Food & Drink',
        'community': '👥 Community & Social',
        'other': '⭐ Other'
    };
    return names[category] || category;
}

// ============================================================
// ADD / EDIT EVENT
// ============================================================

function openAddEventModal() {
    document.getElementById('eventFormTitle').textContent = 'Add New Event';
    document.getElementById('eventForm').reset();
    document.getElementById('eventId').value = '';
    document.getElementById('addEventModal').style.display = 'block';
}

function openEditEventModal(eventId) {
    const event = allEvents.find(e => e.id === eventId);
    if (!event) return;

    document.getElementById('eventFormTitle').textContent = 'Edit Event';
    document.getElementById('eventId').value = event.id;
    document.getElementById('eventTitle').value = event.title || '';
    document.getElementById('eventDescription').value = event.description || '';
    document.getElementById('eventLocation').value = event.location || '';
    document.getElementById('eventCategory').value = event.category || '';
    document.getElementById('eventPrice').value = event.price || '';
    document.getElementById('eventSource').value = event.source || '';
    document.getElementById('eventSourceUrl').value = event.source_url || '';

    // Convert ISO dates to datetime-local format (YYYY-MM-DDTHH:MM)
    if (event.start_date) {
        const d = parseLocalDate(event.start_date);
        document.getElementById('eventStartDate').value = toDatetimeLocal(d);
    }
    if (event.end_date) {
        const d = parseLocalDate(event.end_date);
        document.getElementById('eventEndDate').value = toDatetimeLocal(d);
    }
    if (event.registration_deadline) {
        const d = parseLocalDate(event.registration_deadline);
        document.getElementById('eventRegDeadline').value = toDatetimeLocal(d);
    }

    closeModal();
    document.getElementById('addEventModal').style.display = 'block';
}

function toDatetimeLocal(date) {
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function closeAddEventModal() {
    document.getElementById('addEventModal').style.display = 'none';
}

async function handleEventFormSubmit(e) {
    e.preventDefault();

    const eventId = document.getElementById('eventId').value;
    const isEdit = !!eventId;

    const payload = {
        title: document.getElementById('eventTitle').value.trim(),
        description: document.getElementById('eventDescription').value.trim(),
        start_date: document.getElementById('eventStartDate').value,
        end_date: document.getElementById('eventEndDate').value || null,
        location: document.getElementById('eventLocation').value.trim(),
        category: document.getElementById('eventCategory').value,
        price: document.getElementById('eventPrice').value.trim() || null,
        source: document.getElementById('eventSource').value.trim() || 'User Added',
        source_url: document.getElementById('eventSourceUrl').value.trim() || null,
        registration_deadline: document.getElementById('eventRegDeadline').value || null,
    };

    try {
        const url = isEdit ? `${API_BASE}/events/${eventId}` : `${API_BASE}/events`;
        const method = isEdit ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            closeAddEventModal();
            await loadEvents();
            showToast(isEdit ? 'Event updated!' : 'Event added!', 'success');
        } else {
            showToast(`Error: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast('Failed to save event. Is the server running?', 'error');
    }
}

async function deleteEvent(eventId) {
    if (!confirm('Delete this event? This cannot be undone.')) return;

    try {
        const response = await fetch(`${API_BASE}/events/${eventId}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.success) {
            closeModal();
            await loadEvents();
            showToast('Event deleted.', 'success');
        } else {
            showToast(`Error: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast('Failed to delete event.', 'error');
    }
}

// ============================================================
// BOOKMARKS
// ============================================================

async function loadBookmarks() {
    try {
        const response = await fetch(`${API_BASE}/bookmarks`);
        const data = await response.json();
        if (data.success) {
            bookmarkedIds = new Set(data.bookmarks.map(b => b.id));
        }
    } catch (err) {
        console.error('Could not load bookmarks:', err);
    }
}

async function toggleBookmark(eventId) {
    const isBookmarked = bookmarkedIds.has(eventId);

    try {
        if (isBookmarked) {
            const response = await fetch(`${API_BASE}/bookmarks/${eventId}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                bookmarkedIds.delete(eventId);
                showToast('Bookmark removed.', 'success');
            }
        } else {
            const response = await fetch(`${API_BASE}/bookmarks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ event_id: eventId })
            });
            const data = await response.json();
            if (data.success) {
                bookmarkedIds.add(eventId);
                showToast('Event bookmarked! You\'ll get reminders.', 'success');
            }
        }

        // Refresh modal to update bookmark button state
        const event = allEvents.find(e => e.id === eventId);
        if (event) showEventDetail(event);

    } catch (err) {
        showToast('Failed to update bookmark.', 'error');
    }
}

async function showBookmarks() {
    try {
        const response = await fetch(`${API_BASE}/bookmarks`);
        const data = await response.json();

        const modal = document.getElementById('eventModal');
        const modalBody = document.getElementById('modalBody');

        if (!data.success || data.bookmarks.length === 0) {
            modalBody.innerHTML = `
                <h2 class="modal-title">⭐ My Bookmarks</h2>
                <p style="color:#666; margin-top:20px;">No bookmarked events yet.<br>
                Open any event and tap <strong>Bookmark</strong> to save it here.</p>
            `;
            modal.style.display = 'block';
            return;
        }

        const bookmarkRows = data.bookmarks.map(event => {
            const date = parseLocalDate(event.start_date);
            return `
                <div class="bookmark-row" onclick="showBookmarkedEvent(${event.id})" style="cursor:pointer">
                    <div class="bookmark-title">${event.title}</div>
                    <div class="bookmark-date">📅 ${date.toLocaleDateString('en-US', { weekday:'short', month:'short', day:'numeric', year:'numeric' })}</div>
                    <div class="bookmark-loc">📍 ${event.location}</div>
                </div>
            `;
        }).join('');

        modalBody.innerHTML = `
            <h2 class="modal-title">⭐ My Bookmarks (${data.bookmarks.length})</h2>
            <div class="bookmarks-list">${bookmarkRows}</div>
        `;
        modal.style.display = 'block';

    } catch (err) {
        showToast('Failed to load bookmarks.', 'error');
    }
}

function showBookmarkedEvent(eventId) {
    const event = allEvents.find(e => e.id === eventId);
    if (event) showEventDetail(event);
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(message, type = 'success') {
    // Remove any existing toast
    const existing = document.getElementById('toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'toast';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'error' ? '#ef4444' : '#10b981'};
        color: white;
        padding: 14px 28px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 15px;
        z-index: 9999;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        transition: opacity 0.4s;
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 400);
    }, 2800);
}
