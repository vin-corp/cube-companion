from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import Cube
from .extensions import db

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("home.html")


@main.route("/dashboard")
@login_required
def dashboard():
    cubes = Cube.query.filter_by(user_id=current_user.id).order_by(Cube.created_at.desc()).all()
    return render_template("dashboard.html", user=current_user, cubes=cubes)


@main.route("/cube/new", methods=["GET", "POST"])
@login_required
def create_cube():
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        if name:
            cube = Cube(name=name, description=description, user_id=current_user.id)
            db.session.add(cube)
            db.session.commit()
            return redirect(url_for("main.dashboard"))
    return render_template("cube_form.html", cube=None)


@main.route("/cube/<int:cube_id>/edit", methods=["GET", "POST"])
@login_required
def edit_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        if name:
            cube.name = name
            cube.description = description
            db.session.commit()
            return redirect(url_for("main.dashboard"))
    return render_template("cube_form.html", cube=cube)


@main.route("/cube/<int:cube_id>/delete", methods=["POST"])
@login_required
def delete_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
    db.session.delete(cube)
    db.session.commit()
    return redirect(url_for("main.dashboard"))
