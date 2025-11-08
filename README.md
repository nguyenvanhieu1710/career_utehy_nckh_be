# 🎯 Student Job Recommendation System

## 🧩 Overview
**Student Job Recommendation System** is a FastAPI-based web application designed to help **students** find jobs that best match their skills, academic background, and CV information.  
Instead of serving as a recruiting platform for employers, this system focuses entirely on **job seekers (students)** — aggregating and recommending job listings from various career websites that fit each student's profile.

### 🚀 Key Features
- 🔍 Personalized job recommendations based on students’ CVs and academic data  
- 🧠 Integration of recommendation algorithms using machine learning (Joblib, NumPy)  
- 📨 Email notifications using FastAPI-Mail  
- 🗄️ Data storage and management via SQLAlchemy ORM  
- 🧾 Secure authentication using JOSE and Passlib  
- 🧩 QR code generation for quick access to job details  
- ⚡ Fast, asynchronous API built with FastAPI  

---

## ⚙️ Tech Stack
- **Backend Framework:** FastAPI  
- **Database:** SQLAlchemy ORM  
- **Machine Learning:** Joblib, NumPy  
- **Authentication:** JOSE, Passlib  
- **Email Service:** FastAPI-Mail  
- **Cache/Queue:** Redis  
- **Utilities:** OpenCV, Pillow, QRCode, Requests, dotenv  

---

## 🧰 Installation & Setup

### 1 Clone the Repository

```bash
git clone https://github.com/thanhtungdo2003/career_utehy_nckh_be.git
cd career_utehy_nckh_be
```
### 2 Create a Virtual Environment

```bash
python -m venv venv
```

### 3 Activate the Virtual Environment

```bash
.\venv\Scripts\activate
```

### 4 Install Package

```bash
pip install -r requirements.txt
```

### 5 Set up environment variables
```bash
echo. > .env
```

### 6 Build and start containers
```bash
docker-compose up -d --build
```

### 7 Run
```bash
python run.py
```

