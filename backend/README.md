# Vachan Study Bible Chatbot - Backend

A FastAPI-based backend for the AI-powered Bible study chatbot with authentication, chat functionality, and analytics.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Application configuration
│   │   └── security.py      # Authentication utilities
│   └── routes/
│       ├── __init__.py
│       ├── auth.py          # Authentication routes
│       ├── chat.py          # Chat routes
│       └── analytics.py     # Analytics routes
├── schemas/
│   ├── __init__.py
│   ├── auth.py              # Authentication schemas
│   ├── requests.py          # Request schemas
│   └── responses.py         # Response schemas
├── db/
│   ├── __init__.py
│   ├── mongodb.py           # MongoDB connection
│   ├── repositories.py      # Existing repositories
│   └── user_repository.py   # User account management
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── test_auth.py         # Authentication tests
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variables template
```

## Features

### Authentication
- JWT-based authentication
- User registration and login
- Password hashing with bcrypt
- Rate limiting for login attempts
- Protected endpoints

### Chat
- Bible study chat functionality
- Book-specific conversations
- Chat history management

### Analytics
- Usage statistics
- Daily study metrics
- User activity tracking

## Setup

### Prerequisites
- Python 3.10+
- MongoDB (local or Atlas)
- Redis (for rate limiting)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Seffin/vachan-study-chat.git
   cd vachan-study-chat/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Start MongoDB:**
   ```bash
   # If using local MongoDB
   mongod --dbpath /path/to/data/directory
   ```

6. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Application
APP_NAME=Vachan Study Bible Chatbot API
APP_VERSION=1.0.0
APP_DESCRIPTION=AI-powered Bible study chatbot with multilingual support

# Authentication
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=vachan_study

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Rate Limiting
RATE_LIMIT=5
RATE_LIMIT_MINUTES=1
```

## API Documentation

The API documentation is automatically generated using Swagger UI:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login and get JWT token | No |
| GET | `/api/auth/me` | Get current user info | Yes |
| POST | `/api/auth/logout` | Logout (invalidate token) | Yes |

### Chat

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/chat/` | Send chat message | Yes |
| GET | `/api/chat/history/{book_code}` | Get chat history for book | Yes |

### Analytics

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/analytics/usage` | Get usage statistics | Yes |
| GET | `/api/analytics/daily` | Get daily study metrics | Yes |

## Testing

### Run tests

```bash
pytest tests/ -v
```

### Run with coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Test authentication system

```bash
python test_auth_system.py
```

## Development

### Code Style
- Use `ruff` for linting:
  ```bash
  ruff check app/
  ```

- Use `mypy` for type checking:
  ```bash
  mypy app/
  ```

### Project Conventions
- Use `snake_case` for variables and functions
- Use `PascalCase` for classes
- Use `UPPER_CASE` for constants
- Use type hints for all functions
- Include docstrings for all public functions

## Deployment

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t vachan-study-backend .
docker run -p 8000:8000 --env-file .env vachan-study-backend
```

### Production with Gunicorn

```bash
pip install gunicorn
 gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 app.main:app
```

## Integration with Existing Code

This backend is designed to integrate with your existing codebase:

1. **Database Integration:** The `UserRepository` uses the same MongoDB connection as your existing repositories.

2. **Chat Integration:** The chat routes can be connected to your existing chat logic in the `services/` directory.

3. **AI Services:** Your existing AI services (embedding, retrieval, generation) can be integrated with the chat endpoints.

## Next Steps

1. **Integrate existing chat logic** into the chat routes
2. **Connect AI services** to the chat endpoints
3. **Add more endpoints** for specific Bible study features
4. **Implement analytics tracking** for user activity
5. **Add logging** for debugging and monitoring

## License

MIT License - Feel free to use this code for your project.