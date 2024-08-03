from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import sqlite3
import uuid

app = Flask(__name__)

DATABASE = 'conferences.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    # called before everything else to set up all the tables and make sure everything is set up at the backend
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS conferences (
                    name TEXT PRIMARY KEY,
                    location TEXT,
                    topics TEXT,
                    start_timestamp TEXT,
                    end_timestamp TEXT,
                    available_slots INTEGER)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    interested_topics TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    booking_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    conference_name TEXT,
                    status TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(conference_name) REFERENCES conferences(name))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS waitlists (
                    waitlist_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    conference_name TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(conference_name) REFERENCES conferences(name))''')
    conn.commit()
    conn.close()


with app.app_context():
    create_tables()


def is_overlap(existing_start, existing_end, new_start, new_end):
    return not (existing_end <= new_start or existing_start >= new_end)


def check_valid_string(word):
    for letter in word:
        if not (('a' <= letter <= 'z') or ('A' <= letter <= 'Z') or ('0' <= letter <= '9') or letter == ' '):
            return False
    return True

def check_valid_string_userID(word):
    for letter in word:
        if not (('a' <= letter <= 'z') or ('A' <= letter <= 'Z') or ('0' <= letter <= '9')):
            return False
    return True



def validate_timestamp(timestamp):
    try:
        datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
        return True
    except ValueError:
        return False

@app.route('/add_conference', methods=['POST'])
def add_conference():
    data = request.form
    all_topics = data['topics'].split(',')
    
    if not check_valid_string(data['name']) or not check_valid_string(data['location']):
        return jsonify({"error": "No other characters except alphanumeric characters and spaces are allowed for name, location."}), 400
    
    for topic in all_topics:
        if not check_valid_string(topic):
            return jsonify({"error": "No other characters except alphanumeric characters and spaces are allowed for topics."}), 400

    if len(all_topics) > 10:
        return jsonify({"error": "You are allowed to mention only up to 10 topics!"}), 400

    name = data['name']
    location = data['location']
    topics = data['topics']
    start_timestamp = data['start_timestamp']
    end_timestamp = data['end_timestamp']

    # Validate timestamp format
    if not validate_timestamp(start_timestamp) or not validate_timestamp(end_timestamp):
        return jsonify({"error": "Timestamp format is incorrect. Use 'YYYY-MM-DDTHH:MM:SSZ' format."}), 400

    try:
        start_timestamp = datetime.strptime(start_timestamp, '%Y-%m-%dT%H:%M:%SZ')
        end_timestamp = datetime.strptime(end_timestamp, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        return jsonify({"error": "Timestamp format is incorrect. Use 'YYYY-MM-DDTHH:MM:SSZ' format."}), 400

    try:
        available_slots = int(data['available_slots'])
    except ValueError:
        return jsonify({"error": "Available slots should be an integer."}), 400

    if available_slots <= 0:
        return jsonify({"error": "Available slots should be greater than 0."}), 400

    # Check if the time constraints are satisfied
    if start_timestamp >= end_timestamp or (end_timestamp - start_timestamp).total_seconds() > 43200:
        return jsonify({"error": "Invalid timing"}), 400

    try:
        conn = get_db_connection()
        conn.execute('''INSERT INTO conferences 
                        (name, location, topics, start_timestamp, end_timestamp, available_slots) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (name, location, topics, start_timestamp.isoformat(), end_timestamp.isoformat(), available_slots))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Conference name must be unique"}), 400
    
    finally:
        conn.close()
    return jsonify({"message": "Conference added successfully"}), 201



@app.route('/add_user', methods=['POST'])
def add_user():
    # adds a user to the database checking all the constraints being satisfied
    data = request.form
    
    user_id = data['user_id']
    interested_topics = data['interested_topics']

    if not check_valid_string_userID(user_id):
        return jsonify({"error": "No other characters except alphanumeric characters for userID."}), 400
    
    
    all_topics = data['interested_topics'].split(',')

    if len(all_topics) > 50:
        return jsonify({"error": "Maximum of 50 interested topics allowed."}), 400
    for topic in all_topics:
        if not check_valid_string(topic):
            return jsonify(
                {"error": "No other characters except alphanumeric characters and spaces are allowed for "
                          "topics."}), 400

    try:
        conn = get_db_connection()
        conn.execute('''INSERT INTO users (user_id, interested_topics) VALUES (?, ?)''',
                     (user_id, interested_topics))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "UserID must be unique"}), 400
    finally:
        conn.close()
    return jsonify({"message": "User added successfully"}), 201


@app.route('/book_conference', methods=['POST'])
def book_conference():
    data = request.form
    conference_name = data['conference_name']
    user_id = data['user_id']

    conn = get_db_connection()
    conference = conn.execute('SELECT * FROM conferences WHERE name = ?', (conference_name,)).fetchone()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

    if not conference or not user:
        conn.close()
        return jsonify({"error": "Conference or User does not exist"}), 400

    existing_booking = conn.execute('SELECT * FROM bookings WHERE user_id = ? AND conference_name = ?', 
                                   (user_id, conference_name)).fetchone()
    
    if existing_booking:
        conn.close()
        return jsonify({"error": "User has already booked this conference.", "booking_id": existing_booking['booking_id']}), 400
    
    user_bookings = conn.execute('SELECT * FROM bookings WHERE user_id = ?', (user_id,)).fetchall()
    for booking in user_bookings:
        booked_conf = conn.execute('SELECT * FROM conferences WHERE name = ?', (booking['conference_name'],)).fetchone()
        if is_overlap(datetime.fromisoformat(booked_conf['start_timestamp']),
                      datetime.fromisoformat(booked_conf['end_timestamp']),
                      datetime.fromisoformat(conference['start_timestamp']),
                      datetime.fromisoformat(conference['end_timestamp'])):
            conn.close()
            return jsonify({"error": "User has overlapping conference booked"}), 400

    try:
        conn.execute('BEGIN TRANSACTION')
        
        # Promote users from waitlist if slots are available
        while conference['available_slots'] > 0:
            waitlist_entry = conn.execute('''SELECT * FROM waitlists WHERE conference_name = ? 
                                            ORDER BY timestamp ASC LIMIT 1''',
                                          (conference_name,)).fetchone()
            if not waitlist_entry:
                break  # No more users in waitlist

            waitlist_id = waitlist_entry['waitlist_id']
            conn.execute('UPDATE conferences SET available_slots = available_slots - 1 WHERE name = ?',
                         (conference_name,))
            conn.execute('DELETE FROM waitlists WHERE waitlist_id = ?', (waitlist_id,))
            conn.execute('UPDATE bookings SET status = ? WHERE booking_id = ?', ('confirmed', waitlist_id))
            conference = conn.execute('SELECT * FROM conferences WHERE name = ?', (conference_name,)).fetchone()

        # Book the conference for the user or add to waitlist
        if conference['available_slots'] > 0:
            booking_id = str(uuid.uuid4())
            conn.execute('UPDATE conferences SET available_slots = available_slots - 1 WHERE name = ?',
                         (conference_name,))
            conn.execute('''INSERT INTO bookings (booking_id, user_id, conference_name, status) 
                            VALUES (?, ?, ?, ?)''', (booking_id, user_id, conference_name, 'confirmed'))
            conn.commit()
            conn.close()
            return jsonify({"message": "Booking successful", "booking_id": booking_id}), 201
        else:
            waitlist_id = str(uuid.uuid4())
            conn.execute('''INSERT INTO waitlists (waitlist_id, user_id, conference_name, timestamp)
                            VALUES (?, ?, ?, ?)''',
                         (waitlist_id, user_id, conference_name, datetime.now(timezone.utc).isoformat()))
            conn.execute('''INSERT INTO bookings (booking_id, user_id, conference_name, status) 
                            VALUES (?, ?, ?, ?)''', (waitlist_id, user_id, conference_name, 'waitlisted'))
            conn.commit()
            conn.close()
            return jsonify({"message": "Added to waitlist", "waitlist_id": waitlist_id}), 201
    except sqlite3.Error:
        conn.rollback()
        conn.close()
        return jsonify({"error": "Booking failed due to a database error"}), 500


@app.route('/booking_status/<booking_id>', methods=['GET'])
def booking_status(booking_id):
    # gets the booking status for a users booking and return the status to the user
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE booking_id = ?', (booking_id,)).fetchone()

    if booking:
        status = booking['status']
        if status == 'waitlisted':
            waitlist_entry = conn.execute('SELECT * FROM waitlists WHERE waitlist_id = ?', (booking_id,)).fetchone()
            can_confirm_until = datetime.fromisoformat(waitlist_entry['timestamp']) + timedelta(hours=1)
            if datetime.now(timezone.utc) < can_confirm_until:
                conn.close()
                return jsonify({"status": status, "can_confirm_until": can_confirm_until.isoformat() + 'Z'}), 200
            else:
                conn.close()
                return jsonify({"status": status, "can_confirm_until": "Expired"}), 200
        conn.close()
        return jsonify({"status": status}), 200
    conn.close()
    return jsonify({"error": "Booking ID not found"}), 404


@app.route('/confirm_waitlist_booking/<booking_id>', methods=['POST'])
def confirm_waitlist_booking(booking_id):
    #  to confirm a waitlisted booking like if it can be confirmed we check and update the status accordingly
    conn = get_db_connection()
    waitlist_entry = conn.execute('SELECT * FROM waitlists WHERE waitlist_id = ?', (booking_id,)).fetchone()
    if(waitlist_entry):
        if (datetime.now(timezone.utc) < datetime.fromisoformat(waitlist_entry['timestamp']) +
                timedelta(hours=1)):
            conference_name = waitlist_entry['conference_name']
            conference = conn.execute('SELECT * FROM conferences WHERE name = ?', (conference_name,)).fetchone()
            if conference['available_slots'] > 0:
                try:
                    conn.execute('BEGIN TRANSACTION')
                    conn.execute('UPDATE conferences SET available_slots = available_slots - 1 WHERE name = ?',
                                (conference_name,))
                    conn.execute('DELETE FROM waitlists WHERE waitlist_id = ?', (booking_id,))
                    conn.execute('UPDATE bookings SET status = ? WHERE booking_id = ?', ('confirmed', booking_id))
                    conn.commit()
                    conn.close()
                    return jsonify({"message": "Booking confirmed"}), 200
                except sqlite3.Error:
                    conn.rollback()
                    conn.close()
                    return jsonify({"error": "Booking confirmation failed due to a database error"}), 500
        conn.close()
        return jsonify({"error": "Booking cannot be confirmed"}), 400
    else:
        conn.close()
        return jsonify({"error": "Booking ID not found in waitlist"}), 404

@app.route('/cancel_booking/<booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE booking_id = ?', (booking_id,)).fetchone()

    if booking:
        try:
            conn.execute('BEGIN TRANSACTION')
            if booking['status'] == 'confirmed':
                conference_name = booking['conference_name']
                conn.execute('UPDATE conferences SET available_slots = available_slots + 1 WHERE name = ?',
                             (conference_name,))
                conn.execute('DELETE FROM bookings WHERE booking_id = ?', (booking_id,))
            elif booking['status'] == 'waitlisted':
                conn.execute('DELETE FROM waitlists WHERE waitlist_id = ?', (booking_id,))
            conn.execute('UPDATE bookings SET status = ? WHERE booking_id = ?', ('canceled', booking_id))
            conn.commit()
            conn.close()
            return jsonify({"message": "Booking canceled"}), 200
        except sqlite3.Error:
            conn.rollback()
            conn.close()
            return jsonify({"error": "Booking cancellation failed due to a database error"}), 500
    conn.close()
    return jsonify({"error": "Booking ID not found"}), 404


if __name__ == '__main__':
    app.run(debug=True)
