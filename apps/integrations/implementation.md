# 📦 Integrations App – Technical Implementation

---

## 1. 📝 Overview

The **Integrations App** manages all user and staff notifications for your POS/warehouse inventory system:

- **Welcome credentials** (email/SMS) for new users
- **Inventory alerts** (low stock, expired products)
- **Staff shift notifications**
- **Password reset emails**

**Supports:**
- ✅ Email (HTML + plain text)
- ✅ SMS (via Africa's Talking API)
- ✅ Async processing (Celery)

---

## 2. 🏗️ Core Components

### A. **Models**

| Model            | Purpose                    | Key Fields                                 |
|------------------|---------------------------|--------------------------------------------|
| `Notification`   | Tracks sent notifications | `user`, `notification_type`, `is_read`, `sent_at` |
| `InventoryAlert` | Logs stock alerts         | `product`, `alert_type`, `resolved`        |

---

### B. **Services**

| Service              | Functionality                              |
|----------------------|--------------------------------------------|
| `NotificationService`| Main class for sending notifications       |
| `EmailService`       | Handles email templates & delivery         |
| `SMSService`         | Sends SMS via Africa’s Talking API         |

---

### C. **Celery Tasks**

| Task                          | Purpose                                 |
|-------------------------------|-----------------------------------------|
| `send_notification_task`      | Async notification delivery             |
| `send_welcome_credentials_task` | Sends credentials to new users        |
| `check_low_stock_items`       | Scans for low stock & triggers alerts   |

---

## 3. 🌟 Key Features

### A. **Welcome Credentials**

- **Trigger:** When a new user is created.
- **Actions:**
  - Generates a random password.
  - Sends email + SMS with:
    - Username
    - Temporary password
    - Role (POS/Warehouse/etc.)
  - No forced password reset (users can update later).

---

### B. **Inventory Alerts**

- **Checks for:**
  - Low stock (`LOW_STOCK_THRESHOLD` in settings)
  - Expired products
- **Recipients:** All staff users (`is_staff=True`).

---

### C. **Staff Shift Notifications**

- Sends shift details via SMS + email.

---

## 4. ⚙️ Setup Requirements

### A. **Django Settings**

```python
# settings.py

# Email (SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'

# SMS (Africa's Talking)
AFRICASTALKING_USERNAME = 'your_username'
AFRICASTALKING_API_KEY = 'your_api_key'

# Low stock threshold
LOW_STOCK_THRESHOLD = 10  # Default