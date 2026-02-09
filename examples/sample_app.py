"""Sample web application to demonstrate code visualization"""


class DatabaseConnection:
    """Database connection manager"""
    
    def __init__gi(self, host: str, port: int):
        self.host = host
        self.port = port
    
    def connect(self):
        """Establish database connection"""
        return True
    
    def query(self, sql: str):
        """Execute SQL query"""
        return []


class UserService:
    """User management service"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def get_user(self, user_id: int):
        """Get user by ID"""
        result = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return self._parse_user(result)
    
    def create_user(self, username: str, email: str):
        """Create new user"""
        self._validate_email(email)
        user_id = self._insert_user(username, email)
        return user_id
    
    def _parse_user(self, result):
        """Parse user data"""
        if result:
            return result[0]
        return None
    
    def _validate_email(self, email: str):
        """Validate email format"""
        return "@" in email
    
    def _insert_user(self, username: str, email: str):
        """Insert user into database"""
        self.db.query(f"INSERT INTO users (username, email) VALUES ({username}, {email})")
        return 1


class AuthService:
    """Authentication service"""
    
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    def login(self, username: str, password: str):
        """User login"""
        user = self._find_user(username)
        if user and self._verify_password(password):
            return self._create_session(user)
        return None
    
    def _find_user(self, username: str):
        """Find user by username"""
        return None
    
    def _verify_password(self, password: str):
        """Verify password"""
        return True
    
    def _create_session(self, user):
        """Create user session"""
        return {"user_id": user.get("id")}


def initialize_app():
    """Initialize application"""
    db = DatabaseConnection("localhost", 5432)
    db.connect()
    user_service = UserService(db)
    auth_service = AuthService(user_service)
    return auth_service


def handle_request(auth_service: AuthService, request: dict):
    """Handle HTTP request"""
    if request.get("action") == "login":
        return auth_service.login(request.get("username"), request.get("password"))
    elif request.get("action") == "register":
        return handle_registration(auth_service, request)
    return None


def handle_registration(auth_service: AuthService, request: dict):
    """Handle user registration"""
    user_service = auth_service.user_service
    user_id = user_service.create_user(request.get("username"), request.get("email"))
    return {"user_id": user_id}


def main():
    """Main entry point"""
    auth_service = initialize_app()
    
    login_request = {
        "action": "login",
        "username": "admin",
        "password": "password123"
    }
    
    result = handle_request(auth_service, login_request)
    print(f"Login result: {result}")


def test_bare_except():
    """Test function with dangerous 'except: pass' pattern"""
    try:
        print("Doing something risky...")
        1 / 0
    except:  # ← Bare except
        pass  # ← This will be caught by your detector!

def test_unused():
    '''Test function with unused variable'''
    used = "ok"
    unused_var = 42  # ← this will be detected
    print(used)

if __name__ == "__main__":
    main()

