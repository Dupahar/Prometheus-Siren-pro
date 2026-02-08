# vulnerable_app/app.py
"""
Vulnerable Flask Application for Demo/Testing.
Contains OWASP Top 10 vulnerabilities for Prometheus to fix.

⚠️ WARNING: This app is INTENTIONALLY VULNERABLE.
DO NOT deploy this in production!
"""

import os
import sqlite3
import subprocess
from flask import Flask, request, render_template_string, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "insecure_secret_key"  # VULN: Weak secret key

# Initialize SQLite database
DB_PATH = "users.db"


def init_db():
    """Initialize the demo database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            email TEXT
        )
    """)
    # Insert demo users
    cursor.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin', 'admin123', 'admin@example.com')")
    cursor.execute("INSERT OR IGNORE INTO users VALUES (2, 'user', 'password', 'user@example.com')")
    conn.commit()
    conn.close()


# ==========================================
# VULN 1: SQL Injection
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    VULNERABLE: SQL Injection in login.
    Attack: username = "admin' OR '1'='1' --"
    """
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        
        # VULNERABLE: String concatenation in SQL query
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        cursor.execute(query)  # VULN: SQL Injection!
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session["user"] = user[1]
            return redirect(url_for("dashboard"))
        return "Invalid credentials", 401
    
    return """
    <h1>Login</h1>
    <form method="POST">
        <input name="username" placeholder="Username"><br>
        <input name="password" type="password" placeholder="Password"><br>
        <button type="submit">Login</button>
    </form>
    """


# ==========================================
# VULN 2: Cross-Site Scripting (XSS)
# ==========================================
@app.route("/search")
def search():
    """
    VULNERABLE: Reflected XSS.
    Attack: ?q=<script>alert('XSS')</script>
    """
    query = request.args.get("q", "")
    
    # VULNERABLE: Unescaped user input in HTML
    html = f"""
    <h1>Search Results</h1>
    <p>You searched for: {query}</p>
    """
    return render_template_string(html)  # VULN: XSS!


# ==========================================
# VULN 3: Path Traversal
# ==========================================
@app.route("/file")
def read_file():
    """
    VULNERABLE: Path Traversal.
    Attack: ?name=../../../etc/passwd
    """
    filename = request.args.get("name", "readme.txt")
    
    # VULNERABLE: No path validation
    filepath = os.path.join("files", filename)  # VULN: Path Traversal!
    
    try:
        with open(filepath, "r") as f:
            content = f.read()
        return f"<pre>{content}</pre>"
    except FileNotFoundError:
        return "File not found", 404


# ==========================================
# VULN 4: Command Injection
# ==========================================
@app.route("/ping")
def ping():
    """
    VULNERABLE: Command Injection.
    Attack: ?host=127.0.0.1;cat /etc/passwd
    """
    host = request.args.get("host", "127.0.0.1")
    
    # VULNERABLE: Shell command with user input
    result = subprocess.run(
        f"ping -c 1 {host}",  # VULN: Command Injection!
        shell=True,
        capture_output=True,
        text=True,
    )
    return f"<pre>{result.stdout}</pre>"


# ==========================================
# VULN 5: Insecure Deserialization (simulated)
# ==========================================
@app.route("/data")
def data():
    """
    VULNERABLE: Simulated insecure deserialization.
    """
    import pickle
    import base64
    
    data_b64 = request.args.get("data", "")
    if data_b64:
        try:
            # VULNERABLE: Unpickling untrusted data
            data = pickle.loads(base64.b64decode(data_b64))  # VULN!
            return f"Data: {data}"
        except Exception as e:
            return f"Error: {e}", 400
    return "Provide ?data=<base64>"


# ==========================================
# VULN 6: Broken Access Control
# ==========================================
@app.route("/admin")
def admin():
    """
    VULNERABLE: No authentication check.
    """
    # VULNERABLE: No access control
    return """
    <h1>Admin Panel</h1>
    <p>Welcome, Administrator!</p>
    <ul>
        <li><a href="/admin/users">Manage Users</a></li>
        <li><a href="/admin/settings">Settings</a></li>
    </ul>
    """


# ==========================================
# Safe Routes
# ==========================================
@app.route("/")
def index():
    return """
    <h1>Vulnerable Demo App</h1>
    <p>⚠️ This app is intentionally vulnerable for testing Prometheus.</p>
    <ul>
        <li><a href="/login">Login (SQL Injection)</a></li>
        <li><a href="/search?q=test">Search (XSS)</a></li>
        <li><a href="/file?name=readme.txt">File Reader (Path Traversal)</a></li>
        <li><a href="/ping?host=127.0.0.1">Ping (Command Injection)</a></li>
        <li><a href="/admin">Admin (Broken Access Control)</a></li>
    </ul>
    """


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return f"<h1>Welcome, {session['user']}!</h1>"


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


# ==========================================
# Calculator (for Prometheus demo)
# ==========================================
@app.route("/calculate")
def calculate():
    """
    Endpoint with potential division by zero error.
    Used for Prometheus auto-patching demo.
    """
    a = request.args.get("a", type=float, default=10)
    b = request.args.get("b", type=float, default=2)
    op = request.args.get("op", default="add")
    
    if op == "add":
        result = a + b
    elif op == "sub":
        result = a - b
    elif op == "mul":
        result = a * b
    elif op == "div":
        result = a / b  # Potential ZeroDivisionError!
    else:
        return "Unknown operation", 400
    
    return {"a": a, "b": b, "op": op, "result": result}


if __name__ == "__main__":
    init_db()
    # Create files directory for path traversal demo
    os.makedirs("files", exist_ok=True)
    with open("files/readme.txt", "w") as f:
        f.write("This is a sample file.\nNothing sensitive here.")
    
    # Run the vulnerable app
    app.run(host="0.0.0.0", port=5000, debug=True)
