import os
from dotenv import load_dotenv
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, jsonify, session, flash, send_file, abort, Response
import csv
import io
from sqlalchemy.orm import joinedload
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, DateField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from werkzeug.utils import secure_filename
import r2_storage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import weasyprint
import os

app = Flask(__name__)
app.config.from_object('config.Config')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

@app.context_processor
def inject_globals():
    from datetime import datetime
    def get_hotel_settings():
        return {
            'name': Settings.get('hotel_name', 'HOTEL SHRI GOVIND'),
            'address': Settings.get('hotel_address', ''),
            'phone': Settings.get('hotel_phone', ''),
            'email': Settings.get('hotel_email', ''),
            'gst': Settings.get('hotel_gst', ''),
            'owner': Settings.get('hotel_owner', ''),
            'gst_rate': Settings.get('gst_rate', '5'),
            'price_classic': Settings.get('price_classic', '1500'),
            'price_deluxe': Settings.get('price_deluxe', '2500'),
            'price_suite': Settings.get('price_suite', '4000'),
        }
    def get_r2_url(filename):
        if not filename:
            return None
        return r2_storage.get_url(filename)
    return dict(datetime=datetime, hotel=get_hotel_settings(), r2_url=get_r2_url)

@app.template_filter('month_name')
def month_name_filter(month):
    from datetime import datetime
    return datetime(2000, month, 1).strftime('%B')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ==================== MODELS ====================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Staff, int(user_id))

class Staff(db.Model, UserMixin):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='receptionist')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'

class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    
    @staticmethod
    def get(key, default=None):
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set(key, value):
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = Settings(key=key, value=str(value))
            db.session.add(setting)
        db.session.commit()

def init_settings():
    defaults = {
        'hotel_name': 'HOTEL SHRI GOVIND',
        'hotel_address': 'Jagmal Chowk, near Honda Showroom, Tikrapara, Bilaspur, Chhattisgarh 495001',
        'hotel_phone': '7891234560',
        'hotel_email': 'example@gmail.com',
        'hotel_gst': '22AATFH3393Q1ZL',
        'hotel_owner': 'Akshay Shukla',
        'gst_rate': '5',
        'price_classic': '1500',
        'price_deluxe': '2500',
        'price_suite': '4000',
        'extra_person_charge': '300',
    }
    for key, value in defaults.items():
        if not Settings.get(key):
            Settings.set(key, value)

class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False)
    room_type = db.Column(db.String(30), nullable=False)
    price_per_night = db.Column(db.Numeric(10,2), nullable=False)
    status = db.Column(db.String(20), default='available')
    floor = db.Column(db.Integer, default=1)
    amenities = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='room', lazy=True)
    
    def get_amenities_list(self):
        if self.amenities:
            import json
            return json.loads(self.amenities)
        return []

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer)
    number_of_children = db.Column(db.Integer, default=0)
    address = db.Column(db.Text)
    id_proof_type = db.Column(db.String(20))
    id_proof_number = db.Column(db.String(50))
    id_proof_file = db.Column(db.String(255))
    total_stays = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='customer', lazy=True)
    accompanying_persons = db.relationship('AccompanyingPerson', backref='customer', lazy=True, cascade='all, delete-orphan')

class AccompanyingPerson(db.Model):
    __tablename__ = 'accompanying_persons'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    age = db.Column(db.Integer)
    id_proof_type = db.Column(db.String(20))
    id_proof_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    booking_category = db.Column(db.String(20), default='normal')
    wedding_package = db.Column(db.String(20), nullable=True)
    check_in = db.Column(db.DateTime, nullable=False)
    check_out = db.Column(db.DateTime, nullable=False)
    actual_check_in = db.Column(db.DateTime)
    actual_check_out = db.Column(db.DateTime)
    stay_duration = db.Column(db.Integer, nullable=False)
    number_of_persons = db.Column(db.Integer, default=1)
    gst_mode = db.Column(db.String(20), default='exclude')
    room_charge = db.Column(db.Numeric(10,3), default=0)
    extra_person_charges = db.Column(db.Numeric(10,3), default=0)
    extra_charges = db.Column(db.Numeric(10,3), default=0)
    discount = db.Column(db.Numeric(10,3), default=0)
    subtotal = db.Column(db.Numeric(10,3), default=0)
    gst_rate = db.Column(db.Numeric(5,3), default=5)
    gst_amount = db.Column(db.Numeric(10,3), default=0)
    total_amount = db.Column(db.Numeric(10,3), default=0)
    advance_amount = db.Column(db.Numeric(10,3), default=0)
    pending_amount = db.Column(db.Numeric(10,3), default=0)
    status = db.Column(db.String(20), default='checked_in')
    checked_in_by = db.Column(db.Integer, db.ForeignKey('staff.id'))
    checked_out_by = db.Column(db.Integer, db.ForeignKey('staff.id'))
    billing_name = db.Column(db.String(200))
    company_gst = db.Column(db.String(20))
    company_address = db.Column(db.Text)
    bill_payer_type = db.Column(db.String(20), default='guest')
    payer_name = db.Column(db.String(200))
    payer_phone = db.Column(db.String(20))
    payer_address = db.Column(db.Text)
    notes = db.Column(db.Text)
    purpose_of_visit = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    checked_in_staff = db.relationship('Staff', foreign_keys=[checked_in_by])
    checked_out_staff = db.relationship('Staff', foreign_keys=[checked_out_by])
    extra_charges_list = db.relationship('ExtraCharge', backref='booking', lazy=True)
    payments = db.relationship('Payment', backref='booking', lazy=True)
    invoice = db.relationship('Invoice', backref='booking', uselist=False)
    accompanying_persons = db.relationship('AccompanyingPerson', backref='booking', lazy=True)

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Numeric(10,3), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(20), default='completed')
    transaction_id = db.Column(db.String(50))
    received_by = db.Column(db.Integer, db.ForeignKey('staff.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    received_by_staff = db.relationship('Staff', foreign_keys=[received_by])

class ExtraCharge(db.Model):
    __tablename__ = 'extra_charges'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    charge_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    quantity = db.Column(db.Integer, default=1)
    amount = db.Column(db.Numeric(10,3), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('staff.id'))

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    pdf_path = db.Column(db.String(255))

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('staff.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    added_by_staff = db.relationship('Staff', foreign_keys=[added_by])

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    staff = db.relationship('Staff', backref='activities')

# ==================== FORMS ====================

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class StaffForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    role = SelectField('Role', choices=[('receptionist', 'Receptionist'), ('admin', 'Admin')])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
        validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Add Staff')
    
    def validate_username(self, username):
        staff = Staff.query.filter_by(username=username.data).first()
        if staff:
            raise ValidationError('Username already exists')

class CustomerForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    age = IntegerField('Age')
    number_of_children = IntegerField('Number of Children', default=0)
    address = TextAreaField('Address')
    id_proof_type = SelectField('ID Proof Type', 
        choices=[('', 'Select ID Proof'), ('aadhar', 'Aadhar Card'), ('voter_id', 'Voter ID'), 
                ('driving_license', 'Driving License'), ('passport', 'Passport')])
    id_proof_number = StringField('ID Proof Number', validators=[Length(max=50)])
    submit = SubmitField('Save Customer')

class BookingForm(FlaskForm):
    room_id = SelectField('Room', coerce=int, validators=[Optional()])
    check_in = StringField('Check-in Date', validators=[DataRequired()])
    check_out = StringField('Check-out Date')
    purpose_of_visit = StringField('Purpose of Visit', validators=[DataRequired()])
    billing_name = StringField('Billing Name (Company/Individual)', validators=[Length(max=200)])
    advance_amount = FloatField('Advance Amount', default=0)
    notes = TextAreaField('Notes')
    submit = SubmitField('Check In')

class PaymentForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired()])
    payment_method = SelectField('Payment Method', 
        choices=[('cash', 'Cash'), ('upi', 'UPI'), ('card', 'Card')])
    transaction_id = StringField('Transaction ID (for UPI/Card)')
    submit = SubmitField('Add Payment')

class ExtraChargeForm(FlaskForm):
    charge_type = SelectField('Charge Type', 
        choices=[('food', 'Food'), ('laundry', 'Laundry'), ('late_checkout', 'Late Checkout'),
                ('extra_person', 'Extra Person'), ('other', 'Other')])
    description = StringField('Description')
    amount = FloatField('Amount', validators=[DataRequired()])
    submit = SubmitField('Add Charge')

class ExpenseForm(FlaskForm):
    category = SelectField('Category', 
        choices=[('salary', 'Salary'), ('utility', 'Utility'), ('maintenance', 'Maintenance'),
                ('supplies', 'Supplies'), ('other', 'Other')])
    description = TextAreaField('Description', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    expense_date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Add Expense')

class RoomForm(FlaskForm):
    room_type = SelectField('Room Type', 
        choices=[('standard', 'Standard'), ('deluxe', 'Deluxe'), ('suite', 'Suite')])
    price_per_night = FloatField('Price per Night', validators=[DataRequired()])
    status = SelectField('Status', 
        choices=[('available', 'Available'), ('maintenance', 'Maintenance')])
    submit = SubmitField('Update Room')

# ==================== HELPER FUNCTIONS ====================

def generate_booking_id():
    now = datetime.now()
    return now.strftime('%Y%m%d%H%M%S')

def generate_invoice_number():
    from sqlalchemy import func
    max_num = db.session.query(func.max(Invoice.invoice_number)).scalar()
    if max_num:
        try:
            next_num = int(max_num) + 1
        except (ValueError, TypeError):
            count = db.session.query(func.count(Invoice.id)).scalar() or 0
            next_num = count + 1
    else:
        next_num = 1
    return f'{next_num:09d}'

def calculate_bill(booking):
    try:
        if booking.booking_category == 'wedding':
            wedding_rates = {'all_9_ac': Decimal('15000'), 'all_rooms': Decimal('17000')}
            package_rate = wedding_rates.get(booking.wedding_package, Decimal('15000'))
            base_room_charge = package_rate * (booking.stay_duration or 1)
        else:
            room = db.session.get(Room, booking.room_id)
            if not room:
                return {'error': 'Room not found'}
            base_room_charge = (room.price_per_night or 0) * (booking.stay_duration or 1)
    except Exception as e:
        return {'error': str(e)}
    
    try:
        extra_person_charges = booking.extra_person_charges if booking.extra_person_charges else Decimal('0')
        
        room_charge = base_room_charge + (extra_person_charges or Decimal('0'))
        
        extra_total = Decimal('0')
        try:
            extra_total = sum(ec.amount for ec in booking.extra_charges_list if ec.amount)
        except:
            extra_total = Decimal('0')
        
        discount = booking.discount if booking.discount else Decimal('0')
        subtotal = room_charge + extra_total - discount
        
        gst_rate = Decimal(str(booking.gst_rate or 5))
        gst_amount = Decimal('0')
        base_price = Decimal('0')
        
        if subtotal > 0:
            if booking.gst_mode == 'exclude':
                gst_amount = (subtotal * gst_rate) / 100
                total = subtotal + gst_amount
                base_price = subtotal
                display_subtotal = subtotal
            else:
                base_price = (subtotal * 100) / (100 + gst_rate)
                gst_amount = subtotal - base_price
                total = subtotal
                display_subtotal = subtotal
        else:
            total = Decimal('0')
            base_price = Decimal('0')
            display_subtotal = Decimal('0')
        
        advance = booking.advance_amount if booking.advance_amount else Decimal('0')
        pending = total - advance
        
        return {
            'base_room_charge': Decimal(str(base_room_charge)),
            'extra_person_charges': extra_person_charges,
            'extra_charges': extra_total,
            'subtotal': display_subtotal,
            'base_price': base_price,
            'gst_amount': gst_amount,
            'gst_rate': gst_rate,
            'gst_mode': booking.gst_mode or 'exclude',
            'total_amount': total,
            'pending_amount': pending,
            'stay_duration': booking.stay_duration or 1
        }
    except Exception as e:
        return {
            'base_room_charge': Decimal('0'),
            'extra_person_charges': Decimal('0'),
            'extra_charges': Decimal('0'),
            'subtotal': Decimal('0'),
            'gst_amount': Decimal('0'),
            'gst_mode': 'exclude',
            'total_amount': Decimal('0'),
            'pending_amount': Decimal('0'),
            'stay_duration': 1,
            'error': str(e)
        }

def calculate_extra_person_charge(room_type, total_persons, stay_duration):
    extra_persons = 0
    if room_type in ['classic', 'standard', 'deluxe']:
        if total_persons > 2:
            extra_persons = total_persons - 2
    elif room_type == 'suite':
        if total_persons > 3:
            extra_persons = total_persons - 3
    
    per_head_charge = Decimal(str(Settings.get('extra_person_charge', '300')))
    extra_charge = extra_persons * per_head_charge * stay_duration
    return float(extra_charge), extra_persons

def log_activity(action, details=None):
    log = ActivityLog(
        staff_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def create_pdf_invoice(invoice, booking, customer, room):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    elements = []
    
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    
    hotel_name = Settings.get('hotel_name', 'HOTEL SHRI GOVIND')
    hotel_address = Settings.get('hotel_address', '')
    hotel_phone = Settings.get('hotel_phone', '')
    hotel_gst = Settings.get('hotel_gst', '')
    hotel_owner = Settings.get('hotel_owner', 'Akshay Shukla')
    
    PRIMARY = colors.HexColor('#1a365d')
    ACCENT = colors.HexColor('#c9a227')
    SUCCESS = colors.HexColor('#38a169')
    DANGER = colors.HexColor('#e53e3e')
    GRAY = colors.HexColor('#718096')
    
    def P(text, style='N', **kw):
        return Paragraph(text, ParagraphStyle('S', parent=styles['Normal'], fontSize=kw.get('fs', 11), textColor=kw.get('c', colors.black), alignment=kw.get('a', TA_LEFT), fontName=kw.get('fn', 'Helvetica'), spaceAfter=kw.get('sa', 0), spaceBefore=kw.get('sb', 0), leading=kw.get('l', 14)))
    
    def H(text, fs=11, c=colors.black, a=TA_LEFT):
        return P(f'<b>{text}</b>', fs=fs, c=c, a=a)
    
    header_td_left = []
    header_td_left.append(H(hotel_name.upper(), fs=18, c=PRIMARY))
    if hotel_address:
        header_td_left.append(P(hotel_address, fs=10, c=GRAY))
    contact_parts = []
    if hotel_phone: contact_parts.append(f'Phone: {hotel_phone}')
    if hotel_gst: contact_parts.append(f'GST: {hotel_gst}')
    if contact_parts:
        header_td_left.append(P(' | '.join(contact_parts), fs=9, c=GRAY))
    
    checkin_str = booking.actual_check_in.strftime('%d %b %Y, %I:%M %p') if booking.actual_check_in else booking.check_in.strftime('%d %b %Y, %I:%M %p')
    checkout_str = booking.actual_check_out.strftime('%d %b %Y, %I:%M %p') if booking.actual_check_out else booking.check_out.strftime('%d %b %Y, %I:%M %p')
    
    header_td_right = []
    header_td_right.append(H('INVOICE', fs=20, c=colors.HexColor('#1a202c'), a=TA_RIGHT))
    header_td_right.append(P(f'<b>{invoice.invoice_number}</b><br/>Date: {invoice.generated_at.strftime("%d %b %Y, %I:%M %p")}', fs=11, c=colors.HexColor('#4a5568'), a=TA_RIGHT))
    
    left_content = []
    for item in header_td_left:
        left_content.append(item)
    left_cell = []
    for item in left_content:
        left_cell.append(item)
    
    left_block = []
    for item in header_td_left:
        left_block.append(item)
        left_block.append(Spacer(1, 2))
    
    qr_image = None
    qr_path = os.path.join(os.path.dirname(__file__), 'static', 'hotel_qr.png')
    if os.path.exists(qr_path):
        try:
            qr_image = Image(qr_path, width=60, height=60)
        except:
            qr_image = None
    
    right_col_items = []
    for item in header_td_right:
        right_col_items.append(item)
    if qr_image:
        right_col_items.append(Spacer(1, 5))
        right_col_items.append(qr_image)
    
    right_block = []
    for item in header_td_right:
        right_block.append(item)
    if qr_image:
        right_block.append(Spacer(1, 5))
        right_block.append(qr_image)
    
    header_cell_left = []
    header_cell_left.append(H(hotel_name.upper(), fs=18, c=PRIMARY))
    if hotel_address:
        header_cell_left.append(P(hotel_address, fs=10, c=GRAY))
    if contact_parts:
        header_cell_left.append(P(' | '.join(contact_parts), fs=9, c=GRAY))
    
    header_cell_right = []
    header_cell_right.append(H('INVOICE', fs=20, c=colors.HexColor('#1a202c'), a=TA_RIGHT))
    header_cell_right.append(P(f'<b>{invoice.invoice_number}</b><br/>Date: {invoice.generated_at.strftime("%d %b %Y, %I:%M %p")}', fs=11, c=colors.HexColor('#4a5568'), a=TA_RIGHT))
    if qr_image:
        header_cell_right.append(Spacer(1, 5))
        header_cell_right.append(qr_image)
    
    left_frame = []
    for item in header_cell_left:
        left_frame.append(item)
    
    right_frame = []
    for item in header_cell_right:
        right_frame.append(item)
    
    header_table = Table([
        [left_frame, right_frame]
    ], colWidths=[300, 250])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    
    elements.append(Table([['']], colWidths=[550], style=TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, PRIMARY),
    ])))
    elements.append(Spacer(1, 15))
    
    bill_to = H('BILL TO', fs=9, c=GRAY)
    bill_to_name = booking.billing_name if booking.billing_name else customer.name
    bill_lines = [bill_to, P(f'<b>{bill_to_name}</b>', fs=11)]
    if booking.company_gst:
        bill_lines.append(P(f'GST: {booking.company_gst}', fs=10, c=GRAY))
    if booking.company_address:
        bill_lines.append(P(f'{booking.company_address}', fs=10, c=GRAY))
    elif customer.address:
        bill_lines.append(P(f'{customer.address}', fs=10, c=GRAY))
    
    guest_lines = [H('GUEST DETAILS', fs=9, c=GRAY), P(f'<b>{customer.name}</b>', fs=11), P(f'{customer.phone}', fs=10, c=GRAY)]
    if customer.address:
        guest_lines.append(P(f'{customer.address}', fs=10, c=GRAY))
    
    booking_lines = [H('BOOKING DETAILS', fs=9, c=GRAY)]
    booking_lines.append(P(f'<b>Booking ID:</b> {booking.booking_id}', fs=10))
    if booking.booking_category == 'wedding':
        pkg_name = {'all_9_ac': 'All 9 AC Rooms', 'all_rooms': 'All Rooms'}.get(booking.wedding_package, 'Wedding Package')
        booking_lines.append(P(f'<b>Package:</b> {pkg_name}', fs=10))
    else:
        rt = room.room_number + ' (' + room.room_type.title() + ')' if room else 'N/A'
        booking_lines.append(P(f'<b>Room:</b> {rt}', fs=10))
    booking_lines.append(P(f'<b>Persons:</b> {booking.number_of_persons}', fs=10))
    booking_lines.append(P(f'<b>Check-in:</b> {checkin_str}', fs=10))
    booking_lines.append(P(f'<b>Check-out:</b> {checkout_str}', fs=10))
    booking_lines.append(P(f'<b>Nights:</b> {booking.stay_duration}', fs=10))
    
    col_width = 180
    info_table = Table([
        [bill_lines, guest_lines, booking_lines]
    ], colWidths=[col_width, col_width, col_width])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))
    
    accompanying_persons = AccompanyingPerson.query.filter_by(booking_id=booking.id).all()
    if accompanying_persons:
        ap_names = '  |  '.join([f'{ap.name}' + (f' ({ap.phone})' if ap.phone else '') for ap in accompanying_persons])
        elements.append(H('ACCOMPANYING PERSONS', fs=9, c=GRAY))
        elements.append(P(ap_names, fs=10))
        elements.append(Spacer(1, 12))
    
    cgst_amount = float(booking.gst_amount or 0) / 2
    sgst_amount = float(booking.gst_amount or 0) / 2
    gst_percent = float(booking.gst_rate or 5) / 2
    
    if booking.booking_category == 'wedding':
        wedding_rates = {'all_9_ac': 15000, 'all_rooms': 17000}
        room_rate = wedding_rates.get(booking.wedding_package, 15000)
        package_name = {'all_9_ac': 'All 9 AC Rooms', 'all_rooms': 'All Rooms'}.get(booking.wedding_package, 'Wedding Package')
        room_charge_total = room_rate * booking.stay_duration
        charges_data = [
            [P('<b>Description</b>', fs=10), P('<b>Qty</b>', fs=10, a=TA_CENTER), P('<b>Rate</b>', fs=10, a=TA_RIGHT), P('<b>Amount</b>', fs=10, a=TA_RIGHT)],
            [P(f'<b>Wedding Package ({package_name})</b>', fs=10), P(f'<b>{booking.stay_duration}</b>', fs=10, a=TA_CENTER), P(f'<b>Rs. {room_rate:,.2f}</b>', fs=10, a=TA_RIGHT, fn='Courier'), P(f'<b>Rs. {room_charge_total:,.2f}</b>', fs=10, a=TA_RIGHT, fn='Courier')],
        ]
    else:
        room_rate = float(room.price_per_night)
        room_charge_total = room_rate * booking.stay_duration
        charges_data = [
            [P('<b>Description</b>', fs=10), P('<b>Qty</b>', fs=10, a=TA_CENTER), P('<b>Rate</b>', fs=10, a=TA_RIGHT), P('<b>Amount</b>', fs=10, a=TA_RIGHT)],
            [P('<b>Room Charge</b>', fs=10), P(f'<b>{booking.stay_duration}</b>', fs=10, a=TA_CENTER), P(f'<b>Rs. {room_rate:,.2f}</b>', fs=10, a=TA_RIGHT, fn='Courier'), P(f'<b>Rs. {room_charge_total:,.2f}</b>', fs=10, a=TA_RIGHT, fn='Courier')],
        ]
        if float(booking.extra_person_charges or 0) > 0:
            charges_data.append([P('Extra Person Charges', fs=10), P('', fs=10), P('Rs. 500.00', fs=10, a=TA_RIGHT, fn='Courier'), P(f'Rs. {float(booking.extra_person_charges):,.2f}', fs=10, a=TA_RIGHT, fn='Courier')])
    
    for ec in booking.extra_charges_list:
        desc = ec.description if ec.description else ec.charge_type.replace('_', ' ').title()
        unit_rate = float(ec.amount/ec.quantity) if ec.quantity > 0 else float(ec.amount)
        charges_data.append([P(desc, fs=10), P(str(ec.quantity), fs=10, a=TA_CENTER), P(f'Rs. {unit_rate:,.2f}', fs=10, a=TA_RIGHT, fn='Courier'), P(f'Rs. {float(ec.amount):,.2f}', fs=10, a=TA_RIGHT, fn='Courier')])
    
    if float(booking.discount or 0) > 0:
        charges_data.append([P('Discount', fs=10), P('', fs=10), P('', fs=10), P(f'Rs. {float(booking.discount):,.2f}', fs=10, a=TA_RIGHT, fn='Courier', c=SUCCESS)])
    
    if float(booking.gst_amount or 0) > 0 and booking.gst_mode == 'include':
        gst_rate = float(booking.gst_rate or 5)
        taxable = float(booking.total_amount) - float(booking.gst_amount)
        cgst = round(float(booking.gst_amount) / 2, 2)
        sgst = float(booking.gst_amount) - cgst
        charges_data.append([P('', fs=10), P('', fs=10), P(f'<b>Grand Total (Incl. GST {gst_rate:.1f}%):</b>', fs=11, c=PRIMARY, a=TA_RIGHT), P(f'<b>Rs. {float(booking.total_amount):,.2f}</b>', fs=11, c=PRIMARY, a=TA_RIGHT, fn='Courier')])
        charges_data.append([P('<i>Included Tax Breakdown</i>', fs=8, c=GRAY), P('', fs=10), P('', fs=10), P('', fs=10)])
        charges_data.append([P('Taxable Amount', fs=9), P('', fs=10), P('', fs=10), P(f'Rs. {taxable:,.2f}', fs=9, a=TA_RIGHT, fn='Courier')])
        charges_data.append([P(f'CGST @{gst_rate/2:.1f}%', fs=9), P('', fs=10), P('', fs=10), P(f'{cgst:,.2f}', fs=9, a=TA_RIGHT, fn='Courier')])
        charges_data.append([P(f'SGST @{gst_rate/2:.1f}%', fs=9), P('', fs=10), P('', fs=10), P(f'{sgst:,.2f}', fs=9, a=TA_RIGHT, fn='Courier')])
        charges_data.append([P('Total GST', fs=9, c=GRAY), P('', fs=10), P('', fs=10), P(f'{float(booking.gst_amount):,.2f}', fs=9, c=GRAY, a=TA_RIGHT, fn='Courier')])
    else:
        gst_amount = float(booking.gst_amount or 0)
        cgst_e = round(gst_amount / 2, 2) if gst_amount > 0 else 0
        sgst_e = gst_amount - cgst_e if gst_amount > 0 else 0
        charges_data.append([P('', fs=10), P('', fs=10), P('<b>Subtotal (before GST):</b>', fs=10, a=TA_RIGHT), P(f'<b>Rs. {float(booking.subtotal):,.2f}</b>', fs=10, a=TA_RIGHT, fn='Courier')])
        if gst_amount > 0:
            charges_data.append([P('', fs=10), P('', fs=10), P('<i>Tax Breakdown</i>', fs=8, c=GRAY, a=TA_RIGHT), P('', fs=10)])
            charges_data.append([P('', fs=10), P('', fs=10), P(f'CGST @{gst_percent:.1f}%', fs=9, a=TA_RIGHT), P(f'{cgst_e:,.2f}', fs=9, a=TA_RIGHT, fn='Courier')])
            charges_data.append([P('', fs=10), P('', fs=10), P(f'SGST @{gst_percent:.1f}%', fs=9, a=TA_RIGHT), P(f'{sgst_e:,.2f}', fs=9, a=TA_RIGHT, fn='Courier')])
            charges_data.append([P('', fs=10), P('', fs=10), P('Total GST', fs=9, c=GRAY, a=TA_RIGHT), P(f'{gst_amount:,.2f}', fs=9, c=GRAY, a=TA_RIGHT, fn='Courier')])
        charges_data.append([P('', fs=10), P('', fs=10), P(f'<b>Grand Total (incl. GST {float(booking.gst_rate or 5):.1f}%):</b>', fs=11, c=PRIMARY, a=TA_RIGHT), P(f'<b>Rs. {float(booking.total_amount):,.2f}</b>', fs=11, c=PRIMARY, a=TA_RIGHT, fn='Courier')])
    
    pending = float(booking.pending_amount or 0)
    advance = float(booking.advance_amount or 0)
    
    if advance > 0 and pending > 0:
        charges_data.append([P('', fs=10), P('', fs=10), P('<b>Advance Paid:</b>', fs=10, c=SUCCESS, a=TA_RIGHT), P(f'<b>-Rs. {advance:,.2f}</b>', fs=10, c=SUCCESS, a=TA_RIGHT, fn='Courier')])
        charges_data.append([P('', fs=10), P('', fs=10), P('<b>Balance Due:</b>', fs=10, c=DANGER, a=TA_RIGHT), P(f'<b>Rs. {pending:,.2f}</b>', fs=10, c=DANGER, a=TA_RIGHT, fn='Courier')])
    elif pending < 0:
        charges_data.append([P('', fs=10), P('', fs=10), P('<b>Excess Paid:</b>', fs=10, c=SUCCESS, a=TA_RIGHT), P(f'<b>Rs. {advance - float(booking.total_amount):,.2f}</b>', fs=10, c=SUCCESS, a=TA_RIGHT, fn='Courier')])
    else:
        charges_data.append([P('', fs=10), P('', fs=10), P('<b>Paid:</b>', fs=10, c=SUCCESS, a=TA_RIGHT), P('<b>PAID</b>', fs=10, c=SUCCESS, a=TA_RIGHT, fn='Courier')])
    
    charges_table = Table(charges_data, colWidths=[270, 50, 110, 120])
    table_style = [
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    charges_table.setStyle(TableStyle(table_style))
    elements.append(charges_table)
    elements.append(Spacer(1, 25))
    
    elements.append(Spacer(1, 20))
    
    sign_table = Table([
        [P('<b>Guest Signature</b>', fs=10, c=GRAY), P('', fs=10), P(f'<b>For {hotel_name.upper()}</b>', fs=10, a=TA_RIGHT, c=GRAY)],
        [P('_' * 30, fs=10), P('', fs=10), P('_' * 30, fs=10, a=TA_RIGHT)],
        [P(f'<b>{customer.name}</b>', fs=10), P('', fs=10), P(f'<b>Authorised Signatory</b><br/>{hotel_owner}', fs=9, a=TA_RIGHT, c=GRAY)],
    ], colWidths=[180, 190, 180])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(sign_table)
    elements.append(Spacer(1, 20))
    
    elements.append(Table([['']], colWidths=[550], style=TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, ACCENT),
    ])))
    elements.append(Spacer(1, 8))
    elements.append(P('<i>Thank you for staying with us!</i>', fs=10, c=GRAY, a=TA_CENTER))
    elements.append(P('Terms: Check-out time is 12:00 PM. Late checkout charges apply after that.', fs=8, c=GRAY, a=TA_CENTER))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== ROUTES ====================

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        staff = Staff.query.filter_by(username=form.username.data).first()
        if staff and staff.check_password(form.password.data) and staff.is_active:
            login_user(staff)
            staff.last_login = datetime.utcnow()
            db.session.commit()
            log_activity('Login', f'User {staff.username} logged in')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    log_activity('Logout', f'User {current_user.username} logged out')
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    # Today's stats
    today_bookings = Booking.query.filter(
        db.extract('year', Booking.created_at) == today.year,
        db.extract('month', Booking.created_at) == today.month,
        db.extract('day', Booking.created_at) == today.day
    ).count()
    
    # Today's revenue
    today_payments = db.session.query(db.func.sum(Payment.amount)).filter(
        db.extract('year', Payment.created_at) == today.year,
        db.extract('month', Payment.created_at) == today.month,
        db.extract('day', Payment.created_at) == today.day,
        Payment.payment_status == 'completed'
    ).scalar() or 0
    
    # Occupancy
    occupied = Room.query.filter_by(status='occupied').count()
    occupancy_rate = (occupied / 12) * 100
    
    # Pending payments
    pending_bookings = Booking.query.filter_by(status='checked_in').all()
    total_pending = sum(float(b.pending_amount) for b in pending_bookings)
    
    # Today's check-outs
    today_checkouts = Booking.query.filter(
        db.extract('year', Booking.check_out) == today.year,
        db.extract('month', Booking.check_out) == today.month,
        db.extract('day', Booking.check_out) == today.day,
        Booking.status == 'checked_in'
    ).count()
    
    # Rooms
    rooms = Room.query.order_by(Room.room_number).all()
    
    # Recent bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    
    stats = {
        'today_bookings': today_bookings,
        'today_revenue': float(today_payments),
        'occupancy_rate': occupancy_rate,
        'pending_payments': total_pending,
        'today_checkouts': today_checkouts
    }
    
    return render_template('dashboard.html', stats=stats, rooms=rooms, recent_bookings=recent_bookings)

# ==================== ROOMS ====================

@app.route('/rooms')
@login_required
def rooms():
    rooms_list = Room.query.order_by(Room.room_number).all()
    return render_template('rooms.html', rooms=rooms_list)

@app.route('/rooms/<int:room_id>', methods=['GET', 'POST'])
@login_required
def room_detail(room_id):
    room = db.get_or_404(Room, room_id)
    form = RoomForm(obj=room)
    
    if form.validate_on_submit():
        room.room_type = form.room_type.data
        room.price_per_night = Decimal(str(form.price_per_night.data))
        if room.status != 'occupied':
            room.status = form.status.data
        db.session.commit()
        log_activity('Update Room', f'Room {room.room_number} updated')
        flash('Room updated successfully', 'success')
        return redirect(url_for('rooms'))
    
    # Get current booking if occupied
    current_booking = None
    if room.status == 'occupied':
        current_booking = Booking.query.filter_by(room_id=room.id, status='checked_in').first()
    
    return render_template('room_detail.html', room=room, form=form, current_booking=current_booking)

@app.route('/rooms/<int:room_id>/status', methods=['POST'])
@login_required
def update_room_status(room_id):
    room = db.get_or_404(Room, room_id)
    status = request.json.get('status')
    
    if status in ['available', 'maintenance', 'cleaning']:
        room.status = status
        db.session.commit()
        log_activity('Room Status', f'Room {room.room_number} marked as {status}')
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid status'})

@app.route('/api/rooms', methods=['GET'])
@login_required
def api_get_rooms():
    rooms_list = Room.query.order_by(Room.room_number).all()
    return jsonify([{
        'id': r.id,
        'room_number': r.room_number,
        'room_type': r.room_type,
        'price_per_night': float(r.price_per_night),
        'status': r.status,
        'floor': r.floor,
        'amenities': r.get_amenities_list()
    } for r in rooms_list])

@app.route('/api/rooms', methods=['POST'])
@login_required
def api_create_room():
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data.get('room_number') or not data.get('room_type') or not data.get('price_per_night'):
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    existing = Room.query.filter_by(room_number=data['room_number']).first()
    if existing:
        return jsonify({'success': False, 'error': 'Room number already exists'})
    
    room = Room(
        room_number=data['room_number'],
        room_type=data['room_type'],
        price_per_night=Decimal(str(data['price_per_night'])),
        status=data.get('status', 'available'),
        floor=int(data.get('floor', 1)),
        amenities='["AC", "TV", "WiFi", "Hot Water"]' if data['room_type'] in ['deluxe', 'suite'] else '["TV", "WiFi", "Hot Water"]'
    )
    db.session.add(room)
    db.session.commit()
    log_activity('Add Room', f'Room {room.room_number} added')
    
    return jsonify({'success': True, 'room': {
        'id': room.id,
        'room_number': room.room_number,
        'room_type': room.room_type,
        'price_per_night': float(room.price_per_night),
        'status': room.status,
        'floor': room.floor
    }})

@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
@login_required
def api_update_room(room_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'success': False, 'error': 'Room not found'}), 404
    
    data = request.get_json()
    
    if data.get('room_number'):
        existing = Room.query.filter(Room.room_number == data['room_number'], Room.id != room_id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Room number already exists'})
        room.room_number = data['room_number']
    
    if data.get('room_type'):
        room.room_type = data['room_type']
    if data.get('price_per_night'):
        room.price_per_night = Decimal(str(data['price_per_night']))
    if data.get('floor') is not None:
        room.floor = data['floor']
    if data.get('status') and room.status != 'occupied':
        room.status = data['status']
    if data.get('floor'):
        room.floor = int(data['floor'])
    
    db.session.commit()
    log_activity('Update Room', f'Room {room.room_number} updated')
    
    return jsonify({'success': True, 'room': {
        'id': room.id,
        'room_number': room.room_number,
        'room_type': room.room_type,
        'price_per_night': float(room.price_per_night),
        'status': room.status,
        'floor': room.floor
    }})

@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
@login_required
def api_delete_room(room_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'success': False, 'error': 'Room not found'}), 404
    
    if room.status == 'occupied':
        return jsonify({'success': False, 'error': 'Cannot delete occupied room'})
    
    room_number = room.room_number
    db.session.delete(room)
    db.session.commit()
    log_activity('Delete Room', f'Room {room_number} deleted')
    
    return jsonify({'success': True})

# ==================== CUSTOMERS ====================

@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '')
    if search:
        customers_list = Customer.query.filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%')
            )
        ).order_by(Customer.created_at.desc()).all()
    else:
        customers_list = Customer.query.order_by(Customer.created_at.desc()).limit(50).all()
    return render_template('customers.html', customers=customers_list, search=search)

@app.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    bookings = Booking.query.filter_by(customer_id=customer_id).order_by(Booking.created_at.desc()).all()
    return render_template('customer_detail.html', customer=customer, bookings=bookings)

@app.route('/customers/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    form = CustomerForm()
    
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            phone=form.phone.data,
            age=form.age.data,
            number_of_children=form.number_of_children.data,
            address=form.address.data,
            id_proof_type=form.id_proof_type.data,
            id_proof_number=form.id_proof_number.data
        )
        
        if 'id_proof' in request.files:
            file = request.files['id_proof']
            if file and allowed_file(file.filename):
                filename = f'{uuid.uuid4()}_{secure_filename(file.filename)}'
                if r2_storage.is_configured():
                    r2_storage.upload_fileobj(file, filename)
                else:
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                customer.id_proof_file = filename
        
        db.session.add(customer)
        db.session.commit()
        
        extra_persons_count = int(request.form.get('extra_persons_count', 0))
        for i in range(extra_persons_count):
            person_name = request.form.get(f'person_name_{i}')
            if person_name:
                person = AccompanyingPerson(
                    customer_id=customer.id,
                    name=person_name,
                    phone=request.form.get(f'person_phone_{i}'),
                    age=request.form.get(f'person_age_{i}') if request.form.get(f'person_age_{i}') else None,
                    id_proof_type=request.form.get(f'person_id_type_{i}'),
                    id_proof_number=request.form.get(f'person_id_number_{i}')
                )
                db.session.add(person)
        db.session.commit()
        
        log_activity('New Customer', f'Customer {customer.name} added')
        flash('Customer added successfully', 'success')
        return redirect(url_for('customers'))
    
    return render_template('new_customer.html', form=form)

@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        customer.name = form.name.data
        customer.phone = form.phone.data
        customer.age = form.age.data
        customer.number_of_children = form.number_of_children.data
        customer.address = form.address.data
        customer.id_proof_type = form.id_proof_type.data
        customer.id_proof_number = form.id_proof_number.data
        
        if 'id_proof' in request.files and request.files['id_proof'].filename:
            file = request.files['id_proof']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{customer.id}_id_proof_{file.filename}")
                if r2_storage.is_configured():
                    r2_storage.upload_fileobj(file, filename)
                else:
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                customer.id_proof_file = filename
        
        db.session.commit()
        log_activity('Update Customer', f'Customer {customer.name} updated')
        flash('Customer updated successfully', 'success')
        return redirect(url_for('customer_detail', customer_id=customer.id))
    
    return render_template('edit_customer.html', form=form, customer=customer)

@app.route('/api/customers/search')
@login_required
def search_customers():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    customers = Customer.query.filter(
        db.or_(
            Customer.name.ilike(f'%{query}%'),
            Customer.phone.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'total_stays': c.total_stays
    } for c in customers])

@app.route('/api/customers/<int:customer_id>')
@login_required
def get_customer(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    accompanying_persons = AccompanyingPerson.query.filter_by(customer_id=customer_id).all()
    
    return jsonify({
        'id': customer.id,
        'name': customer.name,
        'phone': customer.phone,
        'age': customer.age,
        'number_of_children': customer.number_of_children,
        'address': customer.address,
        'id_proof_type': customer.id_proof_type,
        'id_proof_number': customer.id_proof_number,
        'total_stays': customer.total_stays,
        'accompanying_persons': [{
            'id': ap.id,
            'name': ap.name,
            'phone': ap.phone,
            'age': ap.age,
            'id_proof_type': ap.id_proof_type,
            'id_proof_number': ap.id_proof_number
        } for ap in accompanying_persons]
    })

# ==================== BOOKINGS ====================

@app.route('/bookings')
@login_required
def bookings():
    status = request.args.get('status', 'all')
    
    query = Booking.query.order_by(Booking.created_at.desc())
    if status != 'all':
        query = query.filter_by(status=status)
    
    bookings_list = query.all()
    
    for b in bookings_list:
        try:
            _ = b.customer.name if b.customer else None
            _ = b.room.room_number if b.room else None
        except Exception as e:
            print(f"[DEBUG] Error loading relationships for booking {b.booking_id}: {e}")
    
    return render_template('bookings.html', bookings=bookings_list, status=status)

@app.route('/bookings/new', methods=['GET', 'POST'])
@login_required
def new_booking():
    form = BookingForm()
    
    customers = Customer.query.order_by(Customer.name).all()
    available_rooms = Room.query.filter(Room.status.in_(['available', 'cleaning'])).order_by(Room.room_number).all()
    gst_rate = float(Settings.get('gst_rate', '5'))
    
    if not available_rooms:
        flash('No rooms are currently available. Please wait for rooms to be cleaned or check room statuses.', 'warning')
    
    form.room_id.choices = [(r.id, f'{r.room_number} - {r.room_type.title()} (Rs. {float(r.price_per_night):.0f}/night)') for r in available_rooms]
    
    if request.method == 'GET':
        form.check_in.data = datetime.now().strftime('%Y-%m-%d')
        form.check_out.data = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    form.check_out.data = request.form.get('check_out') or form.check_out.data
    
    if form.validate_on_submit():
        customer_id = request.form.get('customer_id')
        print(f"[DEBUG] Form validated successfully - Creating booking...")
        
        if not customer_id or customer_id == '0' or customer_id == '':
            flash('Please select a customer first', 'danger')
            return render_template('new_booking.html', form=form, customers=customers)
        
        booking_category = request.form.get('booking_category', 'normal')
        wedding_package = request.form.get('wedding_package', '') if booking_category == 'wedding' else None
        
        if booking_category == 'wedding':
            room_id = None
            if wedding_package not in ['all_9_ac', 'all_rooms']:
                flash('Please select a wedding package', 'danger')
                return render_template('new_booking.html', form=form, customers=customers)
        else:
            room_id = form.room_id.data
            if not room_id:
                flash('Please select a room', 'danger')
                return render_template('new_booking.html', form=form, customers=customers)
        
        check_in_date = datetime.strptime(form.check_in.data, '%Y-%m-%d')
        if form.check_out.data:
            check_out_date = datetime.strptime(form.check_out.data, '%Y-%m-%d')
        else:
            check_out_date = check_in_date + timedelta(days=1)
        
        check_in_time_str = request.form.get('check_in_time')
        check_out_time_str = request.form.get('check_out_time')
        now = datetime.now()
        
        try:
            if check_in_time_str:
                check_in_time_parts = check_in_time_str.split(':')
                check_in_hour = int(check_in_time_parts[0])
                check_in_minute = int(check_in_time_parts[1]) if len(check_in_time_parts) > 1 else 0
            else:
                check_in_hour, check_in_minute = now.hour, now.minute
        except:
            check_in_hour, check_in_minute = now.hour, now.minute
        
        try:
            if check_out_time_str:
                check_out_time_parts = check_out_time_str.split(':')
                check_out_hour = int(check_out_time_parts[0])
                check_out_minute = int(check_out_time_parts[1]) if len(check_out_time_parts) > 1 else 0
            else:
                check_out_hour, check_out_minute = now.hour, now.minute
        except:
            check_out_hour, check_out_minute = now.hour, now.minute
        
        check_in = datetime(check_in_date.year, check_in_date.month, check_in_date.day, check_in_hour, check_in_minute)
        check_out = datetime(check_out_date.year, check_out_date.month, check_out_date.day, check_out_hour, check_out_minute)
        actual_check_in = check_in
        
        stay_duration = (check_out.date() - check_in.date()).days
        
        if stay_duration < 1:
            flash('Check-out date must be after check-in date', 'danger')
            return render_template('new_booking.html', form=form, customers=customers)
        
        room = None
        if booking_category == 'wedding':
            wedding_rates = {'all_9_ac': Decimal('15000'), 'all_rooms': Decimal('17000')}
            package_rate = wedding_rates.get(wedding_package, Decimal('15000'))
            base_room_charge = package_rate * stay_duration
            extra_person_charge = 0
            number_of_persons = int(request.form.get('number_of_persons', 1))
        else:
            room = db.session.get(Room, room_id)
            if not room or room.status not in ['available', 'cleaning']:
                flash('Selected room is not available', 'danger')
                return render_template('new_booking.html', form=form, customers=customers)
            number_of_persons = int(request.form.get('number_of_persons', 1))
            extra_person_charge, extra_persons = calculate_extra_person_charge(room.room_type, number_of_persons, stay_duration)
            base_room_charge = Decimal(str((room.price_per_night or 0) * stay_duration))
        
        customer_obj = db.session.get(Customer, int(customer_id))
        gst_mode = request.form.get('gst_mode', 'exclude')
        
        company_billing = request.form.get('company_billing') == 'on'
        
        if company_billing:
            billing_name = form.billing_name.data.strip() if form.billing_name.data else None
            company_gst = request.form.get('company_gst', '').strip()
            company_address = request.form.get('company_address', '').strip()
            bill_payer_type = 'company'
            payer_name = billing_name
            payer_phone = None
            payer_address = company_address
        else:
            billing_name = customer_obj.name
            company_gst = None
            company_address = None
            bill_payer_type = 'guest'
            payer_name = customer_obj.name
            payer_phone = customer_obj.phone
            payer_address = customer_obj.address
        
        booking = Booking(
            booking_id=generate_booking_id(),
            customer_id=int(customer_id),
            room_id=room_id if booking_category == 'normal' else None,
            booking_category=booking_category,
            wedding_package=wedding_package,
            check_in=check_in,
            check_out=check_out,
            actual_check_in=actual_check_in,
            stay_duration=stay_duration,
            number_of_persons=number_of_persons,
            purpose_of_visit=form.purpose_of_visit.data,
            gst_mode=gst_mode,
            room_charge=base_room_charge,
            extra_person_charges=Decimal(str(extra_person_charge)),
            gst_rate=Decimal(str(gst_rate)),
            advance_amount=Decimal(str(form.advance_amount.data or 0)),
            billing_name=billing_name,
            company_gst=company_gst,
            company_address=company_address,
            bill_payer_type=bill_payer_type,
            payer_name=payer_name,
            payer_phone=payer_phone,
            payer_address=payer_address,
            notes=form.notes.data,
            status='checked_in',
            checked_in_by=current_user.id
        )
        
        total_room_charge = base_room_charge + Decimal(str(extra_person_charge))
        
        gst_rate_decimal = Decimal(str(gst_rate))
        if gst_mode == 'exclude':
            subtotal = total_room_charge
            booking.subtotal = subtotal
            booking.gst_amount = (subtotal * gst_rate_decimal) / 100
            booking.total_amount = subtotal + booking.gst_amount
        else:
            base_price = (total_room_charge * 100) / (100 + gst_rate_decimal)
            booking.subtotal = total_room_charge
            booking.gst_amount = total_room_charge - base_price
            booking.total_amount = total_room_charge
        
        booking.pending_amount = booking.total_amount - booking.advance_amount
        
        if room:
            room.status = 'occupied'
        
        customer_obj.total_stays += 1
        
        accompanying_ids = request.form.getlist('accompanying_person_ids')
        for ap_id in accompanying_ids:
            if ap_id:
                ap = db.session.get(AccompanyingPerson, int(ap_id))
                if ap:
                    ap.booking_id = booking.id
        
        db.session.add(booking)
        db.session.commit()
        
        log_activity('New Booking', f'Booking {booking.booking_id} created for room {room.room_number if room else "Wedding - " + wedding_package}')
        flash(f'Check-in successful! Booking ID: {booking.booking_id}', 'success')
        return redirect(url_for('bookings'))
    
    return render_template('new_booking.html', form=form, customers=customers)

@app.route('/bookings/<int:booking_id>')
@login_required
def booking_detail(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    room = db.session.get(Room, booking.room_id) if booking.room_id else None
    customer = db.session.get(Customer, booking.customer_id)
    
    if not customer:
        flash('Customer not found', 'danger')
        return redirect(url_for('bookings'))
    
    return render_template('booking_detail.html', booking=booking, room=room, customer=customer)

@app.route('/bookings/<int:booking_id>/checkout', methods=['GET', 'POST'])
@login_required
def checkout(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    
    if booking.status != 'checked_in':
        flash('This booking is not active', 'warning')
        return redirect(url_for('bookings'))
    
    # Handle checkout date/time update from query params
    checkout_date = request.args.get('checkout_date')
    checkout_time = request.args.get('checkout_time')
    if checkout_date:
        try:
            if checkout_time:
                time_parts = checkout_time.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                new_checkout = datetime.strptime(checkout_date, '%Y-%m-%d').replace(hour=hour, minute=minute)
            else:
                new_checkout = datetime.strptime(checkout_date, '%Y-%m-%d')
            
            booking.actual_check_out = new_checkout
            booking.check_out = new_checkout
            
            if booking.actual_check_in:
                new_duration = (new_checkout.date() - booking.actual_check_in.date()).days
                if new_duration < 1:
                    new_duration = 1
                booking.stay_duration = new_duration
            else:
                booking.stay_duration = 1
            
            db.session.commit()
            flash(f'Checkout date updated to {new_checkout.strftime("%d %b %Y %I:%M %p")}', 'success')
        except Exception as e:
            flash(f'Error updating checkout date: {str(e)}', 'danger')
    
    # Handle discount update from query params
    discount = request.args.get('discount')
    if discount is not None:
        try:
            discount_val = Decimal(str(discount))
            if discount_val < 0:
                raise ValueError('Discount cannot be negative')
            booking.discount = discount_val
            db.session.commit()
            flash(f'Discount updated to Rs. {discount}', 'success')
        except Exception as e:
            flash(f'Error updating discount: {str(e)}', 'danger')
    
    room = db.session.get(Room, booking.room_id) if booking.room_id else None
    customer = db.session.get(Customer, booking.customer_id)
    extra_form = ExtraChargeForm()
    payment_form = PaymentForm()
    
    bill_data = calculate_bill(booking)
    if 'error' in bill_data:
        flash(f'Error calculating bill: {bill_data["error"]}', 'warning')
    
    booking.extra_charges = Decimal(str(bill_data.get('extra_charges', 0)))
    booking.subtotal = Decimal(str(bill_data.get('subtotal', 0)))
    booking.gst_amount = Decimal(str(bill_data.get('gst_amount', 0)))
    booking.total_amount = Decimal(str(bill_data.get('total_amount', 0)))
    booking.pending_amount = Decimal(str(bill_data.get('pending_amount', 0)))
    db.session.commit()
    
    if extra_form.validate_on_submit() and 'add_extra_charge' in request.form:
        quantity = int(request.form.get('quantity', 1))
        charge = ExtraCharge(
            booking_id=booking.id,
            charge_type=extra_form.charge_type.data,
            description=extra_form.description.data,
            quantity=quantity,
            amount=Decimal(str(extra_form.amount.data * quantity)),
            created_by=current_user.id
        )
        db.session.add(charge)
        db.session.commit()
        
        bill_data = calculate_bill(booking)
        booking.extra_charges = Decimal(str(bill_data.get('extra_charges', 0)))
        booking.subtotal = Decimal(str(bill_data.get('subtotal', 0)))
        booking.gst_amount = Decimal(str(bill_data.get('gst_amount', 0)))
        booking.total_amount = Decimal(str(bill_data.get('total_amount', 0)))
        booking.pending_amount = Decimal(str(bill_data.get('pending_amount', 0)))
        db.session.commit()
        
        log_activity('Extra Charge', f'Added {extra_form.charge_type} charge to {booking.booking_id}')
        flash('Extra charge added', 'success')
        return redirect(url_for('checkout', booking_id=booking_id))
    
    if payment_form.validate_on_submit() and 'add_payment' in request.form:
        payment = Payment(
            booking_id=booking.id,
            amount=Decimal(str(payment_form.amount.data)),
            payment_method=payment_form.payment_method.data,
            transaction_id=payment_form.transaction_id.data,
            received_by=current_user.id
        )
        db.session.add(payment)
        
        booking.advance_amount += Decimal(str(payment_form.amount.data))
        booking.pending_amount = booking.total_amount - booking.advance_amount
        
        db.session.commit()
        log_activity('Payment', f'Payment of Rs. {payment_form.amount.data} received for {booking.booking_id}')
        flash('Payment recorded', 'success')
        return redirect(url_for('checkout', booking_id=booking_id))
    
    if request.method == 'POST' and 'process_checkout' in request.form:
        discount = float(request.form.get('discount', 0))
        now = datetime.now()
        
        manual_date = request.form.get('checkout_date', '')
        manual_time = request.form.get('checkout_time', '')
        
        if manual_date and manual_time:
            try:
                date_parts = manual_date.split('-')
                time_parts = manual_time.split(':')
                new_checkout = datetime(
                    int(date_parts[0]), int(date_parts[1]), int(date_parts[2]),
                    int(time_parts[0]), int(time_parts[1]))
                booking.actual_check_out = new_checkout
                
                if booking.actual_check_in:
                    new_duration = (new_checkout.date() - booking.actual_check_in.date()).days
                    if new_duration < 1:
                        new_duration = 1
                    booking.stay_duration = new_duration
                    booking.check_out = new_checkout
            except:
                booking.actual_check_out = now
        else:
            booking.actual_check_out = now
        
        booking.discount = Decimal(str(discount))
        booking.status = 'checked_out'
        booking.checked_out_by = current_user.id
        
        bill_data = calculate_bill(booking)
        booking.subtotal = Decimal(str(bill_data['subtotal']))
        booking.gst_amount = Decimal(str(bill_data['gst_amount']))
        booking.total_amount = Decimal(str(bill_data['total_amount']))
        booking.pending_amount = Decimal(str(bill_data['pending_amount']))
        
        for payment in booking.payments:
            if payment.payment_status == 'pending':
                payment.payment_status = 'completed'
        
        try:
            if room:
                room.status = 'cleaning'
        except:
            pass
        
        invoice = Invoice(
            invoice_number=generate_invoice_number(),
            booking_id=booking.id
        )
        db.session.add(invoice)
        db.session.commit()
        
        log_activity('Checkout', f'Booking {booking.booking_id} checked out')
        flash(f'Check-out successful! Invoice: {invoice.invoice_number}', 'success')
        return redirect(url_for('booking_detail', booking_id=booking_id))
    
    return render_template('checkout.html', booking=booking, room=room, customer=customer,
                         extra_form=extra_form, payment_form=payment_form, bill_data=bill_data)

@app.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    
    if booking.status == 'checked_out':
        return jsonify({'success': False, 'error': 'Cannot cancel checked-out booking'})
    
    room = db.session.get(Room, booking.room_id) if booking.room_id else None
    if room:
        room.status = 'available'
    booking.status = 'cancelled'
    db.session.commit()
    
    log_activity('Cancel Booking', f'Booking {booking.booking_id} cancelled')
    return jsonify({'success': True})

@app.route('/bookings/<int:booking_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    
    if booking.status != 'checked_in':
        flash('Only active bookings can be edited', 'warning')
        return redirect(url_for('booking_detail', booking_id=booking_id))
    
    room = db.session.get(Room, booking.room_id) if booking.room_id else None
    customer = db.session.get(Customer, booking.customer_id)
    
    if request.method == 'POST':
        new_check_in = request.form.get('check_in_date')
        new_check_out = request.form.get('check_out_date')
        new_persons = int(request.form.get('number_of_persons', 1))
        purpose_of_visit = request.form.get('purpose_of_visit', booking.purpose_of_visit)
        
        if new_check_in and new_check_out:
            check_in = datetime.strptime(new_check_in, '%Y-%m-%d')
            check_out = datetime.strptime(new_check_out, '%Y-%m-%d')
            stay_duration = (check_out.date() - check_in.date()).days
            
            if stay_duration < 1:
                flash('Check-out must be after check-in', 'danger')
                return redirect(url_for('edit_booking', booking_id=booking_id))
            
            booking.check_in = check_in
            booking.check_out = check_out
            booking.stay_duration = stay_duration
            booking.number_of_persons = new_persons
            booking.purpose_of_visit = purpose_of_visit
            
            if booking.booking_category == 'wedding':
                wedding_rates = {'all_9_ac': Decimal('15000'), 'all_rooms': Decimal('17000')}
                package_rate = wedding_rates.get(booking.wedding_package, Decimal('15000'))
                base_room_charge = package_rate * stay_duration
                extra_person_charge = 0
            else:
                base_room_charge = (room.price_per_night or 0) * stay_duration
                extra_person_charge, extra_persons = calculate_extra_person_charge(room.room_type, new_persons, stay_duration)
            
            booking.room_charge = Decimal(str(base_room_charge))
            booking.extra_person_charges = Decimal(str(extra_person_charge))
            
            gst_rate = float(Settings.get('gst_rate', '5'))
            booking.gst_rate = Decimal(str(gst_rate))
            
            subtotal = base_room_charge + extra_person_charge
            booking.subtotal = Decimal(str(subtotal))
            
            if booking.gst_mode == 'exclude':
                booking.gst_amount = (subtotal * Decimal(str(gst_rate))) / 100
                booking.total_amount = subtotal + booking.gst_amount
            else:
                base_price = (subtotal * 100) / (100 + Decimal(str(gst_rate)))
                booking.gst_amount = subtotal - base_price
                booking.total_amount = subtotal
            
            booking.pending_amount = booking.total_amount - booking.advance_amount
            
            db.session.commit()
            
            log_activity('Edit Booking', f'Booking {booking.booking_id} updated - {stay_duration} nights, {new_persons} persons')
            flash('Booking updated successfully!', 'success')
            return redirect(url_for('booking_detail', booking_id=booking_id))
    
    return render_template('edit_booking.html', booking=booking, room=room, customer=customer)

@app.route('/api/charges/<int:charge_id>', methods=['DELETE'])
@login_required
def delete_charge(charge_id):
    charge = db.get_or_404(ExtraCharge, charge_id)
    booking = db.session.get(Booking, charge.booking_id)
    
    db.session.delete(charge)
    db.session.commit()
    
    # Recalculate
    bill_data = calculate_bill(booking)
    booking.extra_charges = Decimal(str(bill_data['extra_charges']))
    booking.subtotal = Decimal(str(bill_data['subtotal']))
    booking.gst_amount = Decimal(str(bill_data['gst_amount']))
    booking.total_amount = Decimal(str(bill_data['total_amount']))
    booking.pending_amount = Decimal(str(bill_data['pending_amount']))
    db.session.commit()
    
    log_activity('Delete Charge', f'Deleted charge from {booking.booking_id}')
    return jsonify({'success': True})

@app.route('/bookings/<int:booking_id>/recalculate', methods=['POST'])
@login_required
def recalculate_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    bill_data = calculate_bill(booking)
    if 'error' in bill_data:
        flash(f'Error: {bill_data["error"]}', 'danger')
        return redirect(url_for('booking_detail', booking_id=booking_id))
    booking.subtotal = Decimal(str(bill_data['subtotal']))
    booking.gst_amount = Decimal(str(bill_data['gst_amount']))
    booking.total_amount = Decimal(str(bill_data['total_amount']))
    booking.pending_amount = Decimal(str(bill_data['pending_amount']))
    db.session.commit()
    log_activity('Recalculate Bill', f'Bill recalculated for {booking.booking_id}')
    flash('Bill recalculated successfully!', 'success')
    return redirect(url_for('booking_detail', booking_id=booking_id))

# ==================== INVOICES ====================

@app.route('/invoices')
@login_required
def invoices():
    invoices_list = Invoice.query.order_by(Invoice.generated_at.desc()).all()
    return render_template('invoices.html', invoices=invoices_list)

@app.route('/invoices/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    booking = db.session.get(Booking, invoice.booking_id)
    room = db.session.get(Room, booking.room_id) if booking.room_id else None
    customer = db.session.get(Customer, booking.customer_id)
    
    return render_template('invoice.html', invoice=invoice, booking=booking, room=room, customer=customer, now=datetime.now())

@app.route('/invoices/<int:invoice_id>/download')
@login_required
def download_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    booking = db.session.get(Booking, invoice.booking_id)
    room = db.session.get(Room, booking.room_id) if booking.room_id else None
    customer = db.session.get(Customer, booking.customer_id)
    
    html = render_template('invoice_pdf_standalone.html', invoice=invoice,
                           booking=booking, room=room, customer=customer,
                           now=datetime.now())
    
    pdf_buffer = BytesIO()
    weasyprint.HTML(string=html).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{invoice.invoice_number}.pdf'
    )

# ==================== PAYMENTS ====================

@app.route('/payments')
@login_required
def payments():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Join Booking to filter by check_in date
    query = Payment.query.join(Booking).options(
        joinedload(Payment.booking).joinedload(Booking.customer)
    ).order_by(Booking.check_in.desc())

    if date_from:
        try:
            query = query.filter(Booking.check_in >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            flash(f'Invalid "From" date format: {date_from}', 'error')
            date_from = None
    if date_to:
        try:
            # Using +1 day to include the entire check-in date
            query = query.filter(Booking.check_in <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            flash(f'Invalid "To" date format: {date_to}', 'error')
            date_to = None

    payments_list = query.all()
    return render_template('payments.html', payments=payments_list)

@app.route('/payments/export')
@login_required
def export_payments():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Join Booking to filter by check_in date
    query = Payment.query.join(Booking).options(
        joinedload(Payment.booking).joinedload(Booking.customer)
    ).order_by(Booking.check_in.desc())

    if date_from:
        try:
            query = query.filter(Booking.check_in >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Booking.check_in <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            pass

    payments_list = query.all()

    # Pre-process data to avoid lazy loading issues in the generator
    rows = []
    for payment in payments_list:
        rows.append([
            payment.booking.customer.name if payment.booking and payment.booking.customer else '-',
            payment.booking.booking_id if payment.booking else '-',
            payment.booking.customer.phone if payment.booking and payment.booking.customer else '-',
            payment.booking.customer.id_proof_number if payment.booking and payment.booking.customer else '-',
            payment.booking.check_in.strftime('%d %b %Y') if payment.booking else '-',
            payment.booking.check_in.strftime('%I:%M %p') if payment.booking else '-',
            payment.booking.check_out.strftime('%d %b %Y') if payment.booking else '-',
            payment.booking.check_out.strftime('%I:%M %p') if payment.booking else '-',
            f"{int(payment.amount)}"
        ])

    def generate():
        data = io.StringIO()
        writer = csv.writer(data)

        # Header
        writer.writerow(['Name', 'Booking ID', 'Phone Number', 'ID Proof', 'Check-in Date', 'Check-in Time', 'Check-out Date', 'Check-out Time', 'Amount Paid'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        for row in rows:
            writer.writerow(row)
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response = Response(generate(), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename=f'payments_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    return response

# ==================== EXPENSES ====================

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    form = ExpenseForm()
    
    if form.validate_on_submit():
        expense = Expense(
            category=form.category.data,
            description=form.description.data,
            amount=Decimal(str(form.amount.data)),
            expense_date=form.expense_date.data,
            added_by=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        log_activity('Expense', f'Expense of Rs. {form.amount.data} added ({form.category})')
        flash('Expense added successfully', 'success')
        return redirect(url_for('expenses'))
    
    expenses_list = Expense.query.order_by(Expense.expense_date.desc()).limit(100).all()
    return render_template('expenses.html', form=form, expenses=expenses_list)

@app.route('/api/expenses/total')
@login_required
def api_expenses_total():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    total = db.session.query(db.func.sum(Expense.amount)).filter(
        db.extract('month', Expense.expense_date) == month,
        db.extract('year', Expense.expense_date) == year
    ).scalar() or 0
    
    return jsonify({'total': float(total)})

# ==================== REPORTS ====================

@app.route('/reports')
@login_required
def reports():
    month = datetime.now().month
    year = datetime.now().year
    start_date = datetime(year, month, 1)
    end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    
    revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.created_at >= start_date,
        Payment.created_at < end_date,
        Payment.payment_status == 'completed'
    ).scalar() or 0
    
    expenses_total = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.expense_date >= start_date.date(),
        Expense.expense_date < end_date.date()
    ).scalar() or 0
    
    bookings_count = Booking.query.filter(
        Booking.created_at >= start_date,
        Booking.created_at < end_date
    ).count()
    
    profit = float(revenue) - float(expenses_total)
    
    return render_template('reports.html', 
        revenue=float(revenue), 
        expenses_total=float(expenses_total),
        profit=profit,
        bookings_count=bookings_count
    )

@app.route('/reports/revenue')
@login_required
def revenue_report():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Revenue
    revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.created_at >= start_date,
        Payment.created_at < end_date,
        Payment.payment_status == 'completed'
    ).scalar() or 0
    
    # Expenses
    expenses_total = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.expense_date >= start_date.date(),
        Expense.expense_date < end_date.date()
    ).scalar() or 0
    
    # Bookings count
    bookings_count = Booking.query.filter(
        Booking.created_at >= start_date,
        Booking.created_at < end_date
    ).count()
    
    profit = float(revenue) - float(expenses_total)
    
    # Daily breakdown
    daily_data = []
    for day in range(1, 32):
        try:
            current_date = datetime(year, month, day)
        except ValueError:
            break
        
        day_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            db.extract('year', Payment.created_at) == year,
            db.extract('month', Payment.created_at) == month,
            db.extract('day', Payment.created_at) == day,
            Payment.payment_status == 'completed'
        ).scalar() or 0
        
        day_expense = db.session.query(db.func.sum(Expense.amount)).filter(
            db.extract('year', Expense.expense_date) == year,
            db.extract('month', Expense.expense_date) == month,
            db.extract('day', Expense.expense_date) == day
        ).scalar() or 0
        
        daily_data.append({
            'date': current_date.strftime('%d %b'),
            'revenue': float(day_revenue),
            'expense': float(day_expense),
            'profit': float(day_revenue) - float(day_expense)
        })
    
    return render_template('revenue_report.html', 
                         revenue=float(revenue), 
                         expenses=float(expenses_total),
                         profit=profit,
                         bookings_count=bookings_count,
                         daily_data=daily_data,
                         month=month,
                         year=year)

@app.route('/reports/occupancy')
@login_required
def occupancy_report():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    # Calculate occupancy
    days_in_month = (datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1) - timedelta(days=1)).day
    
    bookings = Booking.query.filter(
        db.or_(
            db.and_(
                db.extract('year', Booking.check_in) == year,
                db.extract('month', Booking.check_in) <= month
            ),
            db.and_(
                db.extract('year', Booking.check_out) >= year,
                db.extract('month', Booking.check_out) >= month
            )
        )
    ).all()
    
    # Room-wise occupancy
    room_stats = []
    for room in Room.query.order_by(Room.room_number).all():
        room_bookings = [b for b in bookings if b.room_id == room.id and b.status == 'checked_out']
        occupied_days = sum(b.stay_duration for b in room_bookings)
        rate = (occupied_days / (days_in_month * 12)) * 100 if days_in_month > 0 else 0
        room_stats.append({
            'room': room,
            'bookings': len(room_bookings),
            'occupied_days': occupied_days,
            'rate': rate
        })
    
    total_occupied = sum(r['occupied_days'] for r in room_stats)
    total_rate = (total_occupied / (days_in_month * 12)) * 100 if days_in_month > 0 else 0
    
    # Type averages
    type_averages = {}
    for rt in ['standard', 'deluxe', 'suite']:
        type_rooms = [r for r in room_stats if r['room'].room_type == rt]
        if type_rooms:
            type_averages[rt] = sum(r['rate'] for r in type_rooms) / len(type_rooms)
        else:
            type_averages[rt] = 0
    
    return render_template('occupancy_report.html',
                         room_stats=room_stats,
                         total_rate=total_rate,
                         days_in_month=days_in_month,
                         month=month,
                         year=year,
                         type_averages=type_averages)

@app.route('/api/reports/export')
@login_required
def export_report():
    report_type = request.args.get('type', 'revenue')
    try:
        month = int(request.args.get('month', datetime.now().month))
    except (ValueError, TypeError):
        month = datetime.now().month
    try:
        year = int(request.args.get('year', datetime.now().year))
    except (ValueError, TypeError):
        year = datetime.now().year
    
    if report_type == 'revenue':
        start_date = datetime(year, month, 1)
        end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        
        payments = Payment.query.filter(
            Payment.created_at >= start_date,
            Payment.created_at < end_date,
            Payment.payment_status == 'completed'
        ).all()
        
        # Create Excel-like CSV
        csv = 'Date,Amount,Method,Received By\n'
        for p in payments:
            csv += f'{p.created_at.strftime("%Y-%m-%d")},{p.amount},{p.payment_method},{p.received_by_staff.name if p.received_by_staff else "N/A"}\n'
        
        return csv, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=revenue_report_{month}_{year}.csv'
        }
    
    return '', 400

# ==================== STAFF ====================

@app.route('/staff')
@login_required
@admin_required
def staff():
    staff_list = Staff.query.order_by(Staff.created_at.desc()).all()
    return render_template('staff.html', staff_list=staff_list)

@app.route('/staff/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_staff():
    form = StaffForm()
    
    if form.validate_on_submit():
        staff = Staff(
            username=form.username.data,
            name=form.name.data,
            role=form.role.data
        )
        staff.set_password(form.password.data)
        db.session.add(staff)
        db.session.commit()
        log_activity('New Staff', f'Staff {staff.name} added by {current_user.name}')
        flash('Staff added successfully', 'success')
        return redirect(url_for('staff'))
    
    return render_template('new_staff.html', form=form)

@app.route('/staff/<int:staff_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_staff(staff_id):
    staff = db.get_or_404(Staff, staff_id)
    
    if staff.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot deactivate yourself'})
    
    staff.is_active = not staff.is_active
    db.session.commit()
    
    status = 'activated' if staff.is_active else 'deactivated'
    log_activity('Staff Status', f'Staff {staff.name} {status}')
    
    return jsonify({'success': True, 'is_active': staff.is_active})

@app.route('/activity-log')
@login_required
@admin_required
def activity_log():
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(100).all()
    return render_template('activity_log.html', logs=logs)

# ==================== HISTORY ====================

@app.route('/history')
@login_required
def history():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    history_type = request.args.get('type', 'all')
    
    # Default to last 30 days
    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to - timedelta(days=30)
    
    try:
        date_from = datetime.strptime(str(date_from), '%Y-%m-%d') if isinstance(date_from, str) else datetime.combine(date_from, datetime.min.time())
        date_to = datetime.strptime(str(date_to), '%Y-%m-%d') if isinstance(date_to, str) else datetime.combine(date_to, datetime.max.time())
    except ValueError:
        date_from = datetime.combine(date.today() - timedelta(days=30), datetime.min.time())
        date_to = datetime.combine(date.today(), datetime.max.time())
    
    # Fetch bookings (only checked_out)
    if history_type in ['all', 'bookings']:
        bookings = Booking.query.filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to,
            Booking.status == 'checked_out'
        ).order_by(Booking.created_at.desc()).all()
    else:
        bookings = []
    
    # Fetch payments
    if history_type in ['all', 'payments']:
        payments = Payment.query.filter(
            Payment.created_at >= date_from,
            Payment.created_at <= date_to
        ).order_by(Payment.created_at.desc()).all()
    else:
        payments = []
    
    # Fetch expenses
    if history_type in ['all', 'expenses']:
        expenses = Expense.query.filter(
            Expense.expense_date >= date_from.date(),
            Expense.expense_date <= date_to.date()
        ).order_by(Expense.expense_date.desc()).all()
    else:
        expenses = []
    
    # Fetch activity logs
    if history_type in ['all', 'activity']:
        activities = ActivityLog.query.filter(
            ActivityLog.created_at >= date_from,
            ActivityLog.created_at <= date_to
        ).order_by(ActivityLog.created_at.desc()).limit(200).all()
    else:
        activities = []
    
    # Calculate totals
    total_revenue = sum(float(p.amount) for p in payments if p.payment_status == 'completed')
    total_expenses = sum(float(e.amount) for e in expenses)
    total_bookings = len(bookings)
    checked_out_count = len(bookings)  # All bookings are now checked_out
    
    return render_template('history.html', 
        bookings=bookings,
        payments=payments,
        expenses=expenses,
        activities=activities,
        date_from=date_from.strftime('%Y-%m-%d'),
        date_to=date_to.strftime('%Y-%m-%d'),
        history_type=history_type,
        totals={
            'revenue': total_revenue,
            'expenses': total_expenses,
            'bookings': total_bookings,
            'checked_out': checked_out_count,
            'profit': total_revenue - total_expenses
        }
    )

# ==================== SETTINGS ====================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        if 'change_password' in request.form:
            current_pass = request.form.get('current_password')
            new_pass = request.form.get('new_password')
            confirm_pass = request.form.get('confirm_password')
            
            if not current_user.check_password(current_pass):
                flash('Current password is incorrect', 'danger')
            elif new_pass != confirm_pass:
                flash('New passwords do not match', 'danger')
            elif len(new_pass) < 6:
                flash('Password must be at least 6 characters', 'danger')
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                log_activity('Password Change', 'Password changed')
                flash('Password changed successfully', 'success')
        
        elif 'upload_logo' in request.files:
            file = request.files['upload_logo']
            if file and allowed_file(file.filename):
                filename = 'logo.png'
                file.save(os.path.join('static', filename))
                flash('Logo updated', 'success')
        
        elif 'update_hotel' in request.form:
            Settings.set('hotel_name', request.form.get('hotel_name', ''))
            Settings.set('hotel_address', request.form.get('hotel_address', ''))
            Settings.set('hotel_phone', request.form.get('hotel_phone', ''))
            Settings.set('hotel_email', request.form.get('hotel_email', ''))
            Settings.set('hotel_gst', request.form.get('hotel_gst', ''))
            Settings.set('hotel_owner', request.form.get('hotel_owner', ''))
            flash('Hotel information updated', 'success')
        
        elif 'update_prices' in request.form:
            Settings.set('price_classic', request.form.get('price_classic', '1500'))
            Settings.set('price_deluxe', request.form.get('price_deluxe', '2500'))
            Settings.set('price_suite', request.form.get('price_suite', '4000'))
            Settings.set('extra_person_charge', request.form.get('extra_person_charge', '300'))
            flash('Room prices updated', 'success')
        
        elif 'update_gst' in request.form:
            Settings.set('gst_rate', request.form.get('gst_rate', '5'))
            flash('GST rate updated', 'success')
    
    hotel_settings = {
        'hotel_name': Settings.get('hotel_name', 'HOTEL SHRI GOVIND'),
        'hotel_address': Settings.get('hotel_address', ''),
        'hotel_phone': Settings.get('hotel_phone', ''),
        'hotel_email': Settings.get('hotel_email', 'hotelshrigovind06@gmail.com'),
        'hotel_gst': Settings.get('hotel_gst', '22AATFH3393Q1ZL'),
        'hotel_owner': Settings.get('hotel_owner', 'Akshay Shukla'),
        'gst_rate': Settings.get('gst_rate', '5'),
        'price_classic': Settings.get('price_classic', '1500'),
        'price_deluxe': Settings.get('price_deluxe', '2500'),
        'price_suite': Settings.get('price_suite', '4000'),
        'extra_person_charge': Settings.get('extra_person_charge', '300'),
    }
    
    rooms_list = Room.query.order_by(Room.room_number).all()
    
    return render_template('settings.html', hotel_settings=hotel_settings, rooms=rooms_list)

@app.route('/settings/reset-data', methods=['POST'])
@login_required
def reset_all_data():
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Only admin can reset data'})
    
    try:
        db.session.query(Payment).delete()
        db.session.query(ExtraCharge).delete()
        db.session.query(Invoice).delete()
        db.session.query(Booking).delete()
        db.session.query(AccompanyingPerson).delete()
        db.session.query(Customer).delete()
        db.session.query(ActivityLog).delete()
        db.session.query(Expense).delete()
        
        room_ids = [r.id for r in Room.query.all()]
        for room in Room.query.all():
            room.status = 'available'
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings/setup-rooms', methods=['POST'])
@login_required
def setup_rooms():
    if not current_user.is_admin():
        flash('Only admin can setup rooms', 'danger')
        return redirect(url_for('settings'))
    
    Room.query.delete()
    
    classic_price = int(Settings.get('price_classic', '1500'))
    deluxe_price = int(Settings.get('price_deluxe', '2500'))
    suite_price = int(Settings.get('price_suite', '4000'))
    
    rooms_config = [
        ('101', 'classic', classic_price, 0),
        ('102', 'classic', classic_price, 0),
        ('103', 'classic', classic_price, 0),
        ('201', 'deluxe', deluxe_price, 1),
        ('202', 'deluxe', deluxe_price, 1),
        ('203', 'deluxe', deluxe_price, 1),
        ('301', 'deluxe', deluxe_price, 2),
        ('302', 'deluxe', deluxe_price, 2),
        ('303', 'deluxe', deluxe_price, 2),
        ('401', 'suite', suite_price, 3),
        ('402', 'suite', suite_price, 3),
        ('403', 'suite', suite_price, 3),
    ]
    
    for room_number, room_type, price, floor in rooms_config:
        amenities = '["AC", "TV", "WiFi", "Hot Water"]' if room_type in ['deluxe', 'suite'] else '["TV", "WiFi", "Hot Water"]'
        room = Room(
            room_number=room_number,
            room_type=room_type,
            price_per_night=price,
            status='available',
            floor=floor,
            amenities=amenities
        )
        db.session.add(room)
    
    db.session.commit()
    flash('Rooms setup completed! 12 rooms created.', 'success')
    return redirect(url_for('rooms'))

# ==================== API ENDPOINTS ====================

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    today = date.today()
    
    today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        db.extract('year', Payment.created_at) == today.year,
        db.extract('month', Payment.created_at) == today.month,
        db.extract('day', Payment.created_at) == today.day,
        Payment.payment_status == 'completed'
    ).scalar() or 0
    
    occupied = Room.query.filter_by(status='occupied').count()
    
    pending = db.session.query(db.func.sum(Booking.pending_amount)).filter(
        Booking.status == 'checked_in'
    ).scalar() or 0
    
    checkouts = Booking.query.filter(
        db.extract('year', Booking.check_out) == today.year,
        db.extract('month', Booking.check_out) == today.month,
        db.extract('day', Booking.check_out) == today.day,
        Booking.status == 'checked_in'
    ).count()
    
    return jsonify({
        'today_revenue': float(today_revenue),
        'occupancy': occupied,
        'pending': float(pending),
        'checkouts': checkouts
    })

@app.route('/api/rooms/available')
@login_required
def api_available_rooms():
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    if not check_in or not check_out:
        rooms = Room.query.filter_by(status='available').all()
    else:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
        
        booked_room_ids = [b.room_id for b in Booking.query.filter(
            Booking.status == 'checked_in',
            Booking.check_in < check_out_date,
            Booking.check_out > check_in_date
        ).all()]
        
        rooms = Room.query.filter(
            Room.status == 'available',
            ~Room.id.in_(booked_room_ids)
        ).all()
    
    gst_rate = float(Settings.get('gst_rate', '5'))
    return jsonify([{
        'id': r.id,
        'room_number': r.room_number,
        'room_type': r.room_type,
        'price': float(r.price_per_night) * (1 + gst_rate/100)
    } for r in rooms])

# ==================== INITIALIZATION ====================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Initialize settings
        init_settings()
        
        # Create admin user if not exists
        if not Staff.query.filter_by(username='admin').first():
            admin = Staff(
                username='admin',
                name='Administrator',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Create default rooms if not exists
        if Room.query.count() == 0:
            classic_price = int(Settings.get('price_classic', '1500'))
            deluxe_price = int(Settings.get('price_deluxe', '2500'))
            suite_price = int(Settings.get('price_suite', '4000'))
            
            rooms_config = [
                # Ground Floor - Classic/Non-AC (101, 102, 103)
                ('101', 'classic', classic_price, 0),
                ('102', 'classic', classic_price, 0),
                ('103', 'classic', classic_price, 0),
                # 1st Floor - Deluxe/AC (201, 202, 203)
                ('201', 'deluxe', deluxe_price, 1),
                ('202', 'deluxe', deluxe_price, 1),
                ('203', 'deluxe', deluxe_price, 1),
                # 2nd Floor - Deluxe/AC (301, 302, 303)
                ('301', 'deluxe', deluxe_price, 2),
                ('302', 'deluxe', deluxe_price, 2),
                ('303', 'deluxe', deluxe_price, 2),
                # 3rd Floor - Suite (401, 402, 403)
                ('401', 'suite', suite_price, 3),
                ('402', 'suite', suite_price, 3),
                ('403', 'suite', suite_price, 3),
            ]
            
            for room_number, room_type, price, floor in rooms_config:
                amenities = '["AC", "TV", "WiFi", "Hot Water"]' if room_type in ['deluxe', 'suite'] else '["TV", "WiFi", "Hot Water"]'
                room = Room(
                    room_number=room_number,
                    room_type=room_type,
                    price_per_night=price,
                    status='available',
                    floor=floor,
                    amenities=amenities
                )
                db.session.add(room)
        
        db.session.commit()
        print("Database initialized!")

def migrate_database():
    from sqlalchemy import text
    try:
        conn = db.engine.connect()
        trans = conn.begin()
        
        # Check if PostgreSQL or SQLite
        dialect = db.engine.dialect.name
        
        def table_exists(table_name):
            if dialect == 'postgresql':
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"
                ), {'t': table_name})
                return result.scalar()
            else:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=:t"
                ), {'t': table_name})
                return result.fetchone() is not None
        
        def get_columns(table_name):
            if dialect == 'postgresql':
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
                ), {'t': table_name})
                return [row[0] for row in result.fetchall()]
            else:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                return [row[1] for row in result.fetchall()]
        
        if not table_exists('bookings'):
            trans.commit()
            print("No existing database, skipping migration...")
            return
        
        bookings_columns = get_columns('bookings')
        
        migration_columns = [
            ('billing_name', "ALTER TABLE bookings ADD COLUMN billing_name VARCHAR(200)"),
            ('company_gst', "ALTER TABLE bookings ADD COLUMN company_gst VARCHAR(20)"),
            ('company_address', "ALTER TABLE bookings ADD COLUMN company_address TEXT"),
            ('number_of_persons', "ALTER TABLE bookings ADD COLUMN number_of_persons INTEGER DEFAULT 1"),
            ('gst_mode', "ALTER TABLE bookings ADD COLUMN gst_mode VARCHAR(20) DEFAULT 'exclude'"),
            ('extra_person_charges', "ALTER TABLE bookings ADD COLUMN extra_person_charges DECIMAL(10,3) DEFAULT 0"),
            ('bill_payer_type', "ALTER TABLE bookings ADD COLUMN bill_payer_type VARCHAR(20) DEFAULT 'guest'"),
            ('payer_name', "ALTER TABLE bookings ADD COLUMN payer_name VARCHAR(200)"),
            ('payer_phone', "ALTER TABLE bookings ADD COLUMN payer_phone VARCHAR(20)"),
            ('payer_address', "ALTER TABLE bookings ADD COLUMN payer_address TEXT"),
            ('purpose_of_visit', "ALTER TABLE bookings ADD COLUMN purpose_of_visit VARCHAR(50)"),
            ('booking_category', "ALTER TABLE bookings ADD COLUMN booking_category VARCHAR(20) DEFAULT 'normal'"),
            ('wedding_package', "ALTER TABLE bookings ADD COLUMN wedding_package VARCHAR(20)"),
        ]
        
        for col_name, alter_sql in migration_columns:
            if col_name not in bookings_columns:
                conn.execute(text(alter_sql))
                print(f"Added {col_name} column to bookings")
        
        customers_columns = get_columns('customers')
        
        if 'age' not in customers_columns:
            conn.execute(text("ALTER TABLE customers ADD COLUMN age INTEGER"))
            print("Added age column to customers")
        
        if 'number_of_children' not in customers_columns:
            conn.execute(text("ALTER TABLE customers ADD COLUMN number_of_children INTEGER DEFAULT 0"))
            print("Added number_of_children column to customers")
        
        if table_exists('extra_charges'):
            extra_charges_columns = get_columns('extra_charges')
            if 'quantity' not in extra_charges_columns:
                conn.execute(text("ALTER TABLE extra_charges ADD COLUMN quantity INTEGER DEFAULT 1"))
                print("Added quantity column to extra_charges")
        
        if not table_exists('accompanying_persons'):
            if dialect == 'postgresql':
                conn.execute(text("""
                    CREATE TABLE accompanying_persons (
                        id SERIAL PRIMARY KEY,
                        customer_id INTEGER NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        phone VARCHAR(20),
                        age INTEGER,
                        id_proof_type VARCHAR(20),
                        id_proof_number VARCHAR(50),
                        booking_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers(id),
                        FOREIGN KEY (booking_id) REFERENCES bookings(id)
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE accompanying_persons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        phone VARCHAR(20),
                        age INTEGER,
                        id_proof_type VARCHAR(20),
                        id_proof_number VARCHAR(50),
                        booking_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers(id),
                        FOREIGN KEY (booking_id) REFERENCES bookings(id)
                    )
                """))
            print("Created accompanying_persons table")
        else:
            acc_columns = get_columns('accompanying_persons')
            if 'booking_id' not in acc_columns:
                conn.execute(text("ALTER TABLE accompanying_persons ADD COLUMN booking_id INTEGER"))
                print("Added booking_id column to accompanying_persons")
        
        trans.commit()
        print("Migration completed!")
    except Exception as e:
        try:
            trans.rollback()
        except:
            pass
        print(f"Migration error: {e}")

if __name__ == '__main__':
    with app.app_context():
        migrate_database()
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
