// Philadelphia Events Calendar - JavaScript

const API_BASE = '';  // Same origin
let allEvents = [];
let filteredEvents = [];
let currentCategory = 'all';
let currentMonth = 'all';
let currentNeighborhood = 'all';
let currentTimeFilter = null; // null | 'today' | 'tomorrow' | 'weekend'

// Category badge labels (text-only, no emoji — keeps pills compact on mobile)
const BADGE_LABELS = {
    running: 'Running',
    artsAndCulture: 'Arts & Culture',
    music: 'Music',
    foodAndDrink: 'Food & Drink',
    community: 'Community',
    business: 'Business',
    other: 'Other',
};

// Normalize event titles: if a title is mostly uppercase (shouting), convert to title case.
// Leaves mixed-case titles (e.g. "Dad's Hat & Gas Lamp Hotel") untouched.
function normalizeTitle(title) {
    if (!title) return title;
    const letters = title.replace(/[^a-zA-Z]/g, '');
    if (!letters.length) return title;
    // Only normalize if >60% of letters are uppercase
    const upperRatio = (title.match(/[A-Z]/g) || []).length / letters.length;
    if (upperRatio < 0.6) return title;
    // Small words that stay lowercase (except at the very start)
    const minor = new Set(['a','an','the','and','but','or','nor','for','so','at','by','in','of','on','to','up','as','via','vs','&']);
    return title.toLowerCase().replace(/(\S+)/g, (word, offset) => {
        if (offset === 0 || !minor.has(word)) {
            return word.charAt(0).toUpperCase() + word.slice(1);
        }
        return word;
    });
}

// Keyword mapping: neighbourhood pill label → location substrings to match.
// ONLY entries in this map ever appear in the neighborhood strip — no auto-discovery.
const NEIGHBORHOOD_KEYWORDS = {
    'Rittenhouse':        ['rittenhouse', 'sansom', 'walnut street'],
    'Center City':        ['center city', 'city hall', 'market st', 'market street', 'broad street', 'broad st', 'chestnut st', 'chestnut street', 'juniper', 'dilworth'],
    'Old City':           ['old city', 'independence', '2nd st', '3rd st', 'old city arts', 'elfreth'],
    'Society Hill':       ['society hill', 'headhouse'],
    'Washington Sq West': ['washington square', 'wash west', 'pine street', 'spruce street'],
    'Chinatown':          ['chinatown', 'race street', '10th st', '11th st'],
    'Logan Square':       ['logan square', 'logan circle', 'parkway', 'ben franklin pkwy', 'benjamin franklin pkwy'],
    'Fairmount':          ['fairmount', 'eastern state', 'girard ave', 'fairmount ave'],
    'Fairmount Park':     ['fairmount park', 'kelly drive', 'west river drive', 'wissahickon'],
    'Northern Liberties': ['northern liberties', 'n liberties'],
    'Fishtown':           ['fishtown', 'frankford ave', 'johnny brenda', 'girard'],
    'Kensington':         ['kensington'],
    'Port Richmond':      ['port richmond', 'richmond st'],
    'Bridesburg':         ['bridesburg'],
    'Queen Village':      ['queen village', 'south street'],
    'Bella Vista':        ['bella vista', 'christian street', '9th street', 'italian market'],
    'Graduate Hospital':  ['graduate hospital', 'grad hospital'],
    'Point Breeze':       ['point breeze', 'grays ferry'],
    'Passyunk':           ['passyunk', 'east passyunk'],
    'South Philly':       ['south philly', 'south philadelphia', 'pattison', 'xfinity live', 'citizens bank park', 'lincoln financial', 'wells fargo center'],
    'University City':    ['university city', 'university of pennsylvania', 'penn medicine', 'drexel', 'upen', 'upenn', '40th', '38th', '34th street', 'clark park'],
    'West Philly':        ['west philly', 'west philadelphia', '43rd', 'cobbs creek', 'spruce hill', 'cedar park'],
    'Brewerytown':        ['brewerytown', 'yards brewing', 'girard estates'],
    'Strawberry Mansion': ['strawberry mansion'],
    'Germantown':         ['germantown', 'tulpehocken', 'chelten'],
    'Mt. Airy':           ['mt. airy', 'mt airy', 'mount airy', 'lincoln drive'],
    'Chestnut Hill':      ['chestnut hill', 'germantown ave'],
    'Roxborough':         ['roxborough', 'manayunk ave'],
    'Manayunk':           ['manayunk'],
    'East Falls':         ['east falls', 'henry ave'],
    'Hunting Park':       ['hunting park'],
    'Olney':              ['olney', 'fifth street', '5th street highway'],
    'Mayfair':            ['mayfair', 'frankford'],
    'Northeast Philly':   ['northeast philly', 'northeast philadelphia', 'bustleton', 'rhawnhurst', 'fox chase', 'torresdale', 'holmesburg', 'pennypack'],
    'Reading Terminal':   ['reading terminal', '12th and arch', 'filbert street'],
};
let bookmarkedIds = new Set(); // Track bookmarked event IDs (stored in localStorage)
let currentUser = null;        // { id, email, display_name } when logged in, else null
let savedEventIds = new Set(); // Server-side saved event IDs for the logged-in user
let showAllEvents = false;     // Whether to show events beyond the first month

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
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) refreshBtn.addEventListener('click', refreshEvents);
    document.getElementById('monthSelect').addEventListener('change', handleMonthFilter);

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


    // --- HAMBURGER MENU ---
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const mobileNavDrawer = document.getElementById('mobileNavDrawer');
    if (hamburgerBtn && mobileNavDrawer) {
        hamburgerBtn.addEventListener('click', toggleMobileNav);
    }
    // Mobile refresh button in drawer
    const mobileRefreshBtn = document.getElementById('mobileRefreshBtn');
    if (mobileRefreshBtn) {
        mobileRefreshBtn.addEventListener('click', () => {
            closeMobileNav();
            refreshEvents();
        });
    }
    // Close drawer if user taps outside of it
    document.addEventListener('click', (e) => {
        if (mobileNavDrawer && mobileNavDrawer.classList.contains('open')) {
            if (!mobileNavDrawer.contains(e.target) && e.target !== hamburgerBtn && !hamburgerBtn.contains(e.target)) {
                closeMobileNav();
            }
        }
    });
}

function toggleMobileNav() {
    const drawer = document.getElementById('mobileNavDrawer');
    const btn = document.getElementById('hamburgerBtn');
    if (!drawer || !btn) return;
    const isOpen = drawer.classList.contains('open');
    if (isOpen) {
        closeMobileNav();
    } else {
        drawer.classList.add('open');
        drawer.setAttribute('aria-hidden', 'false');
        btn.setAttribute('aria-expanded', 'true');
        // Swap to X icon
        btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
    }
}

function closeMobileNav() {
    const drawer = document.getElementById('mobileNavDrawer');
    const btn = document.getElementById('hamburgerBtn');
    if (!drawer || !btn) return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    btn.setAttribute('aria-expanded', 'false');
    // Restore hamburger icon
    btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
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
            // Filter out any events before today's midnight in local time
            const todayMidnight = new Date();
            todayMidnight.setHours(0, 0, 0, 0);
            allEvents = data.events.filter(e => {
                try { return parseLocalDate(e.start_date) >= todayMidnight; }
                catch { return true; }
            });
            filteredEvents = allEvents;
            populateMonthFilter();
            renderEvents();
            updateStats();
            // Update hero event count
            const heroCount = document.getElementById('heroEventCount');
            if (heroCount && allEvents.length > 0) {
                heroCount.textContent = `${allEvents.length} upcoming events in Philadelphia`;
            }
            // Rebuild neighborhood strip from live event data
            buildNeighborhoodStrip();
            // Rebuild hottest this week cards
            buildHottestCards();
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

// Update the event count badges on the landmark cards
function updateLandmarkBadges() {
    if (!allEvents || !allEvents.length) return;

    // Count events per neighborhood group using NEIGHBORHOOD_KEYWORDS
    function countForNeighborhood(neighborhood) {
        const keywords = NEIGHBORHOOD_KEYWORDS[neighborhood] || [neighborhood.toLowerCase()];
        return allEvents.filter(ev => {
            const loc = (ev.location || '').toLowerCase();
            return keywords.some(kw => loc.includes(kw));
        }).length;
    }

    const fairmountCount = countForNeighborhood('Fairmount Park');
    const oldCityCount   = countForNeighborhood('Old City');
    const rittenhouseCount = countForNeighborhood('Rittenhouse');

    // Rocky Statue & Art Museum both filter by Fairmount Park
    const badgeFairmount = document.getElementById('badgeFairmount');
    const badgeArtMuseum = document.getElementById('badgeArtMuseum');
    const badgeOldCity   = document.getElementById('badgeOldCity');
    const badgeRittenhouse = document.getElementById('badgeRittenhouse');

    if (badgeFairmount) badgeFairmount.textContent = fairmountCount ? `${fairmountCount} events` : 'Explore';
    if (badgeArtMuseum) badgeArtMuseum.textContent = fairmountCount ? `${fairmountCount} events` : 'Explore';
    if (badgeOldCity)   badgeOldCity.textContent   = oldCityCount   ? `${oldCityCount} events`   : 'Explore';
    if (badgeRittenhouse) badgeRittenhouse.textContent = rittenhouseCount ? `${rittenhouseCount} events` : 'Explore';
}

// Build neighborhood pills from NEIGHBORHOOD_KEYWORDS — only shows curated Philly
// neighborhoods that have ≥1 matching event. No auto-discovery from raw location strings.
function buildNeighborhoodStrip() {
    const track = document.querySelector('.neighborhood-pills-track');
    if (!track || !allEvents.length) return;

    // Known neighborhoods that have ≥1 event
    const activeKnown = Object.keys(NEIGHBORHOOD_KEYWORDS).filter(name => {
        const keywords = NEIGHBORHOOD_KEYWORDS[name];
        return allEvents.some(ev => {
            const loc = (ev.location || '').toLowerCase();
            return keywords.some(kw => loc.includes(kw));
        });
    });

    if (!activeKnown.length) return;
    const allNames = activeKnown;

    function pill(name, hidden = false) {
        const attrs = hidden ? ' aria-hidden="true" tabindex="-1"' : '';
        return `<button class="nbhd-pill" onclick="handleNeighborhoodFilter('${name}')"${attrs}>${name}</button>`;
    }

    track.innerHTML =
        allNames.map(n => pill(n)).join('') +
        allNames.map(n => pill(n, true)).join('');
}

// Build "Hottest This Week" neighborhood cards
// Shows up to 4 neighborhoods with the most events in the next 7 days.
function buildHottestCards() {
    const container = document.getElementById('hottestCardsScroll');
    const section = document.getElementById('hottestSection');
    if (!container || !allEvents.length) return;

    const now = new Date();
    const sevenDaysOut = new Date(now);
    sevenDaysOut.setDate(now.getDate() + 7);

    // Count events per neighborhood for the next 7 days
    const counts = {}; // neighborhoodName -> { count, titles[] }
    allEvents.forEach(ev => {
        const evDate = new Date(ev.start_datetime);
        if (evDate < now || evDate > sevenDaysOut) return;
        const loc = (ev.location || '').toLowerCase();
        for (const [name, keywords] of Object.entries(NEIGHBORHOOD_KEYWORDS)) {
            if (keywords.some(kw => loc.includes(kw))) {
                if (!counts[name]) counts[name] = { count: 0, titles: [] };
                counts[name].count++;
                if (counts[name].titles.length < 3) {
                    counts[name].titles.push(normalizeTitle(ev.title));
                }
                break; // assign to first matching neighborhood only
            }
        }
    });

    // Sort by event count descending, take top 4
    const top = Object.entries(counts)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 4);

    if (!top.length) {
        if (section) section.style.display = 'none';
        return;
    }

    if (section) section.style.display = '';

    container.innerHTML = top.map(([name, data], i) => {
        const shown = data.titles.slice(0, 2);
        const extra = data.count - shown.length;
        const moreHtml = extra > 0
            ? `<div class="hottest-card-more">+${extra} more</div>`
            : '<div class="hottest-card-more">&nbsp;</div>';
        return `
        <div class="hottest-card hc-${i}" onclick="handleNeighborhoodFilter('${name}')" role="button" tabindex="0" aria-label="${name}, ${data.count} events this week">
            <div>
                <div class="hottest-card-name">${escapeHtml(name)}</div>
                <ul class="hottest-card-events">
                    ${shown.map(t => `<li>${escapeHtml(t)}</li>`).join('')}
                </ul>
                ${moreHtml}
            </div>
            <div class="hottest-card-count">${data.count} event${data.count !== 1 ? 's' : ''} →</div>
        </div>`;
    }).join('');
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

    // If triggered from hero pills, scroll to the events list
    document.querySelector('.page-wrapper')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Handle month filter — clears any active time filter since they're mutually exclusive
function handleMonthFilter(e) {
    currentMonth = e.target.value;
    if (currentTimeFilter) clearTimeFilter(false); // clear time pills without re-running filters
    applyFilters();
}

// Handle time filter pills (Today / Tomorrow / This Weekend)
function handleTimeFilter(value) {
    // Toggle off if same pill clicked again
    if (currentTimeFilter === value) {
        clearTimeFilter();
        return;
    }

    currentTimeFilter = value;

    // Update pill active states
    document.querySelectorAll('.hero-time-pill').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.time === value);
    });

    // Hide month dropdown — mutually exclusive
    const monthWrap = document.getElementById('monthSelectWrap');
    if (monthWrap) monthWrap.style.display = 'none';

    // Clear month selection
    currentMonth = 'all';
    const monthSelect = document.getElementById('monthSelect');
    if (monthSelect) monthSelect.value = 'all';

    // Scroll to events list
    document.querySelector('.page-wrapper')?.scrollIntoView({ behavior: 'smooth' });

    applyFilters();
}

// Clear the time filter and restore month dropdown
function clearTimeFilter(andApply = true) {
    currentTimeFilter = null;
    document.querySelectorAll('.hero-time-pill').forEach(btn => btn.classList.remove('active'));
    const monthWrap = document.getElementById('monthSelectWrap');
    if (monthWrap) monthWrap.style.display = '';
    if (andApply) applyFilters();
}


// Clear all filters and search (used by empty state)
function clearFilters() {
    currentCategory = 'all';
    currentMonth = 'all';
    currentNeighborhood = 'all';
    currentTimeFilter = null;
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === 'all');
    });
    document.querySelectorAll('.nbhd-pill').forEach(pill => pill.classList.remove('active'));
    document.querySelectorAll('.hero-time-pill').forEach(btn => btn.classList.remove('active'));
    document.getElementById('monthSelect').value = 'all';
    document.getElementById('searchInput').value = '';
    const monthWrap = document.getElementById('monthSelectWrap');
    if (monthWrap) monthWrap.style.display = '';
    const inlineClear = document.getElementById('inlineClearBtn');
    if (inlineClear) inlineClear.style.display = 'none';
    const searchClear = document.getElementById('searchClearBtn');
    if (searchClear) searchClear.style.display = 'none';
    updateActiveFiltersBar();
    applyFilters();
}

// Store clear actions for active filter tags (keyed by index)
const _filterTagActions = {};

// Update the active filters bar — shows a tag for each active filter
function updateActiveFiltersBar() {
    const bar  = document.getElementById('activeFiltersBar');
    const tags = document.getElementById('activeFilterTags');
    if (!bar || !tags) return;

    const searchVal = (document.getElementById('searchInput')?.value || '').trim();
    const active = [];

    if (currentTimeFilter) {
        const labels = { today: 'Today', tomorrow: 'Tomorrow', weekend: 'This Weekend' };
        active.push({ label: '🗓 ' + labels[currentTimeFilter], key: 'time', clear: () => clearTimeFilter() });
    }
    if (currentCategory !== 'all') {
        const label = { running:'Running', music:'Music', artsAndCulture:'Arts & Culture',
                        foodAndDrink:'Food & Drink', community:'Community' }[currentCategory] || currentCategory;
        active.push({ label, key: 'cat', clear: () => handleFilter('all') });
    }
    if (currentNeighborhood !== 'all') {
        const nb = currentNeighborhood;
        active.push({ label: '📍 ' + nb, key: 'nbhd', clear: () => handleNeighborhoodFilter(nb) });
    }
    if (!currentTimeFilter && currentMonth !== 'all') {
        const [y, m] = currentMonth.split('-');
        const monthName = new Date(y, m - 1, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        active.push({ label: '📅 ' + monthName, key: 'month', clear: () => {
            currentMonth = 'all';
            document.getElementById('monthSelect').value = 'all';
            applyFilters();
        }});
    }
    if (searchVal) {
        active.push({ label: '🔎 "' + searchVal + '"', key: 'search', clear: () => {
            document.getElementById('searchInput').value = '';
            document.getElementById('searchInput').dispatchEvent(new Event('input'));
        }});
    }

    // Show/hide the inline clear button in the filter row
    const inlineClear = document.getElementById('inlineClearBtn');
    if (inlineClear) inlineClear.style.display = active.length > 0 ? 'inline-flex' : 'none';

    // Show/hide the search ✕ clear button
    const searchClear = document.getElementById('searchClearBtn');
    if (searchClear) searchClear.style.display = searchVal ? 'block' : 'none';

    if (active.length === 0) {
        bar.style.display = 'none';
        tags.innerHTML = '';
        return;
    }

    // Store clear actions globally so inline onclick can call them
    active.forEach((f, i) => { _filterTagActions[f.key] = f.clear; });

    bar.style.display = 'flex';
    tags.innerHTML = active.map(f =>
        `<button class="active-filter-tag" onclick="_filterTagActions['${f.key}']()" title="Remove this filter">
            ${escapeHtml(f.label)} <span class="tag-x">✕</span>
        </button>`
    ).join('');
}

// Apply all filters
function applyFilters() {
    showAllEvents = false;
    filteredEvents = allEvents.filter(event => {
        const matchesCategory = currentCategory === 'all' || event.category === currentCategory;

        // Time filter (today/tomorrow/weekend) takes priority over month filter
        let matchesTime = true;
        if (currentTimeFilter) {
            const evDate = parseLocalDate(event.start_date);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const tomorrow = new Date(today);
            tomorrow.setDate(today.getDate() + 1);

            if (currentTimeFilter === 'today') {
                const todayEnd = new Date(today);
                todayEnd.setHours(23, 59, 59, 999);
                matchesTime = evDate >= today && evDate <= todayEnd;
            } else if (currentTimeFilter === 'tomorrow') {
                const tomorrowEnd = new Date(tomorrow);
                tomorrowEnd.setHours(23, 59, 59, 999);
                matchesTime = evDate >= tomorrow && evDate <= tomorrowEnd;
            } else if (currentTimeFilter === 'weekend') {
                // Find nearest Saturday
                const dayOfWeek = today.getDay(); // 0=Sun, 6=Sat
                const daysToSat = dayOfWeek === 6 ? 0 : (6 - dayOfWeek);
                const saturday = new Date(today);
                saturday.setDate(today.getDate() + daysToSat);
                const sunday = new Date(saturday);
                sunday.setDate(saturday.getDate() + 1);
                sunday.setHours(23, 59, 59, 999);
                matchesTime = evDate >= saturday && evDate <= sunday;
            }
        }

        let matchesMonth = true;
        if (!currentTimeFilter && currentMonth !== 'all') {
            const eventDate = parseLocalDate(event.start_date);
            const eventMonthYear = `${eventDate.getFullYear()}-${String(eventDate.getMonth() + 1).padStart(2, '0')}`;
            matchesMonth = eventMonthYear === currentMonth;
        }

        let matchesNeighborhood = true;
        if (currentNeighborhood !== 'all') {
            const keywords = NEIGHBORHOOD_KEYWORDS[currentNeighborhood] || [];
            const loc = (event.location || '').toLowerCase();
            matchesNeighborhood = keywords.some(kw => loc.includes(kw));
        }

        return matchesCategory && matchesTime && matchesMonth && matchesNeighborhood;
    });

    updateActiveFiltersBar();
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

        return matchesCategory && matchesMonth && matchesNeighborhood && matchesSearch;
    });

    updateActiveFiltersBar();
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

    // Determine which events to show: next 7 days by default, or all if a filter is active / expanded
    let eventsToShow = filteredEvents;
    let hasMore = false;

    const hasActiveFilter = currentCategory !== 'all' || currentMonth !== 'all' || currentNeighborhood !== 'all';

    if (!showAllEvents && !hasActiveFilter) {
        // Unfiltered view: show only the next 7 days, with a "Load More" button for the rest
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() + 7);
        cutoffDate.setHours(23, 59, 59, 999);

        const firstTwoWeeks = filteredEvents.filter(event => {
            const d = parseLocalDate(event.start_date);
            return d < cutoffDate;
        });

        if (firstTwoWeeks.length < filteredEvents.length) {
            eventsToShow = firstTwoWeeks;
            hasMore = true;
        }
    }

    container.innerHTML = renderGroupedByDay(eventsToShow);

    if (hasMore) {
        const loadMoreWrapper = document.createElement('div');
        loadMoreWrapper.className = 'load-more-wrapper';
        loadMoreWrapper.innerHTML = `<button class="btn load-more-btn" id="loadMoreBtn">Load More Events</button>`;
        container.appendChild(loadMoreWrapper);

        document.getElementById('loadMoreBtn').addEventListener('click', () => {
            showAllEvents = true;
            renderEvents();
        });
    }

    // Attach click listeners to all event rows
    document.querySelectorAll('.event-row').forEach(row => {
        row.addEventListener('click', () => {
            const idx = parseInt(row.dataset.eventIndex);
            if (!isNaN(idx) && filteredEvents[idx]) showEventDetail(filteredEvents[idx]);
        });
    });
}

// Group events by calendar day and render as a clean list
function renderGroupedByDay(events) {
    // Build a map: "YYYY-MM-DD" → [{event, index}, ...]
    const byDay = {};
    const dayOrder = [];

    events.forEach((event) => {
        const d = parseLocalDate(event.start_date);
        const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        if (!byDay[key]) {
            byDay[key] = [];
            dayOrder.push(key);
        }
        // Use the index in filteredEvents so click handlers resolve correctly
        const filteredIndex = filteredEvents.indexOf(event);
        byDay[key].push({ event, index: filteredIndex });
    });

    dayOrder.sort();

    const tKey = todayKey();
    const tomorrowKey = (() => {
        const t = new Date(); t.setDate(t.getDate() + 1);
        return `${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}`;
    })();

    const CAP = 5;

    return dayOrder.map(key => {
        const [year, month, day] = key.split('-').map(Number);
        const d = new Date(year, month - 1, day);
        const weekday = d.toLocaleDateString('en-US', { weekday: 'long' }).toUpperCase();
        const items = byDay[key];
        const isToday = key === tKey;
        const isTomorrow = key === tomorrowKey;

        // Sort events within the day by start time ascending
        items.sort((a, b) => parseLocalDate(a.event.start_date) - parseLocalDate(b.event.start_date));

        const label = isToday ? 'TODAY' : isTomorrow ? 'TOMORROW' : weekday;
        const shortDate = d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });

        const visible = items.slice(0, CAP);
        const extra   = items.slice(CAP);
        const dayId   = `day-${key.replace(/-/g, '')}`;

        const extraHtml = extra.length > 0 ? `
            <div class="day-extra-rows" id="${dayId}-extra" style="max-height:0;opacity:0;">
                ${extra.map(({ event, index }) => createEventRow(event, index)).join('')}
            </div>
            <button class="show-more-btn" id="${dayId}-toggle" onclick="toggleDayExpand(event, '${dayId}', ${extra.length})">
                Show ${extra.length} more ↓
            </button>` : '';

        return `
        <div class="day-group" id="${dayId}">
            <div class="day-header${isToday ? ' today' : ''}">
                <div class="day-header-left">
                    <span class="day-weekday">${label}</span>
                    <span class="day-date">${shortDate}</span>
                </div>
                <span class="day-count">${items.length} event${items.length !== 1 ? 's' : ''}</span>
            </div>
            ${visible.map(({ event, index }) => createEventRow(event, index)).join('')}
            ${extraHtml}
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
    const badgeLabel = BADGE_LABELS[event.category] || (event.category ? event.category.charAt(0).toUpperCase() + event.category.slice(1) : 'Other');
    const location = event.location || '';
    const pinIcon = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`;

    return `
    <div class="event-row" data-event-index="${index}">
        <div class="event-details-col">
            <div class="event-row-top">
                <span class="event-row-title">${escapeHtml(normalizeTitle(event.title))}</span>
                <span class="event-category ${categoryClass}">${badgeLabel}</span>
            </div>
            <div class="event-row-meta">
                ${timeStr ? `<span class="event-row-time">${escapeHtml(timeStr)}</span>` : ''}
                ${location ? `<span class="event-row-location">${pinIcon}<span class="loc-text">${escapeHtml(location)}</span></span>` : ''}
            </div>
        </div>
        <span class="chevron">›</span>
    </div>`;
}

// Toggle per-day expand / collapse
function toggleDayExpand(e, dayId, extraCount) {
    e.stopPropagation();
    const extra = document.getElementById(dayId + '-extra');
    const btn   = document.getElementById(dayId + '-toggle');
    if (!extra || !btn) return;
    const expanded = extra.classList.contains('expanded');

    if (expanded) {
        // Collapse: stagger rows out bottom-to-top, then close container
        const rows = Array.from(extra.querySelectorAll('.event-row'));
        rows.reverse().forEach((row, i) => {
            setTimeout(() => {
                row.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                row.style.opacity = '0';
                row.style.transform = 'translateY(6px)';
            }, i * 50);
        });
        const rowFadeTime = rows.length * 50 + 200;
        setTimeout(() => {
            const currentHeight = extra.scrollHeight;
            extra.style.maxHeight = currentHeight + 'px';
            extra.offsetHeight;
            extra.style.transition = 'max-height 0.5s ease';
            extra.style.maxHeight = '0';
            extra.classList.remove('expanded');
            btn.textContent = `Show ${extraCount} more ↓`;
        }, rowFadeTime);
        setTimeout(() => {
            document.getElementById(dayId)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, rowFadeTime + 520);
    } else {
        // Expand: animate container height, then stagger rows in
        const rows = extra.querySelectorAll('.event-row');
        // Reset row states before expanding
        rows.forEach(row => {
            row.style.opacity = '0';
            row.style.transform = 'translateY(6px)';
            row.style.transition = 'none';
        });

        const targetHeight = extra.scrollHeight;
        extra.style.maxHeight = '0';
        extra.style.opacity = '1';
        extra.offsetHeight; // force reflow
        extra.style.maxHeight = targetHeight + 'px';
        extra.classList.add('expanded');

        // Stagger each row in with a 60ms delay between them
        rows.forEach((row, i) => {
            setTimeout(() => {
                row.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                row.style.opacity = '1';
                row.style.transform = 'translateY(0)';
            }, 80 + i * 60);
        });

        // Clear inline styles after transition so container is ready for next collapse
        setTimeout(() => {
            extra.style.maxHeight = '';
            extra.style.transition = '';
        }, 520);
        btn.textContent = 'Show less ↑';
    }
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
        <h2 class="modal-title" id="eventModalTitle">${escapeHtml(normalizeTitle(event.title))}</h2>

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

    const lastSync = document.getElementById('lastSync');
    if (lastSync) lastSync.textContent = new Date().toLocaleTimeString();
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
                <div class="bookmark-title">${escapeHtml(normalizeTitle(event.title))}</div>
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
                    <div class="bookmark-title">${escapeHtml(normalizeTitle(event.title))}</div>
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
