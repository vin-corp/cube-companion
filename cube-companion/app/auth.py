from flask import Blueprint, request, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required
from flask import flash
from .models import User
from .extensions import db, login_manager

auth = Blueprint("auth", __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.", "error")
            return redirect(url_for("auth.register"))

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("main.dashboard"))

    return render_template("register.html")



@auth.route("/users")
def list_users():
    users = User.query.all()
    return "<br>".join([f"{u.id}: {u.username}" for u in users])


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
