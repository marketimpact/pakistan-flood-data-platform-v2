# Pakistan Flood Data Platform

**An open-source flood monitoring platform developed by MarketImpact Digital Solutions**

A production-ready Django web platform that integrates with Google Flood Hub to provide real-time flood monitoring for Pakistan, featuring a public dashboard for data viewing and a secure admin interface for data management.

## 🚀 Demo & Documentation

> **Note**: The original demo deployment has been decommissioned. You can deploy your own instance using the instructions below.

- **Repository**: https://github.com/marketimpact/pakistan-flood-data-platform
- **Documentation**: See `/docs` folder for detailed documentation
- **API Specification**: OpenAPI/Swagger available at `/api/docs/` when deployed

## ⚡ Key Features

✅ **Public Dashboard** - Real-time flood monitoring data accessible to everyone  
✅ **Admin-Only Data Management** - Secure data collection operations  
✅ **Google Flood Hub Integration** - Real Pakistan flood gauge network (2,391 gauges)  
✅ **REST API** - Complete API with authentication and documentation  
✅ **Production Ready** - Deployed on Render.com with PostgreSQL  

## 🌊 Pakistan Flood Monitoring Network

This platform integrates with **Google Flood Hub** using Pakistan's actual virtual gauge network:

## What This Platform Provides

### 🌐 **Public Dashboard Features**
- **Real-time monitoring** - View all 2,391 Pakistan flood gauges
- **Geographic filtering** - Filter by province (Punjab, Sindh, Balochistan, KP, etc.)
- **Status filtering** - Critical, Warning, Stale, No Data alerts
- **Data export** - CSV export of all readings
- **Responsive design** - Works on desktop and mobile

### 🔐 **Admin-Only Features** (Login Required)
- **Data collection** - Fetch forecast data from Google Flood Hub
- **Daily updates** - Update readings across all gauges
- **Admin actions** - Convenient one-click operations from Django admin
- **User management** - Create and manage user accounts

### 📊 **API Features**
- **RESTful endpoints** - Complete CRUD operations
- **Authentication** - Session-based security
- **Documentation** - Auto-generated OpenAPI/Swagger docs
- **Rate limiting** - Production-ready API controls

### 🗄️ **Data Models**
- **Gauges** - 2,391 virtual monitoring stations across Pakistan
- **Readings** - Historical water level and flow rate measurements  
- **Predictions** - Future flood forecasts and risk assessments
- **Geographic data** - Province, district, tehsil administrative boundaries

## Real Google Flood Hub Data

The platform accesses Pakistan's actual Google Flood Hub network of 2,391 virtual gauges:

### Network Composition
- **2,391 total virtual gauges** across Pakistan
- **34 quality-verified gauges** (1.4% verification rate)  
- **100% AI-powered** using HYBAS watershed framework
- **LSTM neural networks** for flood prediction

### Geographic Distribution
- **Northern Pakistan** (≥32°N): 940 gauges (39.3%) - 10 quality verified
- **Central Pakistan** (28-32°N): 853 gauges (35.7%) - 16 quality verified
- **Southern Pakistan** (<28°N): 598 gauges (25.0%) - 8 quality verified

### Technology Stack
- **HydroBASINS (HYBAS)**: Watershed boundary framework
- **NASA IMERG**: Satellite precipitation data
- **ECMWF ERA5**: Weather reanalysis data
- **Google DeepMind**: Weather forecasting models

## Technology Stack

- **Backend**: Django 5.2, Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: HTML/CSS with responsive design
- **API Documentation**: drf-spectacular (Swagger)
- **Deployment**: Render.com with automated builds
- **Testing**: Django test framework with TDD approach

## 🔑 Authentication & Access

### Public Access (No Login Required)
- **Dashboard**: https://flood-data-platform.onrender.com/ - View all flood data
- **Data Export**: Direct CSV download from dashboard
- **API Documentation**: Browse API endpoints and schemas

### Admin Access (Login Required)
- **Default Username**: admin
- **Default Password**: Set via ADMIN_PASS environment variable
- **Admin Panel**: `/admin/` (customizable via settings)
- **Data Operations**: Collect forecast data, update readings, manage users

> **Security Note**: Always change default credentials in production deployments

### Security Model
- **Public Dashboard**: Read-only access to flood monitoring data
- **Admin Operations**: Secure, authenticated access for data management
- **API Access**: Session-based authentication required for data modification

## API Access

- **Base URL**: https://flood-data-platform.onrender.com/api/v1/
- **Documentation**: https://flood-data-platform.onrender.com/api/docs/
- **Authentication**: Session-based (login required)

### Available Endpoints
- `GET /api/v1/gauges/` - List all flood gauges
- `GET /api/v1/readings/` - List all water level readings
- `GET /api/v1/predictions/` - List all predictions

## 🔄 Data Collection & Management

### Current Implementation (Admin-Only)
The platform connects to Google Flood Hub API to collect real flood data:

**Admin Dashboard Actions:**
- **🔄 Collect forecast data** - Fetches data from Google Flood Hub for 2,391 Pakistan gauges
- **📈 Update daily readings** - Updates water level measurements across all gauges  
- **⚙️ Batch processing** - Configurable batch sizes and date ranges
- **🔍 Quality verification** - Automatically identifies Google-verified gauges

**Data Collection Features:**
- Real-time API integration with Google Flood Hub
- Historical and forecast data collection
- Administrative boundary geocoding (province, district, tehsil)
- Automated daily collection via cron jobs

### Production Data Integration
The platform uses multiple data sources:

1. **Government Data Sources**
   - Pakistan Meteorological Department APIs
   - WAPDA (Water and Power Development Authority) data feeds
   - Provincial irrigation department systems

2. **International Sources**
   - Google Flood Hub API (if available)
   - NASA/ESA satellite data
   - USGS international water data

3. **IoT Sensors**
   - Direct sensor integration
   - Real-time data streaming
   - Automated data validation

## Development Setup

### Prerequisites
- Python 3.8+
- PostgreSQL (for production-like setup)
- Git

### Installation
```bash
# Clone repository
git clone https://github.com/ThomasMarketImpact/flood-data-platform.git
cd flood-data-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
cd src
python manage.py migrate

# Create admin user
python manage.py ensure_admin

# Populate sample data
python manage.py fetch_google_flood_data

# Run development server
python manage.py runserver
```

### Running Tests
```bash
cd src
python manage.py test
```

## 📁 Project Structure

```
flood-data-platform/
├── src/                          # Django project root
│   ├── config/                   # Django settings & configuration  
│   │   ├── settings/
│   │   │   ├── base.py          # Base settings
│   │   │   ├── development.py   # Development settings
│   │   │   └── production.py    # Production settings
│   │   ├── urls.py              # Main URL routing
│   │   └── wsgi.py              # WSGI application
│   ├── core/                    # Core flood data models & services
│   │   ├── models.py            # Gauge, Reading, Prediction models
│   │   ├── admin.py             # Admin interface with data operations
│   │   ├── management/commands/ # Django management commands
│   │   │   ├── collect_forecast_data.py  # Google Flood Hub API integration
│   │   │   ├── update_daily_readings.py  # Daily data updates
│   │   │   └── geocode_gauges.py         # Administrative boundary lookup
│   │   └── services/            # Business logic services
│   │       ├── data_collection.py       # Google Flood Hub API client
│   │       └── geocoding.py             # Geographic data services
│   ├── users/                   # User management & authentication
│   │   ├── models.py            # Custom user model
│   │   └── management/commands/ # User creation commands
│   ├── api/                     # REST API endpoints
│   │   ├── views.py             # API views (gauges, readings, predictions)
│   │   ├── serializers.py       # Data serialization
│   │   └── urls.py              # API routing
│   ├── dashboard/               # Public web dashboard
│   │   ├── views.py             # Dashboard & export views
│   │   ├── templates/           # HTML templates
│   │   └── urls.py              # Dashboard routing
│   └── templates/admin/         # Custom admin templates
├── docs/                        # Project documentation
│   ├── api/                     # API documentation
│   └── plan/                    # Development plans
├── archive/                     # Archived analysis & research (gitignored)
│   ├── data-analysis/           # CSV/JSON analysis files
│   ├── scripts/                 # Development scripts
│   ├── documentation/           # Draft documentation
│   └── research/                # Research materials
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies  
├── render.yaml                  # Render.com deployment config
├── build.sh                     # Production build script
├── pytest.ini                   # Test configuration
├── .gitignore                   # Git exclusions
├── CLAUDE.md                    # Project context for AI assistants
└── README.md                    # This documentation
```

## 🚀 Deployment

The platform is automatically deployed to Render.com on every push to the master branch.

### Production Deployment (Render.com)

1. **Automatic Deployment**
   - Push to `master` branch triggers deployment
   - Build script runs migrations and collects static files
   - Admin user created automatically on first deploy

2. **Environment Variables**
   ```
   DJANGO_SETTINGS_MODULE=config.settings.production
   DJANGO_SECRET_KEY=(auto-generated secure key)
   DATABASE_URL=(PostgreSQL connection string)
   ADMIN_USER=admin
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASS=your_secure_password_here
   GOOGLE_FLOOD_HUB_API_KEY=(optional - for API access)
   GOOGLE_GEOCODING_API_KEY=(optional - for geocoding)
   ```

3. **Database Setup**
   - PostgreSQL database auto-provisioned by Render
   - Migrations run automatically via `build.sh`
   - Initial admin user created via `ensure_admin` command

4. **Static Files**
   - Collected automatically during build
   - Served by Render's CDN
   - No additional configuration needed

### Manual Deployment Steps

If deploying to a different platform:

1. **Set Environment Variables** (see list above)
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Run Migrations**: `python src/manage.py migrate`
4. **Collect Static Files**: `python src/manage.py collectstatic --noinput`
5. **Create Admin User**: `python src/manage.py ensure_admin`
6. **Start Server**: `gunicorn config.wsgi:application`

### Post-Deployment Tasks

1. **Verify Deployment**
   - Check dashboard at root URL
   - Test admin login at `/supersecretadminpanel/`
   - Verify API docs at `/api/docs/`

2. **Initial Data Collection** (Admin Only)
   - Login to admin panel
   - Navigate to Gauges section
   - Use "Collect forecast data" action
   - Monitor dashboard for data population

3. **Setup Automated Collection** (Optional)
   - Configure cron job for daily updates
   - Use `collect_forecast_data` management command
   - Recommended schedule: Daily at 2 AM UTC

## Future Development

### Immediate Enhancements
1. **Real Data Integration**
   - Connect to official Pakistani meteorological data
   - Implement automated data collection schedules
   - Add data validation and quality checks

2. **Enhanced Visualization**
   - Interactive maps with gauge locations
   - Time-series charts for water levels
   - Alert threshold visualization

3. **Alert System**
   - Email/SMS notifications for high water levels
   - Configurable alert thresholds
   - Integration with emergency response systems

### Long-term Goals
1. **Predictive Analytics**
   - Machine learning flood prediction models
   - Historical trend analysis
   - Seasonal pattern recognition

2. **Mobile Application**
   - React Native or Flutter app
   - Push notifications
   - Offline data access

3. **Multi-country Support**
   - Extend beyond Pakistan
   - Regional flood monitoring
   - Cross-border data sharing

## Contributing

This project follows Test-Driven Development (TDD) principles:

1. Write failing tests first
2. Implement minimal code to pass tests
3. Refactor for clarity and efficiency

### Development Workflow
1. Create feature branch
2. Write tests for new functionality
3. Implement features to pass tests
4. Ensure all tests pass
5. Submit pull request

## 🧪 Testing

The project follows Test-Driven Development (TDD) principles:

```bash
# Run all tests
cd src
python manage.py test

# Run specific app tests
python manage.py test core
python manage.py test dashboard
python manage.py test api

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 🔧 Maintenance

### Regular Tasks
1. **Monitor API Integration** - Check Google Flood Hub API status
2. **Database Maintenance** - Regular PostgreSQL backups
3. **Security Updates** - Keep Django and dependencies updated
4. **Performance Monitoring** - Track response times and resource usage

### Troubleshooting
- **No data showing**: Check admin panel for data collection errors
- **API errors**: Verify API keys in environment variables
- **Login issues**: Run `python manage.py ensure_admin` to reset admin password
- **Static files 404**: Run `python manage.py collectstatic`

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

This project was developed by MarketImpact Digital Solutions and is open-sourced for research, demonstration, and capacity building purposes.

## 👥 Contact & Support

- **Developer**: MarketImpact Digital Solutions
- **Website**: [marketimpact.org](https://marketimpact.org)
- **Repository**: https://github.com/marketimpact/pakistan-flood-data-platform
- **Technical Issues**: Create an issue on GitHub
- **Professional Services**: info@marketimpact.org

### Project Credits
- **Project Lead**: Thomas Byrnes (Founder & Director, MarketImpact)

## 🏆 Acknowledgments

- **Google Flood Hub** - For providing flood forecast data and API access
- **Render.com** - For hosting and deployment infrastructure
- **Django Community** - For the excellent web framework

## ⚠️ Disclaimer

This platform integrates with Google Flood Hub for demonstration and research purposes. While it displays real flood gauge data for Pakistan:

1. **Not for Emergency Use** - Do not use for actual flood response decisions
2. **Official Sources** - Always consult Pakistan Meteorological Department and NDMA for official warnings
3. **Data Accuracy** - Virtual gauge readings are AI-generated estimates, not physical measurements
4. **Research Purpose** - Platform designed for capacity building and demonstration

---

**Project Status**: ✅ **Production Ready** - Version 1.0.0 (January 2025)

For detailed changes, see [CHANGELOG.md](CHANGELOG.md)