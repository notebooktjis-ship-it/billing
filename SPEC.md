# SNB Hotel Billing System - Specification

## 1. Project Overview

**Project Name:** SNB Hotel Billing System  
**Type:** Full-stack Hotel Management & Billing Software  
**Target:** 12-room hotel management with professional billing

### Tech Stack
- **Backend:** Flask (Python)
- **Frontend:** HTML5, Bootstrap 5, JavaScript (Vanilla)
- **Database:** Neon DB (PostgreSQL)
- **Authentication:** Flask-Bcrypt
- **PDF Generation:** ReportLab
- **Export:** Pandas for Excel

---

## 2. Database Schema

### Tables

#### `staff`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| username | VARCHAR(50) UNIQUE | Login username |
| password_hash | VARCHAR(255) | Bcrypt hashed password |
| name | VARCHAR(100) | Full name |
| role | VARCHAR(20) | 'admin' or 'receptionist' |
| is_active | BOOLEAN | Account status |
| created_at | TIMESTAMP | Creation time |
| last_login | TIMESTAMP | Last login time |

#### `rooms`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| room_number | VARCHAR(10) UNIQUE | Room number (101-112) |
| room_type | VARCHAR(30) | 'standard', 'deluxe', 'suite' |
| price_per_night | DECIMAL(10,2) | Base price |
| status | VARCHAR(20) | 'available', 'occupied', 'cleaning', 'maintenance' |
| floor | INTEGER | Floor number |
| amenities | TEXT | JSON array of amenities |
| created_at | TIMESTAMP | Creation time |

#### `customers`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| name | VARCHAR(100) | Guest full name |
| email | VARCHAR(100) | Email address |
| phone | VARCHAR(20) | Phone number |
| age | INTEGER | Guest age |
| address | TEXT | Full address |
| id_proof_type | VARCHAR(20) | Aadhar/Voter ID/Driving License |
| id_proof_number | VARCHAR(50) | ID proof number |
| id_proof_file | VARCHAR(255) | Uploaded file path |
| total_stays | INTEGER | Number of previous stays |
| created_at | TIMESTAMP | First visit date |

#### `accompanying_persons`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| customer_id | INTEGER FK | Reference to customers |
| name | VARCHAR(100) | Person's name |
| phone | VARCHAR(20) | Phone number |
| age | INTEGER | Person's age |
| id_proof_type | VARCHAR(20) | Aadhar/Voter ID/Driving License |
| id_proof_number | VARCHAR(50) | ID proof number |
| booking_id | INTEGER FK | Reference to bookings (nullable) |
| created_at | TIMESTAMP | Creation time |

#### `bookings`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| booking_id | VARCHAR(20) UNIQUE | BK-YYYYMMDD-XXXX |
| customer_id | INTEGER FK | Reference to customers |
| room_id | INTEGER FK | Reference to rooms |
| check_in | TIMESTAMP | Check-in datetime |
| check_out | TIMESTAMP | Expected check-out |
| actual_check_out | TIMESTAMP | Actual check-out time |
| stay_duration | INTEGER | Number of nights |
| number_of_persons | INTEGER | Total persons in room |
| gst_mode | VARCHAR(20) | 'exclude' (add GST) or 'include' (deduct GST) |
| room_charge | DECIMAL(10,3) | Base room charges |
| extra_person_charges | DECIMAL(10,3) | Extra person charges |
| extra_charges | DECIMAL(10,3) | Food, laundry, etc. |
| discount | DECIMAL(10,3) | Discount amount |
| subtotal | DECIMAL(10,3) | Before GST |
| gst_rate | DECIMAL(5,3) | GST percentage (5%) |
| gst_amount | DECIMAL(10,3) | GST amount (CGST + SGST) |
| total_amount | DECIMAL(10,3) | Final total |
| advance_amount | DECIMAL(10,3) | Advance paid |
| pending_amount | DECIMAL(10,3) | Amount pending |
| status | VARCHAR(20) | 'checked_in', 'checked_out', 'cancelled' |
| checked_in_by | INTEGER FK | Staff who checked in |
| checked_out_by | INTEGER FK | Staff who checked out |
| billing_name | VARCHAR(200) | Company/Individual name for billing |
| company_gst | VARCHAR(20) | Company GST number |
| company_address | TEXT | Company billing address |
| bill_payer_type | VARCHAR(20) | 'guest' or 'company' |
| payer_name | VARCHAR(200) | Person/Company paying the bill |
| payer_phone | VARCHAR(20) | Payer phone number |
| payer_address | TEXT | Payer address |
| notes | TEXT | Special notes |
| created_at | TIMESTAMP | Booking time |

#### `payments`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| booking_id | INTEGER FK | Reference to bookings |
| amount | DECIMAL(10,2) | Payment amount |
| payment_method | VARCHAR(20) | 'cash', 'upi', 'card' |
| payment_status | VARCHAR(20) | 'pending', 'completed', 'refunded' |
| transaction_id | VARCHAR(50) | UPI/Card transaction ID |
| received_by | INTEGER FK | Staff who received |
| created_at | TIMESTAMP | Payment time |

#### `extra_charges`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| booking_id | INTEGER FK | Reference to bookings |
| charge_type | VARCHAR(50) | 'food', 'laundry', 'late_checkout', 'extra_person', 'other' |
| description | VARCHAR(200) | Charge description |
| quantity | INTEGER | Item quantity |
| amount | DECIMAL(10,3) | Charge amount (total = unit_price * quantity) |
| created_at | TIMESTAMP | Charge time |
| created_by | INTEGER FK | Staff who added |

#### `invoices`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| invoice_number | VARCHAR(20) UNIQUE | INV-YYYYMMDD-XXXX |
| booking_id | INTEGER FK | Reference to bookings |
| generated_at | TIMESTAMP | Generation time |
| pdf_path | VARCHAR(255) | Stored PDF path |

#### `expenses`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| category | VARCHAR(50) | 'salary', 'utility', 'maintenance', 'supplies', 'other' |
| description | TEXT | Expense description |
| amount | DECIMAL(10,2) | Expense amount |
| expense_date | DATE | Date of expense |
| added_by | INTEGER FK | Staff who added |
| created_at | TIMESTAMP | Entry time |

#### `activity_log`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-increment ID |
| staff_id | INTEGER FK | Staff who performed |
| action | VARCHAR(100) | Action description |
| details | TEXT | Additional details |
| ip_address | VARCHAR(45) | User IP |
| created_at | TIMESTAMP | Action time |

---

## 3. UI/UX Specification

### Color Palette
| Color | Hex | Usage |
|-------|-----|-------|
| Primary | #1a365d | Main headers, buttons |
| Secondary | #2d3748 | Secondary text, sidebar |
| Accent | #c9a227 | Gold accents, highlights |
| Success | #38a169 | Available rooms, success states |
| Warning | #d69e2e | Pending, alerts |
| Danger | #e53e3e | Occupied, errors |
| Light | #f7fafc | Backgrounds |
| Dark | #1a202c | Text, dark mode |

### Typography
- **Headings:** 'Playfair Display', serif
- **Body:** 'Inter', sans-serif
- **Monospace:** 'JetBrains Mono' (for numbers/IDs)

### Layout Structure
```
├── Login Page (full screen centered)
├── Main Dashboard
│   ├── Top Navigation (logo, notifications, user menu)
│   ├── Sidebar (collapsible)
│   │   ├── Dashboard
│   │   ├── Bookings
│   │   ├── Rooms
│   │   ├── Customers
│   │   ├── Payments
│   │   ├── Expenses
│   │   ├── Reports
│   │   ├── Staff
│   │   └── Settings
│   └── Main Content Area
└── Modals (for forms, confirmations)
```

### Page Specifications

#### 3.1 Login Page
- Centered card layout
- Hotel logo at top
- Username/password fields
- Remember me checkbox
- Forgot password link
- Error messages below fields

#### 3.2 Dashboard
- 4 stat cards (Today's Revenue, Occupancy, Pending Payments, Check-outs Today)
- Room availability grid (12 rooms in 4x3 grid)
- Recent bookings list (5 items)
- Quick actions panel

#### 3.3 Room Management
- Room cards with status badges
- Filter by status, type
- Click to view/edit room details
- Modal for room status update

#### 3.4 Booking/Check-in
- Two-column form
- Left: Customer details (new/existing toggle)
- Right: Room selection (visual grid)
- Bottom: Payment advance section
- Auto-calculation display

#### 3.4.1 Company Billing
- Checkbox option: "Company Billing" during check-in
- When enabled, additional fields appear:
  - Company Name (for billing)
  - Company GST Number
  - Company Address
- Invoice shows:
  - Bill To: Company details (if company billing)
  - Guest Details: Customer who is staying in room

#### 3.4.2 History Feature
- Track all activities for last 30 days (default)
- Filter by date range and type:
  - All
  - Bookings
  - Payments
  - Expenses
  - Activity Log
- Summary cards showing:
  - Total Bookings
  - Check-outs
  - Total Revenue
  - Total Expenses
  - Net Profit

#### 3.5 Invoice Design
```
┌─────────────────────────────────────────────────┐
│         HOTEL SHRI GOVIND                       │
│   Jagmal Chowk, near Honda Showroom,            │
│   Tikrapara, Bilaspur, Chhattisgarh 495001    │
│   Phone: 7891234560 | GST: 22AATFH3393Q1ZL    │
│ ──────────────────────────────────────────────── │
│                              INVOICE              │
│                           #INV-XXXX             │
│ Date: XX/XX/XXXX                                │
│ ──────────────────────────────────────────────── │
│ BILL TO:                     GUEST DETAILS:     │
│ ABC Industries Pvt. Ltd.     Rahul Kumar        │
│ GST: 22AAAAA0000A1Z5        Phone: 9876543210  │
│ Address: Business Park...     Email: abc@xyz.com│
│ ──────────────────────────────────────────────── │
│ Room: XXX    Type: XX    Nights: XX            │
│ Check-in: XX/XX/XX    Check-out: XX/XX/XX      │
│ ──────────────────────────────────────────────── │
│ Description          Qty    Rate     Amount     │
│ Room Charge          XX     XXX.XX    XXX.XX    │
│ Extra Charges        -      -         XX.XX    │
│ Discount             -      -        -XX.XX    │
│ ──────────────────────────────────────────────── │
│                    Subtotal:      Rs. XXXXX.XX  │
│                    CGST (2.5%):     Rs. XXXX.XX  │
│                    SGST (2.5%):     Rs. XXXX.XX  │
│                    Total:          Rs. XXXXX.XX  │
│                    Advance:       -Rs. XXXX.XX   │
│ ──────────────────────────────────────────────── │
│ Payment Mode: CASH / UPI / CARD                 │
│ Thank you for staying with us!                  │
│ ──────────────────────────────────────────────── │
│ For HOTEL SHRI GOVIND                           │
│ ________________________                         │
│ Authorised Signatory (Akshay Shukla)            │
└─────────────────────────────────────────────────┘
```
│ ──────────────────────────────────────────────── │
│ For HOTEL SHRI GOVIND                           │
│ _______________                                  │
│ Authorised Signatory                             │
│ ──────────────────────────────────────────────── │
│ [Download PDF]                                  │
└─────────────────────────────────────────────────┘
```

---

## 4. Functionality Specification

### 4.1 Authentication
- Login with username/password
- Session management (Flask-Login)
- Role-based access (admin, receptionist)
- Password change for admin
- Activity logging

### 4.2 Room Management
- 12 predefined rooms: 101-112
- Room types: 4 Standard (101-104), 4 Deluxe (105-108), 4 Suites (109-112)
- Prices: Standard Rs.1500, Deluxe Rs.2500, Suite Rs.4000
- Status updates: available, occupied, cleaning, maintenance
- Amenities list per room

### 4.3 Customer Management
- New customer registration with age field
- ID proof options: Aadhar Card, Voter ID, Driving License, Passport
- Accompanying persons support (add multiple persons with name, phone, age, ID proof)
- Existing customer search
- ID proof upload (stored in static/uploads)
- Total stay count tracking
- Customer history view

### 4.4 Room Pricing Rules

#### Standard/Deluxe Rooms:
| Persons | Charge |
|---------|--------|
| 1-2 | Default room charge (no extra) |
| 3+ | Rs. 500 per person per night extra |

#### Suite Rooms:
| Persons | Charge |
|---------|--------|
| 1-3 | Default room charge (no extra) |
| 4+ | Rs. 500 per person per night extra |

#### GST Mode Options:
- **Exclude GST**: GST (5%) is added to the subtotal
- **Include GST**: GST is deducted FROM the room price (price shown is inclusive of GST)
  - Example: Room rent Rs. 1000 with Include GST means the GST is already factored into 1000, no separate GST line in invoice

### 4.5 Bill Payer Options
- **Guest Pays**: Only guest details shown in invoice
- **Company Pays**: Both guest AND company details shown in invoice
  - Company billing details: Name, GST, Address
  - Payer details: Name, Phone, Address

### 4.6 Check-in Process
1. Select customer (new/existing)
2. Add accompanying persons (optional)
3. Select number of persons
4. Select GST mode (Include/Exclude)
5. Select room (show available only)
6. Enter check-in/check-out dates
7. Auto-calculate nights and extra person charges
8. Add bill payer type (Guest/Company)
9. Add advance payment
10. Generate booking ID
11. Update room status

### 4.7 Check-out Process
1. Search booking by ID/customer
2. Review charges (room + extras displayed in main bill)
3. Add any extra charges with quantity support
4. Apply discounts if any
5. Calculate GST based on GST mode
6. Show final amount with 3 decimal precision
7. Accept payment
8. Generate invoice
9. Mark room as cleaning

### 4.8 Extra Charges
- Food charges (itemized with quantity)
- Laundry charges
- Late checkout (Rs.200/hour after 12 PM)
- Extra person (Rs.500/night)
- Other charges
- All extras appear in main invoice (single unified bill)

### 4.9 Payment Module
- Cash payments
- UPI payments (with transaction ID)
- Card payments (with transaction ID)
- Partial payments tracking
- Payment history per booking

### 4.10 Invoice Generation
- Auto-generate invoice number: INV-YYYYMMDD-XXXX
- PDF with GST mode indicator
- Shows accompanying persons
- Shows bill payer details (Guest or Company)
- Shows extras in main invoice (no separate extras bill)
- 3 decimal precision in calculations
- Professional layout
- Download option
- Store PDF path in database

### 4.11 Reports
- Daily revenue report
- Monthly revenue report
- Occupancy rate
- Expense report
- Profit & loss calculation
- Export to PDF/Excel

### 4.12 Staff Management
- Add staff (admin only)
- Edit staff details
- Deactivate staff
- View activity logs
- Password reset

### 4.11 Expense Management
- Add expense
- Category selection
- Date picker
- Monthly expense report
- Profit calculation

---

## 5. API Endpoints

### Authentication
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me

### Rooms
- GET /api/rooms
- GET /api/rooms/<id>
- PUT /api/rooms/<id>
- PUT /api/rooms/<id>/status

### Customers
- GET /api/customers
- POST /api/customers
- GET /api/customers/<id>
- PUT /api/customers/<id>

### Bookings
- GET /api/bookings
- POST /api/bookings
- GET /api/bookings/<id>
- PUT /api/bookings/<id>/checkout
- PUT /api/bookings/<id>/cancel

### Payments
- GET /api/payments/booking/<id>
- POST /api/payments

### Extra Charges
- GET /api/charges/booking/<id>
- POST /api/charges
- DELETE /api/charges/<id>

### Invoices
- GET /api/invoices
- GET /api/invoices/<id>
- GET /api/invoices/<id>/download

### Expenses
- GET /api/expenses
- POST /api/expenses
- GET /api/expenses/report

### Reports
- GET /api/reports/daily
- GET /api/reports/monthly
- GET /api/reports/occupancy

### Staff
- GET /api/staff
- POST /api/staff
- PUT /api/staff/<id>

### Dashboard
- GET /api/dashboard/stats

---

## 6. File Structure

```
shreegovind/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── SPEC.md               # This specification
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles
│   ├── js/
│   │   └── main.js        # Custom JavaScript
│   ├── uploads/           # ID proof uploads
│   └── logo.png           # Hotel logo
├── templates/
│   ├── base.html          # Base template
│   ├── login.html         # Login page
│   ├── dashboard.html     # Dashboard
│   ├── rooms.html         # Room management
│   ├── room_detail.html   # Room details
│   ├── customers.html     # Customer list
│   ├── customer_detail.html
│   ├── bookings.html      # Booking list
│   ├── new_booking.html   # New check-in
│   ├── checkout.html      # Checkout process
│   ├── history.html       # History tracking
│   ├── checkout.html      # Check-out page
│   ├── payments.html      # Payment list
│   ├── expenses.html      # Expense management
│   ├── reports.html       # Reports page
│   ├── staff.html         # Staff management
│   ├── settings.html      # Settings page
│   ├── invoice.html       # Invoice view
│   └── partials/
│       ├── room_card.html
│       ├── booking_row.html
│       └── stat_card.html
└── instance/
    └── snb_hotel.db       # SQLite fallback database
```

---

## 7. Security Features

- Bcrypt password hashing
- Session-based authentication
- CSRF protection
- Input validation
- SQL injection prevention (SQLAlchemy ORM)
- Role-based access control
- Activity logging
- Secure file uploads

---

## 8. Future Enhancements (Not in MVP)

- WhatsApp invoice sending
- QR code payments
- SMS alerts
- Multi-language support
- Dark mode toggle
- Mobile app
- API for OTA integrations
