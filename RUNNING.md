# AI Massage Booking System - Application Running! 🚀

## ✅ Both Applications Are Live!

**Frontend:** http://localhost:3000  
**Backend API:** http://localhost:5000

---

## Current Status

### Backend (Flask)
- ✅ Running on http://localhost:5000
- ✅ Database created (SQLite)
- ✅ Migrations applied
- ⚠️ No sample data yet (empty database)

### Frontend (Next.js)
- ✅ Running on http://localhost:3000
- ✅ Connected to backend API
- ✅ All pages functional

---

## Next Steps

### 1. Add Sample Data

You can add sample data manually via API:

**Create a Shop:**
```bash
curl -X POST http://localhost:5000/api/admin/shops \
  -H "Content-Type: application/json" \
  -d '{
    "shopName": "ABC Spa",
    "address": "123 Main Street, District 1, HCMC",
    "phoneNumber": "0123456789",
    "openTime": "08:00",
    "closeTime": "21:00"
  }'
```

**Create Courses:**
```bash
# Thai Massage
curl -X POST http://localhost:5000/api/admin/shops/1/courses \
  -H "Content-Type: application/json" \
  -d '{
    "courseName": "Thai Massage",
    "duration": 60,
    "price": 500000,
    "courseType": "main"
  }'

# Swedish Massage
curl -X POST http://localhost:5000/api/admin/shops/1/courses \
  -H "Content-Type: application/json" \
  -d '{
    "courseName": "Swedish Massage",
    "duration": 90,
    "price": 700000,
    "courseType": "main"
  }'

# Aromatherapy (addon)
curl -X POST http://localhost:5000/api/admin/shops/1/courses \
  -H "Content-Type: application/json" \
  -d '{
    "courseName": "Aromatherapy",
    "duration": 30,
    "price": 200000,
    "courseType": "addon"
  }'
```

**Create Therapists:**
```bash
curl -X POST http://localhost:5000/api/admin/shops/1/therapists \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Anna Nguyen",
    "gender": "Female",
    "phoneNumber": "0987654321"
  }'
```

### 2. Test the Booking Flow

1. Open http://localhost:3000
2. Click "Book Now"
3. Select shop, date, guests, services
4. Complete booking with phone number

### 3. View Bookings

1. Go to http://localhost:3000/my-bookings
2. Enter your phone number
3. View/cancel bookings

---

## API Endpoints Available

### Public (No Auth)
- `GET /api/shops` - List all shops
- `GET /api/shops/{id}` - Get shop details
- `GET /api/shops/{id}/courses` - Get courses
- `GET /api/shops/{id}/available-slots` - Find available slots
- `POST /api/bookings` - Create booking
- `GET /api/bookings?phone=xxx` - Get bookings by phone

### Admin (No Auth Required for Testing)
- `POST /api/admin/shops` - Create shop
- `POST /api/admin/shops/{id}/courses` - Create course
- `POST /api/admin/shops/{id}/therapists` - Create therapist

---

## Database Location

SQLite database: `spa-booking-api/instance/spa_booking.db`

You can inspect it with:
```bash
sqlite3 instance/spa_booking.db
.tables
SELECT * FROM shops;
```

---

## Stopping the Applications

**Stop Backend:**
```bash
pkill -f "python run.py"
```

**Stop Frontend:**
```bash
pkill -f "next dev"
```

---

## Troubleshooting

**Backend not responding?**
```bash
cd spa-booking-api
source venv/bin/activate
python run.py
```

**Frontend not responding?**
```bash
cd spa-booking-frontend
npm run dev
```

**Check if services are running:**
```bash
curl http://localhost:5000/api/shops
curl http://localhost:3000
```

---

## Features Working

✅ Shop listings  
✅ Course browsing  
✅ Multi-step booking wizard  
✅ Phone number lookup  
✅ Booking creation  
✅ Booking management  
✅ Available slot checking  
✅ Therapist selection  
✅ Responsive UI  

---

## Ready to Use!

Visit **http://localhost:3000** to start using the application.

Add sample data using the curl commands above, then test the full booking flow!
