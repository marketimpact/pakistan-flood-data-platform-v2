# Technical Overview - Pakistan Flood Data Platform

## Architecture Summary

This is a Django-based flood monitoring platform with a clear separation between public data viewing and admin data management.

## Core Components

### 1. Public Dashboard (`/`)
- **Access**: No authentication required
- **Features**: Real-time flood data viewing, filtering, CSV export
- **Technology**: Django templates with responsive CSS
- **Data**: Read-only access to all Pakistan flood gauges

### 2. Admin Interface (`/supersecretadminpanel/`)
- **Access**: Staff user authentication required
- **Features**: Data collection operations, user management, CRUD operations
- **Technology**: Django admin with custom actions
- **Data**: Full database access and Google Flood Hub API integration

### 3. REST API (`/api/v1/`)
- **Access**: Session-based authentication required
- **Features**: Programmatic access to gauge and reading data
- **Technology**: Django REST Framework with OpenAPI documentation
- **Data**: RESTful endpoints for all core models

## Data Flow

```
Google Flood Hub API → Django Management Commands → PostgreSQL Database → Views/API → Frontend
```

### Google Flood Hub Integration
- **Endpoint**: Forecast API with Pakistan gauge network
- **Data**: 2,391 virtual gauges with water level readings and predictions
- **Collection**: Admin-triggered via Django management commands
- **Processing**: Automatic geocoding and administrative boundary assignment

### Database Schema
- **Gauges**: Virtual monitoring stations with geographic data
- **Readings**: Historical water level measurements
- **Predictions**: Future flood forecasts
- **Users**: Custom user model for authentication

## Security Model

### Public Access
- Dashboard viewing (read-only)
- CSV data export
- API documentation browsing

### Admin Access (Authentication Required)
- Data collection from Google Flood Hub
- Database operations
- User management
- System administration

### API Access (Authentication Required)
- CRUD operations via REST endpoints
- Rate limiting and security headers
- Session-based authentication

## Deployment Architecture

### Production (Render.com)
- **Web Service**: Django application with Gunicorn
- **Database**: PostgreSQL managed service
- **Storage**: Static files served by Render
- **Environment**: Production settings with security optimizations

### Development
- **Database**: SQLite for local development
- **Server**: Django development server
- **Environment**: Debug mode with detailed error reporting

## Key Technologies

- **Backend**: Django 5.2, Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **API**: RESTful with OpenAPI/Swagger documentation
- **Frontend**: HTML/CSS with responsive design
- **Deployment**: Render.com with automated builds
- **Testing**: Django test framework with comprehensive coverage

## Management Commands

### Data Collection
- `collect_forecast_data`: Fetch data from Google Flood Hub API
- `update_daily_readings`: Update water level measurements
- `geocode_gauges`: Add administrative boundary data

### User Management
- `ensure_admin`: Create admin user if doesn't exist
- `create_admin`: Force create new admin user

## Performance Considerations

- **Pagination**: Dashboard shows 50 gauges per page
- **Caching**: Static files cached with appropriate headers
- **Database**: Optimized queries with select_related and prefetch_related
- **API**: Rate limiting and efficient serialization

## Monitoring & Maintenance

- **Logs**: Comprehensive Django logging in production
- **Health Checks**: Database connectivity monitoring
- **Updates**: Automated daily data collection
- **Backups**: PostgreSQL automated backups on Render

## Development Workflow

1. **Test-Driven Development**: Write tests before implementation
2. **Code Quality**: Follow Django best practices and PEP 8
3. **Security**: Regular security header and dependency updates
4. **Documentation**: Keep technical docs and API documentation current