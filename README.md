# Kenyan Inventory Management System

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/yourusername/kenyan-inventory-system/releases)
[![Django](https://img.shields.io/badge/django-4.2+-green.svg)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.14+-orange.svg)](https://django-rest-framework.org)
[![Python](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/postgresql-13+-blue.svg)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/redis-6.0+-red.svg)](https://redis.io)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/yourusername/kenyan-inventory-system/actions)
[![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen.svg)](https://github.com/yourusername/kenyan-inventory-system/coverage)
[![M-Pesa](https://img.shields.io/badge/M--Pesa-integrated-green.svg)](https://developer.safaricom.co.ke)
[![SMS](https://img.shields.io/badge/SMS-AfricasTalking-blue.svg)](https://africastalking.com)

> A comprehensive Django REST Framework (DRF) backend inventory management system built specifically for the Kenyan market, featuring M-Pesa payments, SMS notifications, real-time analytics, and multi-warehouse operations.

## 🇰🇪 Built for Kenya

This system is designed with Kenyan businesses in mind, integrating local payment methods, SMS services, and business practices to provide a seamless inventory management experience.

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [System Architecture](#system-architecture)
- [M-Pesa Integration](#m-pesa-integration)
- [SMS Integration](#sms-integration)
- [Real-time Analytics](#real-time-analytics)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Testing](#testing)
- [Contributing](#contributing)
- [Support](#support)

## ✨ Features

### 🏪 Core Inventory Management

| Feature | Status | Description |
|---------|--------|-------------|
| 📦 **Multi-Warehouse** | ✅ Complete | Track inventory across multiple locations and bins |
| 🛍️ **Product Management** | ✅ Complete | SKU management, categories, and variant tracking |
| 📊 **Stock Control** | ✅ Complete | Real-time stock levels, low stock alerts, and transfers |
| 🧾 **Purchase Orders** | ✅ Complete | Supplier management and procurement workflows |
| 💰 **Point of Sale** | ✅ Complete | Order processing and receipt generation |
| 📈 **Analytics Dashboard** | ✅ Complete | Real-time business intelligence and reporting |

### 💳 Kenyan Payment Integration

| Service | Status | Features |
|---------|--------|----------|
| 💚 **M-Pesa** | ✅ Live | STK Push, C2B, B2C, Transaction status |
| 📱 **SMS Receipts** | ✅ Live | AfricasTalking integration for notifications |
| 🏦 **Bank Integration** | 🚧 Planned | Support for major Kenyan banks |

### 🔐 Security & Access Control

- **API Token authentication** for secure API access
- **Role-based permissions** (Admin, Branch Manager, etc.)
- **Audit trails** for all transactions
- **Data encryption** for sensitive information
- **API rate limiting** and security headers

### 📊 Real-time Capabilities

- **Real-time inventory alerts** for stock levels
- **Live analytics** with aggregated reports
- **Instant notifications** for critical events
- **Background task processing** with Celery

## 🚀 Quick Start

### Prerequisites Checklist

- [ ] Python 3.9+
- [ ] PostgreSQL 13+ (or SQLite3 for development)
- [ ] Redis 6.0+
- [ ] Safaricom Developer Account
- [ ] AfricasTalking Account
- [ ] SSL Certificate (for M-Pesa callbacks)

### 5-Minute Setup

```bash
# 1. Clone and setup environment
git clone https://github.com/yourusername/kenyan-inventory-system.git
cd kenyan-inventory-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API credentials

# 4. Setup database
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# 5. Start services
redis-server &  # Start Redis
python manage.py runserver
```

Visit `http://localhost:8000/api/v1/` to access the API endpoints.

## 🛠️ Installation

### Development Environment

#### 1. System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.9 python3.9-venv postgresql redis-server
```

**macOS:**
```bash
brew install python@3.9 postgresql redis
```

**Windows:**
```powershell
# Install using Chocolatey
choco install python postgresql redis
```

#### 2. Project Setup

```bash
# Clone repository
git clone https://github.com/yourusername/kenyan-inventory-system.git
cd kenyan-inventory-system

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Database Configuration

```bash
# For PostgreSQL (Production)
sudo -u postgres psql
CREATE DATABASE inventory_system;
CREATE USER inventory_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE inventory_system TO inventory_user;
\q

# Apply migrations
python manage.py migrate

# For SQLite3 (Development) - Already configured
python manage.py migrate
```

#### 4. Environment Configuration

Create `.env` file:

```env
# Django Settings
DEBUG=True
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite3 for development)
DATABASE_URL=sqlite:///db.sqlite3

# For PostgreSQL (Production)
# DATABASE_URL=postgresql://inventory_user:your_password@localhost:5432/inventory_system

# M-Pesa Configuration
MPESA_ENVIRONMENT=sandbox  # or 'production'
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_BUSINESS_SHORTCODE=174379
MPESA_PASSKEY=your_passkey
MPESA_CALLBACK_URL=https://yourdomain.com/api/v1/integrations/mpesa/callback/
MPESA_TIMEOUT_URL=https://yourdomain.com/api/v1/integrations/mpesa/timeout/

# AfricasTalking SMS
AT_USERNAME=sandbox
AT_API_KEY=your_api_key
AT_SENDER_ID=INVENTORY

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 🏗️ System Architecture

### Application Structure

```
kenyan-inventory-system/
├── 📄 .env                         # Environment variables
├── 📄 .gitignore                   # Git ignore rules
├── 📄 db_transactions.log          # Database transaction logs
├── 📄 db.sqlite3                   # SQLite database (development)
├── 📄 error.log                    # Application error logs
├── 📄 Flow.png                     # System flow diagram
├── 📄 manage.py                    # Django management script
├── 📄 README.md                    # Project documentation
├── 📄 requirements.txt             # Python dependencies
├── 📄 schema.yaml                  # API schema documentation
├── 📁 apps/                        # Django applications
│   ├── 📄 __init__.py
│   ├── 📄 reset.ps1               # Reset script
│   ├── 📁 accounts/               # User management & authentication
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 models.py           # User & WorkerProfile models
│   │   ├── 📄 permissions.py      # Role-based permissions
│   │   ├── 📄 serializers.py      # API serializers
│   │   ├── 📄 urls.py             # URL routing
│   │   ├── 📄 views.py            # API views
│   │   └── 📁 migrations/
│   ├── 📁 analytics/              # Real-time dashboards & reports
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 models.py           # SalesReport & RTInventoryAlert
│   │   ├── 📄 tests.py
│   │   └── 📁 migrations/
│   ├── 📁 core/                   # Base models & utilities
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 models.py           # BaseModel, Configuration, AuditLog
│   │   ├── 📁 urls/
│   │   │   ├── 📄 __init__.py
│   │   │   └── 📄 mgt.py
│   │   ├── 📄 views.py
│   │   ├── 📄 tests.py
│   │   └── 📁 migrations/
│   ├── 📁 integrations/           # External service integrations
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 models.py           # Notification & InventoryAlert
│   │   ├── 📄 implementation.md   # Integration documentation
│   │   ├── 📄 tests.py
│   │   └── 📁 migrations/
│   ├── 📁 procurement/            # Purchase orders & suppliers (in development)
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 models.py
│   │   ├── 📄 tests.py
│   │   └── 📁 migrations/
│   ├── 📁 products/               # Product & inventory management
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 models.py           # Category, Product, ProductImage, Inventory
│   │   ├── 📄 permissions.py
│   │   ├── 📄 serializers.py
│   │   ├── 📄 urls.py
│   │   ├── 📄 views.py
│   │   ├── 📄 tests.py
│   │   └── 📁 migrations/
│   ├── 📁 sales/                  # Point of sale & orders
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 models.py           # Customer, Order, OrderItem, Receipt
│   │   ├── 📄 urls.py
│   │   ├── 📄 views.py
│   │   ├── 📄 tests.py
│   │   └── 📁 migrations/
│   ├── 📁 suppliers/              # Supplier management
│   │   ├── 📄 __init__.py
│   │   ├── 📄 admin.py
│   │   ├── 📄 apps.py
│   │   ├── 📄 models.py           # Supplier, PurchaseOrder, PurchaseOrderItem, SupplierPayment
│   │   ├── 📄 views.py
│   │   └── 📁 migrations/
│   └── 📁 warehouses/             # Multi-location management
│       ├── 📄 __init__.py
│       ├── 📄 admin.py
│       ├── 📄 models.py           # Branch, Warehouse, BinLocation, StockTransfer
│       ├── 📄 urls.py
│       ├── 📄 views.py
│       └── 📁 migrations/
├── 📁 root/                       # Django project configuration
│   ├── 📄 __init__.py
│   ├── 📄 asgi.py                 # ASGI configuration
│   ├── 📄 urls.py                 # Main URL configuration
│   ├── 📄 wsgi.py                 # WSGI configuration
│   └── 📁 settings/
│       ├── 📄 __init__.py
│       ├── 📄 base.py             # Base settings
│       └── 📄 development.py      # Development settings
├── 📁 static/                     # Static assets
│   └── 📁 migrations/
└── 📁 templates/                  # Django templates
    ├── 📁 core/
    ├── 📁 emails/
    ├── 📁 migrations/
    └── 📁 sales/
```

### 📝 Models Summary

#### `apps.accounts.models`
- **User**: Custom user model with roles (Admin, Branch Manager, etc.), email, phone, and security fields
- **WorkerProfile**: One-to-one with User, links to branch, stores ID, signature, pin code, and status

#### `apps.analytics.models`
- **SalesReport**: Aggregated sales data for daily/weekly/monthly periods, includes totals, top product, and M-Pesa stats
- **RTInventoryAlert**: Real-time low stock alerts, links product and warehouse, tracks current stock and resolution

#### `apps.core.models`
- **BaseModel**: Abstract base with created_at, updated_at, is_active
- **Configuration**: Key-value store for system-wide settings
- **AuditLog**: Tracks critical actions (create, update, delete, login) with user, model, object ID, and details

#### `apps.integrations.models`
- **Notification**: Tracks notifications sent to users (email, SMS, push), with subject, message, status, and timestamps
- **InventoryAlert**: Logs inventory-related alerts (low stock, expired, restock), links to product, with status and timestamps

#### `apps.procurement.models`
*(No models defined yet; still under development)*

#### `apps.products.models`
- **Category**: Product categories with VAT classification
- **Product**: Main product model with SKU, barcode, prices, type, and category
- **ProductImage**: Images for products, supports primary image and captions
- **Inventory**: Tracks product quantity per warehouse, with restock logic

#### `apps.sales.models`
- **Customer**: Buyer details (name, phone, email, tax ID, address)
- **Order**: Sales order, links to customer and warehouse, tracks status, payment, totals, and M-Pesa code
- **OrderItem**: Line items in an order, links to product, quantity, price, VAT
- **Receipt**: Generated receipts for orders, tracks SMS status and issuance

#### `apps.suppliers.models`
- **Supplier**: Vendor details (name, contact, phone, tax ID, payment terms)
- **PurchaseOrder**: Orders placed with suppliers, tracks status, dates, notes
- **PurchaseOrderItem**: Line items in a purchase order, links to product, quantity, price, VAT
- **SupplierPayment**: Records payments to suppliers (M-Pesa, bank, cash), links to purchase order

#### `apps.warehouses.models`
- **Branch**: Business branch with KRA PIN, registration, VAT, county, address, manager
- **Warehouse**: Physical storage, links to branch, has type, code, manager, capacity, and temperature info
- **BinLocation**: Storage bins/shelves in a warehouse, with barcode/QR support
- **StockTransfer**: Tracks stock movement between warehouses/bins, with reference, type, status, approval, and logistics info

## 💳 M-Pesa Integration

### Setup M-Pesa Developer Account

1. **Register at [Safaricom Developer Portal](https://developer.safaricom.co.ke/)**
2. **Create a new app** and note down:
   - Consumer Key
   - Consumer Secret
   - Business Shortcode
   - Passkey

### Configuration

```python
# apps/integrations/mpesa/settings.py
MPESA_CONFIG = {
    'ENVIRONMENT': 'sandbox',  # or 'production'
    'CONSUMER_KEY': os.getenv('MPESA_CONSUMER_KEY'),
    'CONSUMER_SECRET': os.getenv('MPESA_CONSUMER_SECRET'),
    'BUSINESS_SHORTCODE': os.getenv('MPESA_BUSINESS_SHORTCODE'),
    'PASSKEY': os.getenv('MPESA_PASSKEY'),
    'CALLBACK_URL': os.getenv('MPESA_CALLBACK_URL'),
    'TIMEOUT_URL': os.getenv('MPESA_TIMEOUT_URL'),
}
```

### Usage Examples

#### STK Push Payment

```python
from apps.integrations.mpesa import MpesaClient

# Initialize M-Pesa client
mpesa = MpesaClient()

# Initiate STK Push
response = mpesa.stk_push(
    phone_number='254712345678',
    amount=1000,
    account_reference='ORDER_123',
    transaction_desc='Payment for goods'
)

if response['ResponseCode'] == '0':
    print(f"Payment initiated: {response['CheckoutRequestID']}")
else:
    print(f"Error: {response['ResponseDescription']}")
```

#### Transaction Status Query

```python
# Check payment status
status = mpesa.query_transaction_status(checkout_request_id)
print(f"Payment status: {status['ResultDesc']}")
```

### Testing M-Pesa Integration

```bash
# Test STK Push in sandbox
curl -X POST http://localhost:8000/api/v1/integrations/mpesa/stk-push/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -d '{
    "phone_number": "254712345678",
    "amount": 100,
    "account_reference": "TEST_ORDER",
    "transaction_desc": "Test payment"
  }'
```

## 📱 SMS Integration

### AfricasTalking Setup

1. **Sign up at [AfricasTalking](https://africastalking.com/)**
2. **Get API credentials**:
   - Username
   - API Key
   - Sender ID

### SMS Service Implementation

```python
# apps/integrations/sms/service.py
import africastalking
from django.conf import settings

class SMSService:
    def __init__(self):
        africastalking.initialize(
            username=settings.AT_USERNAME,
            api_key=settings.AT_API_KEY
        )
        self.sms = africastalking.SMS
    
    def send_receipt(self, phone_number, receipt_data):
        """Send receipt via SMS"""
        message = self.format_receipt_message(receipt_data)
        
        try:
            response = self.sms.send(
                message,
                [phone_number],
                sender_id=settings.AT_SENDER_ID
            )
            return response
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return None
    
    def send_stock_alert(self, phone_numbers, product_name, current_stock):
        """Send low stock alert"""
        message = f"ALERT: {product_name} is running low. Current stock: {current_stock} units."
        
        return self.sms.send(
            message,
            phone_numbers,
            sender_id=settings.AT_SENDER_ID
        )
```

## 📊 Real-time Analytics

### Analytics Models

```python
# apps/analytics/models.py
from django.db import models
from apps.core.models import BaseModel

class SalesReport(BaseModel):
    """Aggregated sales data for reporting periods"""
    period_type = models.CharField(max_length=20)  # daily, weekly, monthly
    period_date = models.DateField()
    total_sales = models.DecimalField(max_digits=12, decimal_places=2)
    total_orders = models.IntegerField()
    top_product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True)
    mpesa_transactions = models.IntegerField(default=0)
    
class RTInventoryAlert(BaseModel):
    """Real-time inventory alerts"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    warehouse = models.ForeignKey('warehouses.Warehouse', on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20)  # low_stock, out_of_stock
    current_stock = models.IntegerField()
    threshold = models.IntegerField()
    is_resolved = models.BooleanField(default=False)
```

### Real-time Notifications

```python
# apps/analytics/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.products.models import Inventory
from apps.integrations.models import InventoryAlert

@receiver(post_save, sender=Inventory)
def check_stock_levels(sender, instance, **kwargs):
    """Check stock levels and create alerts"""
    if instance.quantity <= instance.reorder_level:
        InventoryAlert.objects.create(
            product=instance.product,
            warehouse=instance.warehouse,
            alert_type='low_stock',
            current_stock=instance.quantity,
            threshold=instance.reorder_level
        )
```

## 🔗 API Documentation

### Authentication

All API endpoints require Token authentication:

```bash
# Obtain API token
POST /api/v1/accounts/auth/login/
{
    "email": "admin@example.com",
    "password": "password123"
}

# Response
{
    "token": "your_api_token_here",
    "user_id": 1,
    "role": "admin"
}

# Use token in subsequent requests
Authorization: Token <your_api_token>
```

### Core Endpoints

#### Product Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/products/products/` | List all products |
| `POST` | `/api/v1/products/products/` | Create new product |
| `GET` | `/api/v1/products/products/{id}/` | Get product details |
| `PUT` | `/api/v1/products/products/{id}/` | Update product |
| `DELETE` | `/api/v1/products/products/{id}/` | Delete product |
| `GET` | `/api/v1/products/inventory/` | Get inventory levels |
| `POST` | `/api/v1/products/inventory/adjust/` | Adjust stock levels |

#### Sales & Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/sales/orders/` | Create new order |
| `GET` | `/api/v1/sales/orders/{id}/` | Get order details |
| `POST` | `/api/v1/sales/orders/{id}/payment/` | Process payment |
| `GET` | `/api/v1/sales/receipts/{id}/` | Get receipt |

#### Warehouse Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/warehouses/branches/` | List branches |
| `GET` | `/api/v1/warehouses/warehouses/` | List warehouses |
| `POST` | `/api/v1/warehouses/transfers/` | Create stock transfer |

#### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/sales-reports/` | Get sales reports |
| `GET` | `/api/v1/analytics/inventory-alerts/` | Get inventory alerts |
| `GET` | `/api/v1/analytics/dashboard/` | Get dashboard metrics |

### Example API Usage

```python
import requests

# Create a new product
response = requests.post(
    'http://localhost:8000/api/v1/products/products/',
    headers={'Authorization': 'Token YOUR_API_TOKEN'},
    json={
        'name': 'Sample Product',
        'sku': 'PROD001',
        'price': '99.99',
        'category': 1,
        'description': 'A sample product'
    }
)

product = response.json()
print(f"Created product: {product['name']}")
```

### API Response Format

```json
{
    "success": true,
    "data": {
        "id": 1,
        "name": "Sample Product",
        "sku": "PROD001",
        "price": "99.99"
    },
    "message": "Product created successfully",
    "timestamp": "2025-06-29T10:30:00Z"
}
```

## 🚀 Deployment

### Production Environment Variables

```env
# Production Settings
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com,www.api.yourdomain.com
SECRET_KEY=your-production-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/inventory_prod

# M-Pesa Production
MPESA_ENVIRONMENT=production
MPESA_CONSUMER_KEY=your_production_consumer_key
MPESA_CONSUMER_SECRET=your_production_consumer_secret
MPESA_BUSINESS_SHORTCODE=your_actual_shortcode
MPESA_CALLBACK_URL=https://api.yourdomain.com/api/v1/integrations/mpesa/callback/

# Security
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Monitoring
SENTRY_DSN=your_sentry_dsn
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/inventory
    depends_on:
      - db
      - redis
    
  celery:
    build: .
    command: celery -A root worker -l info
    depends_on:
      - db
      - redis
    
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: inventory
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:6-alpine

volumes:
  postgres_data:
```

### Deployment Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up SSL certificates
- [ ] Configure production database
- [ ] Set up Redis for production
- [ ] Configure email settings
- [ ] Set up monitoring (Sentry)
- [ ] Configure logging
- [ ] Set up backup procedures
- [ ] Configure firewall rules
- [ ] Set up API rate limiting

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.sales

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html

# Run integration tests
python manage.py test apps.integrations

# Run API tests
python manage.py test apps.*/tests.py
```

### Test Categories

#### Unit Tests
```python
# apps/products/tests.py
from django.test import TestCase
from apps.products.models import Product

class ProductModelTest(TestCase):
    def test_product_creation(self):
        product = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            price=99.99
        )
        self.assertEqual(product.name, 'Test Product')
        self.assertEqual(str(product), 'Test Product')
```

#### API Tests
```python
# apps/products/test_api.py
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

class ProductAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_create_product(self):
        data = {
            'name': 'Test Product',
            'sku': 'TEST001',
            'price': '99.99'
        }
        response = self.client.post('/api/v1/products/products/', data)
        self.assertEqual(response.status_code, 201)
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load_tests.py --host=http://localhost:8000
```

## 📚 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit changes** (`git commit -m 'Add amazing feature'`)
4. **Push to branch** (`git push origin feature/amazing-feature`)
5. **Open Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use meaningful commit messages
- Test M-Pesa integration in sandbox mode

## 📞 Support

- **Documentation**: [GitHub Wiki](https://github.com/yourusername/kenyan-inventory-system/wiki)
- **Issues**: [GitHub Issues](https://github.com/yourusername/kenyan-inventory-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/kenyan-inventory
