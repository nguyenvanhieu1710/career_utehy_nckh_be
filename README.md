# 🎯 Student Job Recommendation System

## 🧩 Overview

**Student Job Recommendation System** is a FastAPI-based web application designed to help **students** find jobs that best match their skills, academic background, and CV information.  
Instead of serving as a recruiting platform for employers, this system focuses entirely on **job seekers (students)** — aggregating and recommending job listings from various career websites that fit each student's profile.

### 🚀 Key Features

- 🔍 Personalized job recommendations based on students' CVs and academic data
- 🧠 Integration of recommendation algorithms using machine learning (Joblib, NumPy)
- 📨 Email notifications using FastAPI-Mail
- 🗄️ Data storage and management via SQLAlchemy ORM
- 🧾 Secure authentication using JOSE and Passlib
- 🧩 QR code generation for quick access to job details
- ⚡ Fast, asynchronous API built with FastAPI

---

## ⚙️ Tech Stack

- **Backend Framework:** FastAPI
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Machine Learning:** Joblib, NumPy
- **Authentication:** JOSE, Passlib
- **Email Service:** FastAPI-Mail
- **Cache/Queue:** Redis
- **Containerization:** Docker & Docker Compose
- **Reverse Proxy:** Nginx
- **Utilities:** OpenCV, Pillow, QRCode, Requests, dotenv

---

## 🧰 Installation & Setup

### Prerequisites

- Docker and Docker Compose installed
- Git

### 🚀 Quick Start with Docker (Recommended)

#### 1. Clone Repository

```bash
git clone https://github.com/thanhtungdo2003/career_utehy_nckh_be.git
cd career_utehy_nckh_be
```

#### 2. Configure Environment Variables

Copy the `.env.example` file to `.env` and update the necessary values:

```bash
cp .env.example .env
```

#### 3. Run Docker setup script

```bash
docker-compose up -d --build
```

This command will start:

- **PostgreSQL Database** (port 5432)
- **Backend API** (port 8000)
- **Frontend** (port 3000)
- **Nginx Reverse Proxy** (port 80)
- **PgAdmin** (port 5050) - for database management

#### 4. Check services status

```bash
docker-compose ps
```

#### 5. Access the application

- **Frontend:** http://localhost
- **Backend API:** http://localhost/api
- **API Documentation:** http://localhost/api/docs
- **PgAdmin:** http://localhost:5050 (admin@gmail.com / admin)

### 🛠️ Development Setup (Local)

#### 1. Clone Repository

```bash
git clone https://github.com/thanhtungdo2003/career_utehy_nckh_be.git
cd career_utehy_nckh_be
```

#### 2. Create Virtual Environment

```bash
python -m venv venv
```

#### 3. Activate Virtual Environment

**Windows:**

```bash
.\venv\Scripts\activate
```

**Linux/Mac:**

```bash
source venv/bin/activate
```

#### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 5. Run the application

```bash
python run.py
```

---

## 📁 Project Structure

```
career_utehy_nckh_be/
├── app/
│   ├── api/          # API routes
│   ├── core/         # Core configurations
│   ├── models/       # Database models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── utils/        # Utility functions
├── uploads/          # File uploads storage
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

---

## 🔧 Configuration

### Database Migration

After the first startup, the database will automatically create the necessary tables.

### Email Configuration

To use the email functionality, you need to:

1. Enable 2-factor authentication for Gmail
2. Create an App Password
3. Update `MAIL_USERNAME` and `MAIL_PASSWORD` in the `.env` file

---

## 📚 API Documentation

After starting the application, access:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
