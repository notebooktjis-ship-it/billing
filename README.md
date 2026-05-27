# SNB Hotel Billing System

A complete hotel management and billing software designed for a 12-room hotel.

## Features

- **Room Management**: 12 predefined rooms with 3 types (Standard, Deluxe, Suite)
- **Customer Management**: Profile storage, ID proof upload, guest history
- **Check-in/Check-out**: Quick entry, auto room assignment, stay duration calculation
- **Payment Module**: Cash/UPI/Card support, partial payments, payment history
- **Billing**: Auto bill generation with GST calculation, discount handling, extra charges
- **PDF Invoice**: Professional invoice design with hotel logo
- **Reports**: Revenue, occupancy, expense reports with export options
- **Staff Management**: Admin/Receptionist roles with activity tracking
- **Expense Management**: Track expenses, profit calculation

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Database**: SQLite (default) / PostgreSQL (Neon DB)
- **PDF Generation**: ReportLab

## Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open browser: http://localhost:5000

## Default Login

- **Username**: admin
- **Password**: admin123

## Project Structure

```
shreegovind/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── SPEC.md            # Specification document
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   ├── uploads/       # ID proof uploads
│   └── logo.png       # Hotel logo
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── rooms.html
│   ├── customers.html
│   ├── bookings.html
│   ├── checkout.html
│   ├── payments.html
│   ├── expenses.html
│   ├── reports.html
│   ├── staff.html
│   ├── settings.html
│   ├── invoice.html
│   └── partials/
│       ├── sidebar.html
│       └── topnav.html
└── instance/
    └── snb_hotel.db   # SQLite database
```

## Room Configuration

| Room Type | Price/Night | Rooms |
|-----------|-------------|-------|
| Standard  | Rs. 1,500   | 101-104 |
| Deluxe    | Rs. 2,500   | 105-108 |
| Suite     | Rs. 4,000   | 109-112 |

## Room Status

- **Available**: Room is ready for booking
- **Occupied**: Currently booked by a guest
- **Cleaning**: Checked out, being cleaned
- **Maintenance**: Under maintenance

## GST & Billing

- GST Rate: 12%
- Auto-calculation on final bill
- Discount support
- Extra charges: Food, Laundry, Late Checkout, Extra Person

## Database Setup (PostgreSQL/Neon DB)

Set the DATABASE_URL environment variable:
```bash
export DATABASE_URL="postgresql://user:password@host:5432/database"
```

## License

This project is proprietary software for SNB Hotel.
