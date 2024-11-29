# InternalAPI

A FastAPI-based internal API system designed for efficient task management, worker processes, and database connections.

## 🌟 Features

- **Fast and Efficient**: Built with FastAPI and async operations
- **Multi-Worker Support**: Utilizes uvicorn workers for parallel processing
- **Secure Authentication**: JWT token-based authentication
- **Auto Documentation**: Swagger/OpenAPI documentation
- **Database Connection**: SQLite (or other database) integration
- **Type Safety**: Pydantic models for request/response validation
- **Cross-Origin Support**: Configured CORS for secure access

## 🛠️ Tech Stack

- **Framework**: FastAPI v0.7+
- **Server**: Uvicorn with Gunicorn workers
- **Python**: Version 3.8+
- **Database**: SQLite (configurable)
- **Authentication**: JWT (jose library)
- **Validation**: Pydantic v2
- **Testing**: pytest
- **Documentation**: Swagger/OpenAPI

## 📁 Project Structure

```
InternalAPI/
├── api/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt.py           # JWT handling
│   │   └── utils.py         # Auth utilities
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration
│   │   └── security.py      # Security settings
│   ├── crud/
│   │   ├── __init__.py
│   │   └── base.py          # CRUD operations
│   ├── database/
│   │   ├── __init__.py
│   │   └── session.py       # DB session
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # Data models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # Auth routes
│   │   └── api.py           # API routes
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py          # Pydantic schemas
│   └── main.py              # FastAPI application
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── requirements.txt
├── .env
└── README.md
```

## 🚀 Getting Started

1. **Clone the repository**
```bash
git clone https://github.com/anudeepadi/InternalAPI.git
cd InternalAPI
```

2. **Set up virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Create environment file**
```bash
cp .env.example .env
# Update with your configurations
```

5. **Run the server**
```bash
# Development
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📝 Environment Variables

```env
# .env example
API_TITLE=Internal API
API_VERSION=v1
DEBUG=True
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./sql_app.db
CORS_ORIGINS=["http://localhost:3000"]
```

## 🔑 API Endpoints

### Authentication
```
POST /api/token
    - Get access token
    - Body: username, password
    - Returns: access_token, token_type

POST /api/token/refresh
    - Refresh access token
    - Header: Authorization: Bearer {token}
    - Returns: new access_token
```

### Users
```
GET /api/users/
    - Get all users
    - Requires: Authentication

POST /api/users/
    - Create new user
    - Body: UserCreate schema

GET /api/users/{user_id}
    - Get user by ID
    - Requires: Authentication

PUT /api/users/{user_id}
    - Update user
    - Requires: Authentication
    - Body: UserUpdate schema

DELETE /api/users/{user_id}
    - Delete user
    - Requires: Authentication
```

## 📚 Documentation

After starting the server, access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api tests/

# Generate coverage report
pytest --cov=api --cov-report=html tests/
```

## 🔒 Security Features

- JWT Authentication
- Password hashing
- Rate limiting
- CORS protection
- Input validation
- SQL injection prevention
- XSS protection

## 🚀 Deployment

1. **Build and Install**
```bash
pip install "uvicorn[standard]" gunicorn
```

2. **Run in Production**
```bash
gunicorn api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

## 📝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/YourFeature`)
3. Commit changes (`git commit -m 'Add YourFeature'`)
4. Push to branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

## 📧 Contact

- GitHub: [@anudeepadi](https://github.com/anudeepadi)
- Email: contact@anudeepadi.me

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

⭐️ If you find this project useful, please give it a star!
