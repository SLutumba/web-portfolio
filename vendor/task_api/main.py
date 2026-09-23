import os

from flask import Flask
from flask_jwt_extended import JWTManager

from app.api.tasks import task_blueprint
from app.api.users import user_blueprint

app = Flask(__name__)
app.register_blueprint(task_blueprint)
app.register_blueprint(user_blueprint)

app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")

jwt = JWTManager(app)

@app.route("/")
def main():
    return "Landing. This is main."

if __name__ == "__main__":
    app.run(debug=True)
