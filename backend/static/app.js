// Philadelphia Events Calendar - JavaScript

const API_BASE = '';  // Same origin
let allEvents = [];
let filteredEvents = [];
let currentCategory = 'all';
let currentMonth = 'all';
let currentSource = 'all';
let currentNeighborhood = 'all';

// Keyword mapping: neighbourhood pill label → location substrings to match
const NEIGHBORHOOD_KEYWORDS = {
    'Rittenhouse':        ['rittenhouse', 'sansom', 'walnut street'],
    'Fairmount Park':     ['fairmount', 'kelly drive', 'west river drive', 'schuylkill', 'wissahickon'],
    'Old City':           ['old city', 'independence', '2nd st', 'old city arts'],
    'Northern Liberties': ['northern liberties', 'liberty'],
    'Queen Village':      ['queen village', 'south street'],
    'Graduate Hospital':  ['graduate hospital'],
    'Kensington':         ['kensington'],
    'Fishtown':           ['fishtown', 'frankford ave', 'johnny brenda'],
    'Manayunk':           ['manayunk'],
    'Brewerytown':        ['brewerytown', 'yards brewing'],
    'Point Breeze':       ['point breeze', 'passyunk', 'grays ferry'],
    'Chestnut Hill':      ['chestnut hill'],
    'West Philly':        ['west philly', 'clark park', '43rd', 'university of pennsylvania', 'franklin field'],
    'Passyunk':           ['passyunk', 'east passyunk'],
};
let bookmarkedIds = new Set(); // Track bookmarked event IDs (stored in localStorage)
let currentUser = null;        // { id, email, display_name } when logged in, else null
let savedEventIds = new Set(); // Server-side saved event IDs for the logged-in user

// ============================================================
// ADMIN AUTH (sessionStorage — clears when tab closes)
// ============================================================
const ADMIN_SESSION_KEY = 'philly_admin_token';
function getAdminToken() { return sessionStorage.getItem(ADMIN_SESSION_KEY) || ''; }
function isAdminMode() { return !!getAdminToken(); }

// Hero dismiss (sessionStorage — persists until tab closes)
const HERO_DISMISS_KEY = 'philly_hero_dismissed';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    initHeroDismiss();
    loadEvents();
    loadBookmarks();
    renderAdminControls();
    checkForUpdates();
    initUserSession(); // Check if user is already logged in
});

function initHeroDismiss() {
    const hero = document.getElementById('heroBanner');
    const closeBtn = document.getElementById('heroCloseBtn');
    if (!hero || !closeBtn) return;
    if (sessionStorage.getItem(HERO_DISMISS_KEY)) {
        hero.style.display = 'none';
    }
    closeBtn.addEventListener('click', () => {
        sessionStorage.setItem(HERO_DISMISS_KEY, '1');
        hero.style.display = 'none';
    });
}

// (No resize re-render needed — unified day-grouped view works at all sizes)

// Escape HTML to prevent XSS
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Strip HTML tags from a string (for descriptions that contain raw HTML)
function stripHtml(str) {
    if (!str) return '';
    // Remove all HTML tags
    const stripped = String(str).replace(/<[^>]*>/g, ' ');
    // Decode common HTML entities
    const decoded = stripped
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&nbsp;/g, ' ');
    // Collapse multiple spaces
    return decoded.replace(/\s+/g, ' ').trim();
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('input', handleSearch);
    document.getElementById('refreshBtn').addEventListener('click', refreshEvents);
    document.getElementById('monthSelect').addEventListener('change', handleMonthFilter);
    document.getElementById('sourceSelect').addEventListener('change', handleSourceFilter);

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => handleFilter(e.target.dataset.category));
    });

    document.getElementById('eventForm').addEventListener('submit', handleEventFormSubmit);

    // Event modal close (first .close is in event modal)
    const eventModalCloseBtn = document.getElementById('eventModalClose');
    if (eventModalCloseBtn) eventModalCloseBtn.addEventListener('click', closeModal);

    // Escape to close modals
    window.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        if (document.getElementById('addEventModal').style.display === 'block') {
            closeAddEventModal();
        } else if (document.getElementById('eventModal').style.display === 'block') {
            closeModal();
        }
    });

    // Scroll-to-top button visibility
    const scrollBtn = document.getElementById('scrollTopBtn');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            scrollBtn.classList.add('visible');
        } else {
            scrollBtn.classList.remove('visible');
        }
    });

    window.addEventListener('click', (e) => {
        if (e.target.id === 'eventModal') closeModal();
        if (e.target.id === 'profileModal') closeProfileModal();
    });
}

// Load events from API
async function loadEvents() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.textContent = 'Refreshing…';
    }
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
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.textContent = '🔄 Refresh';
        }
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

// Handle neighbourhood pill filter
function handleNeighborhoodFilter(neighborhood) {
    if (currentNeighborhood === neighborhood) {
        // Toggle off if already active
        currentNeighborhood = 'all';
    } else {
        currentNeighborhood = neighborhood;
    }

    // Update pill active states (only first set — duplicates have aria-hidden)
    document.querySelectorAll('.neighborhood-pills-track .nbhd-pill:not([aria-hidden])').forEach(pill => {
        if (pill.textContent.trim() === currentNeighborhood) {
            pill.classList.add('active');
        } else {
            pill.classList.remove('active');
        }
    });

    applyFilters();

    // Scroll to events section
    document.querySelector('.controls-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

// Clear all filters and search (used by empty state)
function clearFilters() {
    currentCategory = 'all';
    currentMonth = 'all';
    currentSource = 'all';
    currentNeighborhood = 'all';
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === 'all');
    });
    document.querySelectorAll('.nbhd-pill').forEach(pill => pill.classList.remove('active'));
    document.getElementById('monthSelect').value = 'all';
    document.getElementById('sourceSelect').value = 'all';
    document.getElementById('searchInput').value = '';
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

        const matchesSource = currentSource === 'all' || (event.source || '').trim() === currentSource;

        let matchesNeighborhood = true;
        if (currentNeighborhood !== 'all') {
            const keywords = NEIGHBORHOOD_KEYWORDS[currentNeighborhood] || [];
            const loc = (event.location || '').toLowerCase();
            matchesNeighborhood = keywords.some(kw => loc.includes(kw));
        }

        return matchesCategory && matchesMonth && matchesSource && matchesNeighborhood;
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
        // Only add non-empty, non-null source names
        if (event.source && event.source.trim()) {
            sources.add(event.source.trim());
        }
    });

    const sortedSources = Array.from(sources).sort();

    // Clear existing options and reset to "All Sources"
    sourceSelect.innerHTML = '<option value="all">All Sources</option>';

    // Add source options
    sortedSources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        sourceSelect.appendChild(option);
    });

    // Reset selection to "All Sources" on reload
    sourceSelect.value = 'all';
    currentSource = 'all';
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

        const matchesSource = currentSource === 'all' || (event.source || '').trim() === currentSource;

        let matchesNeighborhood = true;
        if (currentNeighborhood !== 'all') {
            const keywords = NEIGHBORHOOD_KEYWORDS[currentNeighborhood] || [];
            const loc = (event.location || '').toLowerCase();
            matchesNeighborhood = keywords.some(kw => loc.includes(kw));
        }

        const matchesSearch = query === '' || (
            event.title.toLowerCase().includes(query) ||
            event.description.toLowerCase().includes(query) ||
            event.location.toLowerCase().includes(query)
        );

        return matchesCategory && matchesMonth && matchesSource && matchesNeighborhood && matchesSearch;
    });

    renderEvents();
}

// Render events to DOM — unified day-grouped view for all screen sizes
function renderEvents() {
    const container = document.getElementById('eventsContainer');
    const emptyState = document.getElementById('emptyState');
    const emptyIcon = document.getElementById('emptyIcon');
    const emptyTitle = document.getElementById('emptyTitle');
    const emptyDesc = document.getElementById('emptyDesc');
    const emptyActions = document.getElementById('emptyActions');

    if (filteredEvents.length === 0) {
        container.innerHTML = '';
        emptyState.style.display = 'block';
        const hasFilters = allEvents.length > 0;
        if (hasFilters) {
            emptyIcon.textContent = '🔍';
            emptyTitle.textContent = 'No events match your filters';
            emptyDesc.textContent = 'Try a different category, month, or search.';
            emptyActions.innerHTML = '<button type="button" class="btn btn-ghost" onclick="clearFilters()">Clear all filters</button>';
        } else {
            emptyIcon.textContent = '🔔';
            emptyTitle.textContent = 'No events found';
            emptyDesc.textContent = 'Try adjusting your filters or check back soon!';
            emptyActions.innerHTML = '';
        }
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
                ? `<span class="event-time">${escapeHtml(timeStr)}</span>`
                : `<span class="event-time-tbd">Time TBD</span>`}
        </div>
        <div class="event-row-divider"></div>
        <div class="event-details-col">
            <div class="event-row-top">
                <span class="event-row-title">${escapeHtml(event.title)}</span>
                <span class="event-category ${categoryClass}">${categoryName}</span>
            </div>
            <div class="event-row-meta">
                ${location ? `<span class="event-row-location">📍 ${escapeHtml(location)}</span>` : ''}
                ${price ? `<span class="event-row-price">💰 ${escapeHtml(price)}</span>` : ''}
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
    const isSaved = currentUser ? savedEventIds.has(event.id) : false;

    const cleanDescription = stripHtml(event.description || '');
    const safeUrl = event.source_url ? escapeHtml(event.source_url) : '';

    // Build save/bookmark button
    let saveBtn = '';
    if (currentUser) {
        saveBtn = `<button class="btn ${isSaved ? 'btn-warning' : 'btn-success'}" onclick="toggleSave(${event.id})">
            ${isSaved ? '❤️ Saved' : '🤍 Save'}
        </button>`;
    } else {
        saveBtn = `<button class="btn ${isBookmarked ? 'btn-warning' : 'btn-success'}" onclick="toggleBookmark(${event.id})">
            ${isBookmarked ? '⭐ Bookmarked' : '☆ Bookmark'}
        </button>`;
    }

    modalBody.innerHTML = `
        <h2 class="modal-title" id="eventModalTitle">${escapeHtml(event.title)}</h2>

        <div class="modal-detail">
            <strong>📅 Date & Time</strong><br>
            ${escapeHtml(formatDateLong(startDate))}
        </div>

        <div class="modal-detail">
            <strong>📍 Location</strong><br>
            ${escapeHtml(event.location)}
            ${safeUrl ? `<br><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">🔗 View Event Website</a>` : ''}
        </div>

        <div class="modal-detail">
            <strong>🎯 Category</strong><br>
            ${escapeHtml(categoryName)}
        </div>

        ${event.price ? `
        <div class="modal-detail">
            <strong>💰 Price</strong><br>
            ${escapeHtml(event.price)}
        </div>
        ` : ''}

        ${event.registration_deadline ? `
        <div class="modal-detail">
            <strong>⏰ Registration Deadline</strong><br>
            ${escapeHtml(parseLocalDate(event.registration_deadline).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }))}
        </div>
        ` : ''}

        ${cleanDescription ? `
        <div class="modal-detail">
            <strong>📝 Description</strong><br>
            ${escapeHtml(cleanDescription)}
        </div>
        ` : ''}

        <div class="modal-detail">
            <strong>ℹ️ Source</strong><br>
            ${escapeHtml(event.source || 'Unknown')}
        </div>

        <div class="event-detail-actions">
            ${saveBtn}
            ${isAdminMode() ? `
            <button class="btn btn-primary" onclick="openEditEventModal(${event.id})">✏️ Edit</button>
            <button class="btn btn-danger" onclick="deleteEvent(${event.id})">🗑️ Delete</button>
            ` : ''}
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
    document.getElementById('loadingState').style.display = show ? 'block' : 'none';
}

// Show empty state
function showEmptyState() {
    document.getElementById('eventsContainer').innerHTML = '';
    document.getElementById('emptyState').style.display = 'block';
}

// Show notification (uses toast system)
function showNotification(message, type = 'success') {
    showToast(message, type);
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
        });
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
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Token': getAdminToken()
            },
            body: JSON.stringify(payload)
        });

        if (response.status === 401 || response.status === 403) {
            showToast('Invalid admin password. Please log in again.', 'error');
            adminLogout();
            return;
        }

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
        const response = await fetch(`${API_BASE}/events/${eventId}`, {
            method: 'DELETE',
            headers: { 'X-Admin-Token': getAdminToken() }
        });

        if (response.status === 401 || response.status === 403) {
            showToast('Invalid admin password. Please log in again.', 'error');
            adminLogout();
            return;
        }

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
// BOOKMARKS (stored in localStorage — private per browser)
// ============================================================

function loadBookmarks() {
    try {
        const raw = localStorage.getItem('philly_bookmarks');
        const ids = raw ? JSON.parse(raw) : [];
        bookmarkedIds = new Set(ids);
    } catch (err) {
        console.error('Could not load bookmarks from localStorage:', err);
        bookmarkedIds = new Set();
    }
}

function saveBookmarks() {
    localStorage.setItem('philly_bookmarks', JSON.stringify([...bookmarkedIds]));
}

function toggleBookmark(eventId) {
    if (bookmarkedIds.has(eventId)) {
        bookmarkedIds.delete(eventId);
        showToast('Bookmark removed.', 'success');
    } else {
        bookmarkedIds.add(eventId);
        showToast('Event bookmarked!', 'success');
    }
    saveBookmarks();
    // Refresh modal to update bookmark button state
    const event = allEvents.find(e => e.id === eventId);
    if (event) showEventDetail(event);
}

function showBookmarks() {
    const modal = document.getElementById('eventModal');
    const modalBody = document.getElementById('modalBody');

    const bookmarkedEvents = allEvents.filter(e => bookmarkedIds.has(e.id));

    if (bookmarkedEvents.length === 0) {
        modalBody.innerHTML = `
            <h2 class="modal-title">⭐ My Bookmarks</h2>
            <p style="color:#666; margin-top:20px;">No bookmarked events yet.<br>
            Open any event and tap <strong>Bookmark</strong> to save it here.</p>
        `;
        modal.style.display = 'block';
        return;
    }

    const bookmarkRows = bookmarkedEvents.map(event => {
        const date = parseLocalDate(event.start_date);
        return `
            <div class="bookmark-row" onclick="showBookmarkedEvent(${event.id})" style="cursor:pointer">
                <div class="bookmark-title">${escapeHtml(event.title)}</div>
                <div class="bookmark-date">📅 ${escapeHtml(date.toLocaleDateString('en-US', { weekday:'short', month:'short', day:'numeric', year:'numeric' }))}</div>
                <div class="bookmark-loc">📍 ${escapeHtml(event.location)}</div>
            </div>
        `;
    }).join('');

    modalBody.innerHTML = `
        <h2 class="modal-title">⭐ My Bookmarks (${bookmarkedEvents.length})</h2>
        <div class="bookmarks-list">${bookmarkRows}</div>
    `;
    modal.style.display = 'block';
}

// ============================================================
// ADMIN
// ============================================================

function adminLogin() {
    const token = prompt('Enter admin password:');
    if (!token) return;
    sessionStorage.setItem(ADMIN_SESSION_KEY, token);
    renderAdminControls();
    showToast('Admin mode enabled', 'success');
}

function adminLogout() {
    sessionStorage.removeItem(ADMIN_SESSION_KEY);
    renderAdminControls();
    showToast('Admin mode disabled', 'success');
}

function handleAdminBtn() {
    if (isAdminMode()) {
        if (confirm('Exit admin mode?')) adminLogout();
    } else {
        adminLogin();
    }
}

function renderAdminControls() {
    const adminBtn = document.getElementById('adminBtn');
    if (!adminBtn) return;

    if (isAdminMode()) {
        adminBtn.textContent = '🔒 Admin On';
        adminBtn.classList.remove('btn-secondary');
        adminBtn.classList.add('btn-warning');
    } else {
        adminBtn.textContent = '🔑 Admin';
        adminBtn.classList.remove('btn-warning');
        adminBtn.classList.add('btn-secondary');
    }

    // Show/hide the "+ Add Event" button
    let addBtn = document.getElementById('addEventBtn');
    if (isAdminMode() && !addBtn) {
        addBtn = document.createElement('button');
        addBtn.id = 'addEventBtn';
        addBtn.className = 'btn btn-success';
        addBtn.textContent = '+ Add Event';
        addBtn.onclick = openAddEventModal;
        document.querySelector('.action-btns').appendChild(addBtn);
    } else if (!isAdminMode() && addBtn) {
        addBtn.remove();
    }
}

function showBookmarkedEvent(eventId) {
    const event = allEvents.find(e => e.id === eventId);
    if (event) showEventDetail(event);
}

// ============================================================
// USER AUTH — Email + OTP
// ============================================================

async function initUserSession() {
    try {
        const res = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
        const data = await res.json();
        if (data.logged_in) {
            currentUser = data.user;
            await loadUserSaves();
            updateProfileBtn();
        }
    } catch (err) {
        // Not logged in or server error — stay anonymous
    }
}

function handleProfileBtn() {
    if (currentUser) {
        showSavesModal();
    } else {
        showSignInModal();
    }
}

function updateProfileBtn() {
    const btn = document.getElementById('profileBtn');
    if (!btn) return;
    if (currentUser) {
        const label = currentUser.display_name
            ? currentUser.display_name.split(' ')[0]
            : currentUser.email.split('@')[0];
        btn.textContent = `👤 ${label}`;
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-primary');
    } else {
        btn.textContent = '👤 Sign In';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
    }
}

function showSignInModal() {
    const modal = document.getElementById('profileModal');
    const body = document.getElementById('profileModalBody');
    body.innerHTML = `
        <h2 class="modal-title">👤 Sign In</h2>
        <p style="color:#666; margin-bottom:20px;">Enter your email to receive a one-time login code.</p>
        <div id="otpStep1">
            <div class="form-group">
                <label for="otpEmail">Email Address</label>
                <input type="email" id="otpEmail" placeholder="you@example.com" style="width:100%;">
            </div>
            <div class="form-actions">
                <button class="btn btn-primary" onclick="sendOtp()">📧 Send Code</button>
            </div>
        </div>
        <div id="otpStep2" style="display:none;">
            <p style="color:#10b981; font-weight:600; margin-bottom:16px;">✅ Code sent! Check your inbox.</p>
            <div class="form-group">
                <label for="otpCode">6-Digit Code</label>
                <input type="text" id="otpCode" placeholder="123456" maxlength="6"
                    style="width:100%; font-size:1.4em; letter-spacing:0.2em; text-align:center;"
                    oninput="this.value=this.value.replace(/[^0-9]/g,'')">
            </div>
            <div class="form-actions">
                <button class="btn btn-primary" onclick="verifyOtp()">✅ Verify Code</button>
                <button class="btn btn-secondary" onclick="sendOtp(true)">↩ Resend</button>
            </div>
        </div>
    `;
    modal.style.display = 'block';
}

async function sendOtp(resend = false) {
    const emailEl = document.getElementById('otpEmail');
    const email = emailEl ? emailEl.value.trim() : '';
    if (!email || !email.includes('@')) {
        showToast('Please enter a valid email address.', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/send-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('otpStep1').style.display = 'none';
            document.getElementById('otpStep2').style.display = 'block';
            if (resend) showToast('New code sent!', 'success');
        } else {
            showToast(data.error || 'Could not send code. Try again.', 'error');
        }
    } catch (err) {
        showToast('Could not connect to server.', 'error');
    }
}

async function verifyOtp() {
    const emailEl = document.getElementById('otpEmail');
    const codeEl = document.getElementById('otpCode');
    const email = emailEl ? emailEl.value.trim() : '';
    const code = codeEl ? codeEl.value.trim() : '';

    if (!code || code.length !== 6) {
        showToast('Please enter the 6-digit code.', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, code })
        });
        const data = await res.json();
        if (data.success) {
            await onLoginSuccess(data.user);
        } else {
            showToast(data.error || 'Invalid or expired code.', 'error');
        }
    } catch (err) {
        showToast('Could not connect to server.', 'error');
    }
}

async function onLoginSuccess(user) {
    currentUser = user;
    closeProfileModal();

    // Migrate any existing localStorage bookmarks to server saves
    if (bookmarkedIds.size > 0) {
        const ids = [...bookmarkedIds];
        for (const eventId of ids) {
            try {
                await fetch(`${API_BASE}/profile/saves`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ event_id: eventId })
                });
            } catch (_) {}
        }
        // Clear localStorage bookmarks after migration
        bookmarkedIds = new Set();
        saveBookmarks();
    }

    await loadUserSaves();
    updateProfileBtn();

    const firstName = user.display_name
        ? user.display_name.split(' ')[0]
        : user.email.split('@')[0];
    showToast(`Welcome, ${firstName}! 🎉`, 'success');
}

async function logoutUser() {
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (_) {}
    currentUser = null;
    savedEventIds = new Set();
    updateProfileBtn();
    closeProfileModal();
    showToast('Signed out.', 'success');
}

// ============================================================
// USER SAVES (server-side)
// ============================================================

async function loadUserSaves() {
    if (!currentUser) return;
    try {
        const res = await fetch(`${API_BASE}/profile/saves`, { credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            savedEventIds = new Set(data.event_ids);
        }
    } catch (err) {
        console.error('Could not load saved events:', err);
    }
}

async function toggleSave(eventId) {
    if (!currentUser) {
        // Not logged in — fall back to bookmark
        toggleBookmark(eventId);
        return;
    }

    const isSaved = savedEventIds.has(eventId);
    try {
        if (isSaved) {
            const res = await fetch(`${API_BASE}/profile/saves/${eventId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            const data = await res.json();
            if (data.success) {
                savedEventIds.delete(eventId);
                showToast('Removed from saves.', 'success');
            }
        } else {
            const res = await fetch(`${API_BASE}/profile/saves`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ event_id: eventId })
            });
            const data = await res.json();
            if (data.success) {
                savedEventIds.add(eventId);
                showToast('Event saved! ❤️', 'success');
            }
        }
    } catch (err) {
        showToast('Could not update saves. Try again.', 'error');
        return;
    }

    // Refresh modal to reflect updated state
    const event = allEvents.find(e => e.id === eventId);
    if (event) showEventDetail(event);
}

// ============================================================
// PROFILE / SAVES MODAL
// ============================================================

function showSavesModal() {
    const modal = document.getElementById('profileModal');
    const body = document.getElementById('profileModalBody');

    if (!currentUser) {
        showSignInModal();
        return;
    }

    const initial = (currentUser.display_name || currentUser.email)[0].toUpperCase();
    const displayEmail = escapeHtml(currentUser.email);
    const displayName = escapeHtml(currentUser.display_name || currentUser.email.split('@')[0]);

    // Get saved events from allEvents
    const savedEvents = allEvents.filter(e => savedEventIds.has(e.id));

    let eventsHtml = '';
    if (savedEvents.length === 0) {
        eventsHtml = `
            <div style="text-align:center; padding:30px 0; color:#666;">
                <p style="font-size:2em; margin-bottom:12px;">🤍</p>
                <p style="font-weight:600; color:#333; margin-bottom:8px;">No saved events yet</p>
                <p>Open any event and tap <strong>🤍 Save</strong> to save it here.</p>
            </div>`;
    } else {
        eventsHtml = savedEvents.map(event => {
            const date = parseLocalDate(event.start_date);
            const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
            return `
                <div class="bookmark-row" onclick="openSavedEvent(${event.id})" style="cursor:pointer; position:relative;">
                    <div class="bookmark-title">${escapeHtml(event.title)}</div>
                    <div class="bookmark-date">📅 ${escapeHtml(dateStr)}</div>
                    <div class="bookmark-loc">📍 ${escapeHtml(event.location || '')}</div>
                    <button class="btn btn-danger" style="position:absolute; right:0; top:50%; transform:translateY(-50%); padding:4px 10px; font-size:12px;"
                        onclick="event.stopPropagation(); toggleSave(${event.id}); showSavesModal();">✕</button>
                </div>`;
        }).join('');
    }

    body.innerHTML = `
        <div style="display:flex; align-items:center; gap:14px; margin-bottom:20px;">
            <div style="width:48px; height:48px; border-radius:50%; background:#004C54; color:#FFB612;
                        display:flex; align-items:center; justify-content:center; font-size:1.5em; font-weight:700;">
                ${initial}
            </div>
            <div>
                <div style="font-weight:700; font-size:1.05em;">${displayName}</div>
                <div style="color:#666; font-size:0.9em;">${displayEmail}</div>
            </div>
            <button class="btn btn-secondary" style="margin-left:auto; font-size:13px;"
                onclick="logoutUser()">Sign Out</button>
        </div>
        <h3 style="margin-bottom:14px; font-size:1em; color:#333;">❤️ Saved Events (${savedEvents.length})</h3>
        <div class="bookmarks-list">${eventsHtml}</div>
    `;
    modal.style.display = 'block';
}

function openSavedEvent(eventId) {
    closeProfileModal();
    const event = allEvents.find(e => e.id === eventId);
    if (event) showEventDetail(event);
}

function closeProfileModal() {
    document.getElementById('profileModal').style.display = 'none';
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
