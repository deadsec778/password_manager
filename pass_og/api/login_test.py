import sys
import os

# FORCE the project root into sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from flask import Flask, request, render_template_string
from users.login_user import login_user

app = Flask(__name__)

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login Test</title>
</head>
<body style="font-family: Arial; padding: 40px;">
    <h2>🔐 Test Login Page</h2>
    <form method="POST">
        <label>Username:</label><br>
        <input name="username" required><br><br>

        <label>Master Password:</label><br>
        <input type="password" name="password" required><br><br>

        <button type="submit">Login</button>
    </form>

    {% if message %}
        <hr>
        <h3>{{ message }}</h3>
        {% if role %}
            <p><b>User ID:</b> {{ user_id }}</p>
            <p><b>Role:</b> {{ role }}</p>
            <p><b>Cipher object loaded:</b> Yes</p>
        {% endif %}
    {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form.get("username")
        master_password = request.form.get("password")

        user_id, role, cipher = login_user(username, master_password)

        if user_id:
            return render_template_string(
                LOGIN_PAGE,
                message="✅ Login Successful",
                user_id=user_id,
                role=role
            )
        else:
            return render_template_string(
                LOGIN_PAGE,
                message="❌ Login Failed",
                role=None,
                user_id=None
            )

    return render_template_string(LOGIN_PAGE, message=None)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
