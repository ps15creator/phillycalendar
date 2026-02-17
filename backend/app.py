"""
Flask API for Philadelphia Calendar
Serves scraped events to iOS app
"""

from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from database import EventDatabase
from scrapers import SCRAPERS
import logging
from datetime import datetime
import os
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)  # Allow iOS app to access API

# Initialize database - uses PostgreSQL if DATABASE_URL is set, otherwise SQLite
use_cloud = bool(os.environ.get('DATABASE_URL'))
db = EventDatabase(use_postgres=use_cloud)
if use_cloud:
    logger.info("Using cloud PostgreSQL database")
else:
    logger.info("Using local SQLite database (set DATABASE_URL to use cloud)")


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
    """Trigger event scraping in the background (returns 202 immediately)."""
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


# Bookmark Endpoints
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


if __name__ == '__main__':
    # Run the Flask app
    logger.info("Starting Philadelphia Events Calendar API...")
    logger.info("API will be available at http://localhost:5000")

    stats = db.get_stats()
    logger.info(f"Database ready: {stats.get('total_events', 0)} events ({stats.get('upcoming_events', 0)} upcoming)")
    logger.info("Use POST /scrape to fetch fresh events from Eventbrite and Do215")

    # Start Flask server
    app.run(debug=True, host='0.0.0.0', port=5000)
