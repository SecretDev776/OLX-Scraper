# OLX Scraper

A full-stack web application for scraping and managing OLX listings with a modern React frontend and FastAPI backend.

## Features

-  Real-time OLX listing scraping
-  Interactive dashboard for viewing listings
-  Secure authentication system
-  Responsive design
-  Statistics tracking
-  Export functionality (CSV)
-  Unseen listings tracking
-  Search and filter capabilities

## Tech Stack

### Frontend
- React 18
- TypeScript
- React Router
- Axios
- CSS3

### Backend
- FastAPI
- Python 3.8+
- Selenium
- Pandas
- JWT Authentication

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- Chrome browser (for Selenium)
- ChromeDriver (matching your Chrome version)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SecretDev776/OLX-Scraper.git
cd OLX-Scraper
```

2. Set up the backend:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

3. Set up the frontend:
```bash
cd frontend
npm install
```

## Configuration

1. Backend (.env):
```env
ENVIRONMENT=development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

2. Frontend (.env):
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_FRONTEND_URL=http://localhost:3000
```

## Running the Application

1. Start the backend server:
```bash
# From the root directory
python main.py
```

2. Start the frontend development server:
```bash
# From the frontend directory
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Usage

1. Login:
   - Username: admin
   - Password: admin123

2. Dashboard Features:
   - View all listings
   - Filter unseen listings
   - Search by title, location, or price
   - Export listings to CSV
   - Mark listings as seen
   - Scrape new listings

3. API Endpoints:
   - POST /token - Get authentication token
   - GET /listings - Get all listings
   - POST /scrape - Scrape new listings
   - POST /listings/mark-seen - Mark listings as seen
   - POST /listings/export - Export listings

## Project Structure

```
olx-scraper/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   └── App.tsx
│   └── package.json
├── main.py
├── scraper.py
├── scheduler.py
└── requirements.txt
```

## Development

### Backend Development
- FastAPI provides automatic API documentation at http://localhost:8000/docs
- Use the interactive Swagger UI to test endpoints
- Check logs in the console for debugging

### Frontend Development
- React DevTools for component inspection
- Chrome DevTools for debugging
- Hot reloading enabled for development

## Testing

1. Backend Testing:
```bash
# Run FastAPI server
python main.py

# Test API endpoints
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

2. Frontend Testing:
- Open http://localhost:3000 in your browser
- Use Chrome DevTools for debugging
- Check Network tab for API requests
- Verify authentication flow

## Security Features

- JWT-based authentication
- Password hashing
- CORS protection
- Environment variable configuration
- Secure session management


