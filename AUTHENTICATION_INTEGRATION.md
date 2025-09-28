# Authentication Integration Guide

## Overview
This guide explains how the HTML frontend (`index.html`) connects to the FastAPI backend for user authentication.

## Architecture

### Backend (FastAPI)
- **Base URL**: `http://localhost:8001`
- **Database**: MongoDB
- **Authentication**: JWT tokens with bcrypt password hashing
- **Endpoints**:
  - `POST /api/auth/register` - User registration
  - `POST /api/auth/token` - User login (OAuth2 format)
  - `GET /api/auth/me` - Get current user profile

### Frontend (HTML + JavaScript)
- **File**: `server/agents/weather_agent/test_ui/index.html`
- **Authentication State**: Managed in localStorage
- **UI**: Modal-based login/signup forms

## API Endpoints Details

### 1. User Registration
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "name": "John Doe", 
  "email": "john@example.com",
  "password": "securepassword"
}
```

**Response (201)**:
```json
{
  "id": "64abc123...",
  "username": "johndoe",
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2024-01-01T10:00:00.000Z"
}
```

### 2. User Login
```http
POST /api/auth/token
Content-Type: application/x-www-form-urlencoded

username=johndoe&password=securepassword
```

**Response (200)**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### 3. Get User Profile
```http
GET /api/auth/me
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Response (200)**:
```json
{
  "id": "64abc123...",
  "username": "johndoe", 
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2024-01-01T10:00:00.000Z"
}
```

## Frontend Implementation

### Key JavaScript Functions

1. **`handleSignIn(event)`** - Handles user login
2. **`handleSignUp(event)`** - Handles user registration  
3. **`fetchUserProfile()`** - Retrieves user data after login
4. **`handleLogout()`** - Logs out user and clears session
5. **`updateUIForLoggedInUser()`** - Updates UI for authenticated users

### Authentication Flow

1. **Page Load**: Check for existing token in localStorage
2. **Login**: Submit credentials → Receive JWT token → Store token → Fetch profile
3. **Registration**: Create account → Auto-login → Store token → Fetch profile
4. **Session Persistence**: Token stored in localStorage survives browser restarts
5. **Logout**: Clear token from localStorage and update UI

### UI Changes Based on Authentication

**Not Logged In**:
- Shows "Sign In" and "Sign Up" buttons in header
- Chat bot gives generic responses

**Logged In**:
- Shows "Hello, [Name]!" and "Logout" button in header
- Chat bot personalizes responses with user name
- Access to protected features

## Setup Instructions

### 1. Start the Backend
```bash
cd server
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Open the HTML File
Simply open `server/agents/weather_agent/test_ui/index.html` in your web browser.

### 3. Test Authentication
1. Click "Sign Up" to create a new account
2. Fill in the form and submit
3. You should be automatically logged in
4. Try logging out and signing in again
5. Test the chat functionality as both anonymous and authenticated user

## CORS Configuration

The backend includes CORS middleware configured to accept requests from:
- `http://localhost:5173` (React development server)
- `http://localhost:3000` (Alternative React port)
- `file://` (Local HTML files)
- `*` (All origins for development)

⚠️ **Important**: Remove the wildcard (`*`) CORS setting in production!

## Security Features

### Password Security
- Passwords are hashed using bcrypt before storage
- Plain text passwords are never stored in the database

### JWT Tokens
- Tokens expire after 60 minutes (configurable)
- Tokens include user ID in the `sub` claim
- Secret key is configurable via environment variables

### Input Validation
- Email format validation
- Required field validation
- Password minimum length requirements
- Username/email uniqueness checks

## Error Handling

The frontend handles various error scenarios:

- **Invalid credentials**: Shows "Incorrect email/username or password"
- **User already exists**: Shows "User with given email or username already exists"
- **Network errors**: Shows connection error messages
- **Token expiry**: Automatically logs out user and shows login form

## Testing

### Manual Testing Steps

1. **Registration Test**:
   - Open index.html in browser
   - Click "Sign Up"
   - Enter test credentials
   - Verify account creation and auto-login

2. **Login Test**:
   - Use existing credentials
   - Click "Sign In"
   - Verify successful login and UI update

3. **Session Persistence Test**:
   - Login successfully
   - Refresh the browser
   - Verify you remain logged in

4. **Logout Test**:
   - Click "Logout" button
   - Verify UI returns to logged-out state
   - Verify token is removed from localStorage

### API Testing with curl

```bash
# Test registration
curl -X POST "http://localhost:8001/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "name": "Test User",
    "email": "test@example.com", 
    "password": "testpass123"
  }'

# Test login
curl -X POST "http://localhost:8001/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123"

# Test profile (replace TOKEN with actual token)
curl -X GET "http://localhost:8001/api/auth/me" \
  -H "Authorization: Bearer TOKEN"
```

## Troubleshooting

### Common Issues

1. **CORS Errors**:
   - Ensure backend CORS settings include the correct origins
   - Check browser developer console for specific CORS errors

2. **Connection Refused**:
   - Verify backend is running on port 8001
   - Check firewall settings

3. **MongoDB Connection Issues**:
   - Ensure MongoDB is running
   - Check connection string in config

4. **Token Issues**:
   - Clear localStorage if tokens are corrupted
   - Check token expiration settings

### Browser Developer Tools

Use the following to debug issues:
- **Network tab**: Monitor API requests/responses
- **Console tab**: Check for JavaScript errors  
- **Application tab**: Inspect localStorage for tokens
- **Security tab**: Check for HTTPS/certificate issues

## Future Enhancements

Possible improvements for production:

1. **Enhanced Security**:
   - HTTPS enforcement
   - CSRF protection
   - Rate limiting on auth endpoints

2. **User Experience**:
   - Password reset functionality
   - Email verification
   - Social login options

3. **Session Management**:
   - Refresh token implementation
   - Multi-device session management
   - Remember me functionality

4. **Error Handling**:
   - Better error messages
   - Retry mechanisms
   - Offline support

---

This integration provides a solid foundation for authentication between your HTML frontend and FastAPI backend, with room for future enhancements based on your specific requirements.