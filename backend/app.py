"""
Flask API for Philadelphia Calendar
Serves scraped events to iOS app
"""

from flask import Flask, jsonify, request, send_from_directory, render_template, session
from flask_cors import CORS
from database import EventDatabase
from scrapers import SCRAPERS
import logging
from datetime import datetime
from functools import wraps
import os
import threading
import requests as _requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_security_headers(response):
    """Add security headers to every response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Cache static assets; don't cache API responses
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    elif request.path.startswith('/events') or request.path.startswith('/stats'):
        response.headers['Cache-Control'] = 'no-store'
    return response

def require_admin(f):
    """Decorator that checks X-Admin-Token header against ADMIN_TOKEN env var."""
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_token = os.environ.get('ADMIN_TOKEN', '')
        if not admin_token:
            return jsonify({'success': False, 'error': 'Admin access is not configured'}), 403
        if request.headers.get('X-Admin-Token', '') != admin_token:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


app = Flask(__name__, static_folder='static', static_url_path='/static')

# CORS: allow requests from same origin (browser) and the Render deployment
_ALLOWED_ORIGINS = os.environ.get(
    'ALLOWED_ORIGINS',
    'https://phillycalendar.onrender.com'
).split(',')
CORS(app, origins=_ALLOWED_ORIGINS, supports_credentials=True)

# Session config — required for OTP user auth
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'philly-dev-secret-change-in-prod')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER_EXTERNAL_URL', '').startswith('https')

app.after_request(add_security_headers)

# Initialize database - uses PostgreSQL if DATABASE_URL is set, otherwise SQLite
use_cloud = bool(os.environ.get('DATABASE_URL'))
db = EventDatabase(use_postgres=use_cloud)
if use_cloud:
    logger.info("Using cloud PostgreSQL database")
else:
    logger.info("Using local SQLite database (set DATABASE_URL to use cloud)")


# ================================================================
# AUTH HELPERS
# ================================================================

def get_current_user():
    """Return user dict from session, or None if not logged in."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.get_user_by_id(user_id)


def require_login(f):
    """Decorator: returns 401 if user is not logged in via session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
        return f(*args, **kwargs)
    return decorated


def send_otp_email(to_email: str, code: str) -> bool:
    """Send a 6-digit OTP code to the given email via SMTP. Returns True on success."""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    host     = os.environ.get('MAIL_HOST', 'smtp.gmail.com')
    port     = int(os.environ.get('MAIL_PORT', '587'))
    user     = os.environ.get('MAIL_USER', '').strip()
    password = os.environ.get('MAIL_PASS', '').strip().replace(' ', '')  # strip spaces from Gmail app password
    from_addr = os.environ.get('MAIL_FROM', user).strip()

    if not user or not password:
        logger.warning('MAIL_USER / MAIL_PASS not configured — OTP email not sent')
        return False

    plain = (
        f"Hi there!\n\n"
        f"Your Philly Events Calendar login code is:\n\n"
        f"    {code}\n\n"
        f"This code expires in 10 minutes. If you didn't request this, ignore this email.\n\n"
        f"— Philly Events Calendar\nhttps://phillycalendar.onrender.com"
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
      <h2 style="color:#004C54;">&#x1F514; Philly Events Calendar</h2>
      <p style="color:#333;">Your one-time login code:</p>
      <div style="font-size:38px;font-weight:900;letter-spacing:10px;color:#004C54;
                  background:#e6f4f5;padding:20px;border-radius:12px;text-align:center;
                  margin:20px 0;">{code}</div>
      <p style="color:#888;font-size:13px;">Expires in 10 minutes.<br>
         If you didn't request this, you can safely ignore this email.</p>
    </div>
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"{code} — Your Philly Events login code"
    msg['From']    = f"Philly Events Calendar <{from_addr}>"
    msg['To']      = to_email
    msg.attach(MIMEText(plain, 'plain'))
    msg.attach(MIMEText(html,  'html'))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as smtp:  # 10s timeout prevents gunicorn worker kill
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(user, password)
            smtp.sendmail(from_addr, to_email, msg.as_string())
        logger.info(f'OTP email sent to {to_email}')
        return True
    except Exception as e:
        logger.error(f'Failed to send OTP email to {to_email}: {e}', exc_info=True)
        return False


def _start_scheduler():
    """Start APScheduler for 4-hour auto-scraping and keep-alive pings."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler(daemon=True)

    # Auto-scrape every 4 hours
    scheduler.add_job(
        func=run_scrape_job,
        trigger=IntervalTrigger(hours=4),
        id='auto_scrape',
        name='Auto-scrape Philadelphia Events',
        replace_existing=True
    )

    # Cleanup old events daily at 3 AM
    scheduler.add_job(
        func=lambda: db.delete_old_events(days_old=30),
        trigger=CronTrigger(hour=3, minute=0),
        id='cleanup_old_events',
        name='Cleanup Old Events',
        replace_existing=True
    )

    # Cleanup expired OTP tokens nightly at 3:30 AM
    scheduler.add_job(
        func=db.cleanup_expired_otps,
        trigger=CronTrigger(hour=3, minute=30),
        id='cleanup_otps',
        name='Cleanup Expired OTPs',
        replace_existing=True
    )

    # Keep-alive ping every 14 minutes to prevent Render free-tier spin-down
    _self_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if _self_url:
        def _ping():
            try:
                _requests.get(f'{_self_url}/health', timeout=10)
                logger.debug('Keep-alive ping sent.')
            except Exception as e:
                logger.warning(f'Keep-alive ping failed: {e}')

        scheduler.add_job(
            func=_ping,
            trigger=IntervalTrigger(minutes=14),
            id='keep_alive',
            name='Keep-Alive Ping',
            replace_existing=True
        )
        logger.info(f'Keep-alive pings enabled → {_self_url}/health every 14 min')
    else:
        logger.info('RENDER_EXTERNAL_URL not set — keep-alive pings disabled (local dev)')

    scheduler.start()
    logger.info('Scheduler started: auto-scrape every 4 h, cleanup daily at 3 AM')


@app.route('/')
def home():
    """Serve the web calendar"""
    return send_from_directory('static', 'index.html')


@app.route('/api')
def api_info():
    """API information page"""
    return jsonify({
        'message': 'Philadelphia Events Calendar API',
        'version': '1.0',
        'endpoints': {
            '/events': 'Get all events',
            '/events/upcoming': 'Get upcoming events',
            '/events/category/<category>': 'Get events by category',
            '/events/search?q=<query>': 'Search events',
            '/scrape': 'Trigger manual scraping',
            '/stats': 'Get database statistics'
        }
    })


@app.route('/events', methods=['GET'])
def get_events():
    """Get all events"""
    try:
        events = db.get_all_events()
        return jsonify({
            'success': True,
            'count': len(events),
            'events': events
        })
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/events/upcoming', methods=['GET'])
def get_upcoming_events():
    """Get upcoming events only"""
    try:
        limit = request.args.get('limit', type=int)
        events = db.get_upcoming_events(limit=limit)
        return jsonify({
            'success': True,
            'count': len(events),
            'events': events
        })
    except Exception as e:
        logger.error(f"Error getting upcoming events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/events/category/<category>', methods=['GET'])
def get_events_by_category(category):
    """Get events filtered by category"""
    try:
        events = db.get_events_by_category(category)
        return jsonify({
            'success': True,
            'category': category,
            'count': len(events),
            'events': events
        })
    except Exception as e:
        logger.error(f"Error getting events by category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/events/search', methods=['GET'])
def search_events():
    """Search events"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'success': False, 'error': 'Query parameter required'}), 400

        events = db.search_events(query)
        return jsonify({
            'success': True,
            'query': query,
            'count': len(events),
            'events': events
        })
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def run_scrape_job():
    """Run all scrapers in the background and store results."""
    logger.info("Background scrape job started...")
    total_scraped = 0
    for ScraperClass in SCRAPERS:
        try:
            scraper = ScraperClass()
            events = scraper.scrape()
            added = db.add_events_batch(events)
            total_scraped += added
            logger.info(f"[scrape] {scraper.source_name}: {len(events)} scraped, {added} added")
        except Exception as e:
            logger.error(f"[scrape] Error with {ScraperClass.__name__}: {e}")
    logger.info(f"Background scrape job done — {total_scraped} new events added.")


@app.route('/scrape', methods=['POST'])
def scrape_events():
    """Trigger event scraping in the background (returns 202 immediately).
    Requires the SCRAPE_TOKEN env variable to be set and matched in the
    X-Scrape-Token request header or 'token' query param.
    """
    scrape_token = os.environ.get('SCRAPE_TOKEN', '')
    if not scrape_token:
        return jsonify({'success': False, 'error': 'Scraping is not configured'}), 403
    provided = request.headers.get('X-Scrape-Token', '') or request.args.get('token', '')
    if provided != scrape_token:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    t = threading.Thread(target=run_scrape_job, daemon=True)
    t.start()
    return jsonify({
        'success': True,
        'message': 'Scrape started in background — check server logs for progress.',
        'timestamp': datetime.now().isoformat()
    }), 202


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    try:
        stats = db.get_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


# Event Management Endpoints
@app.route('/events', methods=['POST'])
@require_admin
def add_event():
    """Add a new event manually"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['title', 'start_date', 'location', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        event_id = db.add_event(
            title=data['title'],
            description=data.get('description', ''),
            start_date=data['start_date'],
            end_date=data.get('end_date'),
            location=data['location'],
            category=data['category'],
            price=data.get('price'),
            source=data.get('source', 'User Added'),
            source_url=data.get('source_url'),
            registration_deadline=data.get('registration_deadline'),
            is_user_added=1
        )

        return jsonify({
            'success': True,
            'event_id': event_id,
            'message': 'Event added successfully'
        }), 201

    except Exception as e:
        logger.error(f"Error adding event: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/events/<int:event_id>', methods=['PUT'])
@require_admin
def update_event(event_id):
    """Update an existing event"""
    try:
        data = request.get_json()

        success = db.update_event(event_id, data)

        if success:
            return jsonify({
                'success': True,
                'message': 'Event updated successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Event not found'}), 404

    except Exception as e:
        logger.error(f"Error updating event: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/events/<int:event_id>', methods=['DELETE'])
@require_admin
def delete_event(event_id):
    """Delete an event"""
    try:
        success = db.delete_event(event_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'Event deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Event not found'}), 404

    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Bookmark Endpoints (DEPRECATED: bookmarks are now stored in client localStorage)
@app.route('/bookmarks', methods=['GET'])
def get_bookmarks():
    """Get all bookmarked events"""
    try:
        bookmarks = db.get_bookmarks()
        return jsonify({
            'success': True,
            'count': len(bookmarks),
            'bookmarks': bookmarks
        })
    except Exception as e:
        logger.error(f"Error getting bookmarks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/bookmarks', methods=['POST'])
def add_bookmark():
    """Add event to bookmarks"""
    try:
        data = request.get_json()
        event_id = data.get('event_id')

        if not event_id:
            return jsonify({'success': False, 'error': 'event_id required'}), 400

        bookmark_id = db.add_bookmark(
            event_id=event_id,
            notify_registration=data.get('notify_registration', 1),
            notify_day_before=data.get('notify_day_before', 1),
            notify_3hours_before=data.get('notify_3hours_before', 1)
        )

        return jsonify({
            'success': True,
            'bookmark_id': bookmark_id,
            'message': 'Event bookmarked successfully'
        }), 201

    except Exception as e:
        logger.error(f"Error adding bookmark: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/bookmarks/<int:event_id>', methods=['DELETE'])
def remove_bookmark(event_id):
    """Remove event from bookmarks"""
    try:
        success = db.remove_bookmark(event_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'Bookmark removed successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Bookmark not found'}), 404

    except Exception as e:
        logger.error(f"Error removing bookmark: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/notifications/settings', methods=['GET', 'PUT'])
def notification_settings():
    """Get or update notification settings"""
    try:
        if request.method == 'GET':
            settings = db.get_notification_settings()
            return jsonify({
                'success': True,
                'settings': settings
            })
        else:  # PUT
            data = request.get_json()
            success = db.update_notification_settings(data)

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Settings updated successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Update failed'}), 500

    except Exception as e:
        logger.error(f"Error with notification settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# AUTH ROUTES — Email + OTP
# ================================================================

@app.route('/auth/send-otp', methods=['POST'])
def send_otp():
    """Step 1: Send a 6-digit OTP to the given email address."""
    import random
    import re
    from datetime import timedelta

    try:
        data  = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()

        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return jsonify({'success': False, 'error': 'Invalid email address'}), 400

        code       = f"{random.randint(0, 999999):06d}"
        # Use datetime object for Postgres TIMESTAMP compatibility
        expires_at = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

        try:
            db.create_otp(email, code, expires_at)
        except Exception as e:
            logger.error(f'create_otp failed: {e}', exc_info=True)
            return jsonify({'success': False, 'error': f'Could not create OTP: {str(e)}'}), 500

        sent = send_otp_email(email, code)
        if not sent:
            # Dev fallback: log the code so it's testable without email configured
            logger.info(f'[DEV] OTP for {email}: {code}')

        return jsonify({'success': True, 'message': 'Code sent! Check your email.'})

    except Exception as e:
        logger.error(f'send_otp unexpected error: {e}', exc_info=True)
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/auth/verify-otp', methods=['POST'])
def verify_otp():
    """Step 2: Verify the OTP and create a session."""
    data  = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    code  = (data.get('code')  or '').strip()

    if not email or not code:
        return jsonify({'success': False, 'error': 'Email and code are required'}), 400

    if not db.verify_otp(email, code):
        return jsonify({'success': False, 'error': 'Invalid or expired code. Please try again.'}), 401

    try:
        user = db.get_or_create_user(email)
    except Exception as e:
        logger.error(f'get_or_create_user failed: {e}')
        return jsonify({'success': False, 'error': 'Could not create user'}), 500

    session['user_id'] = user['id']
    session.permanent  = False  # Expires when browser closes

    return jsonify({
        'success': True,
        'user': {
            'id':           user['id'],
            'email':        user['email'],
            'display_name': user.get('display_name') or user['email'].split('@')[0],
        }
    })


@app.route('/auth/logout', methods=['POST'])
def logout():
    """Log out the current user."""
    session.clear()
    return jsonify({'success': True})


@app.route('/auth/db-test', methods=['GET'])
def auth_db_test():
    """Temporary debug: test if otp_tokens table exists and is writable."""
    try:
        from datetime import timedelta
        code = '000000'
        expires_at = (datetime.now() + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        db.create_otp('debug@test.com', code, expires_at)
        return jsonify({'success': True, 'message': 'otp_tokens table OK', 'use_postgres': db.use_postgres})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'use_postgres': db.use_postgres}), 500


@app.route('/auth/smtp-test', methods=['GET'])
def smtp_test():
    """Temporary debug: test SMTP connection and report exact error."""
    import smtplib, ssl, os
    host     = os.environ.get('MAIL_HOST', 'smtp.gmail.com')
    port     = int(os.environ.get('MAIL_PORT', '587'))
    user     = os.environ.get('MAIL_USER', '').strip()
    password = os.environ.get('MAIL_PASS', '').strip().replace(' ', '')
    from_addr = os.environ.get('MAIL_FROM', user).strip()
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(user, password)
        return jsonify({
            'success': True,
            'message': 'SMTP login OK',
            'user': user,
            'from': from_addr,
            'password_length': len(password)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'user': user,
            'from': from_addr,
            'password_length': len(password)
        }), 500


@app.route('/auth/me', methods=['GET'])
def auth_me():
    """Return current user info, or logged_in: false."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'logged_in': False})
    user = db.get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user': {
            'id':           user['id'],
            'email':        user['email'],
            'display_name': user.get('display_name') or user['email'].split('@')[0],
        }
    })


# ================================================================
# PROFILE / SAVES ROUTES
# ================================================================

@app.route('/profile/saves', methods=['GET'])
def get_saves():
    """Get all saved events for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    try:
        events   = db.get_user_saves(user_id)
        event_ids = db.get_user_save_ids(user_id)
        return jsonify({'success': True, 'events': events, 'event_ids': event_ids})
    except Exception as e:
        logger.error(f'get_saves error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/profile/saves', methods=['POST'])
def add_save():
    """Save an event for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data     = request.get_json() or {}
    event_id = data.get('event_id')
    if not event_id:
        return jsonify({'success': False, 'error': 'event_id required'}), 400
    success = db.save_event(user_id, int(event_id))
    return jsonify({'success': success})


@app.route('/profile/saves/<int:event_id>', methods=['DELETE'])
def remove_save(event_id):
    """Unsave an event for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    success = db.unsave_event(user_id, event_id)
    return jsonify({'success': success})


@app.route('/profile/me', methods=['PATCH'])
def update_profile():
    """Update display name for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data         = request.get_json() or {}
    display_name = (data.get('display_name') or '').strip()
    if not display_name:
        return jsonify({'success': False, 'error': 'display_name required'}), 400
    success = db.update_user_display_name(user_id, display_name)
    return jsonify({'success': success})


# Start scheduler after all functions are defined
# Guard prevents duplicate start in Flask debug reloader; gunicorn doesn't set this var
if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    _start_scheduler()


if __name__ == '__main__':
    # Run the Flask app
    logger.info("Starting Philadelphia Events Calendar API...")
    logger.info("API will be available at http://localhost:5000")

    stats = db.get_stats()
    logger.info(f"Database ready: {stats.get('total_events', 0)} events ({stats.get('upcoming_events', 0)} upcoming)")
    logger.info("Use POST /scrape to fetch fresh events from Eventbrite and Do215")

    # Start Flask server (local development only — Render uses gunicorn)
    app.run(debug=False, host='0.0.0.0', port=5000)
