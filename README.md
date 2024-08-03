Here's a comprehensive README for your conference booking API:

---

# Conference Booking API

## Overview

The Conference Booking API is a RESTful web service built using Flask and SQLite. It allows users to add conferences, register users, book conferences, check booking status, confirm waitlist bookings, and cancel bookings. The API adheres to the ACID principles and handles concurrency effectively to ensure data integrity.

## Features

- **Add Conferences**: Create new conferences with unique names, locations, topics, start and end times, and available slots.
- **Register Users**: Add users with unique IDs and their topics of interest.
- **Book Conferences**: Allow users to book conferences, ensuring no overlapping bookings and handling available slots.
- **Waitlist Management**: Automatically manage waitlists when conferences are fully booked and allow users to confirm waitlist bookings within a specified time frame.
- **Check Booking Status**: Retrieve the status of a booking, including waitlist expiration times.
- **Cancel Bookings**: Cancel confirmed or waitlisted bookings and update available slots accordingly.

## Setup

### Prerequisites

- Python 3.7+
- Flask
- SQLite3

### Installation

1. **Create a Virtual Environment**:
    ```sh
    python -m venv venv
    source venv/bin/activate   # On Windows, use `venv\Scripts\activate`
    ```

2. **Install Dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

3. **Initialize the Database**:
    The database tables will be created automatically when you first run the application.

### Running the Application

1. **Run the Flask Application**:
    ```sh
    flask run
    ```

2. The API will be accessible at `http://127.0.0.1:5000`.

## API Endpoints

### Add Conference

- **Endpoint**: `/add_conference`
- **Method**: `POST`
- **Request Body**:
    ```json
    {
        "name": "Conference Name",
        "location": "Location",
        "topics": "Topic1,Topic2",
        "start_timestamp": "2024-08-01T10:00:00Z",
        "end_timestamp": "2024-08-01T22:00:00Z",
        "available_slots": 100
    }
    ```
- **Response**:
    - `201 Created`: Conference added successfully.
    - `400 Bad Request`: Invalid input or conference name already exists.

### Add User

- **Endpoint**: `/add_user`
- **Method**: `POST`
- **Request Body**:
    ```json
    {
        "user_id": "user123",
        "interested_topics": "Topic1,Topic2"
    }
    ```
- **Response**:
    - `201 Created`: User added successfully.
    - `400 Bad Request`: Invalid input or user ID already exists.

### Book Conference

- **Endpoint**: `/book_conference`
- **Method**: `POST`
- **Request Body**:
    ```json
    {
        "conference_name": "Conference Name",
        "user_id": "user123"
    }
    ```
- **Response**:
    - `201 Created`: Booking successful or added to waitlist.
    - `400 Bad Request`: Invalid input, user or conference does not exist, or overlapping booking.

### Check Booking Status

- **Endpoint**: `/booking_status/<booking_id>`
- **Method**: `GET`
- **Response**:
    - `200 OK`: Returns booking status and waitlist confirmation expiry time if applicable.
    - `404 Not Found`: Booking ID not found.

### Confirm Waitlist Booking

- **Endpoint**: `/confirm_waitlist_booking`
- **Method**: `POST`
- **Request Body**:
    ```json
    {
        "booking_id": "waitlist123"
    }
    ```
- **Response**:
    - `200 OK`: Booking confirmed.
    - `400 Bad Request`: Booking cannot be confirmed or waitlist period expired.

### Cancel Booking

- **Endpoint**: `/cancel_booking`
- **Method**: `POST`
- **Request Body**:
    ```json
    {
        "booking_id": "booking123"
    }
    ```
- **Response**:
    - `200 OK`: Booking canceled successfully.
    - `404 Not Found`: Booking ID not found.

## ACID Compliance and Concurrency

- **Atomicity**: Transactions ensure that all operations within a booking or cancellation process are completed successfully or rolled back on failure.
- **Consistency**: Data validation and constraints ensure the database remains in a consistent state.
- **Isolation**: Concurrency control mechanisms prevent race conditions and ensure isolated transactions.
- **Durability**: Committed transactions are saved in the SQLite database, ensuring data persistence.