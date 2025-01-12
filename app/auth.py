# This handles all my authentication routes (login, register, etc.)
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from .models import User, Session
from sqlalchemy import desc
from . import db

auth = Blueprint('auth', __name__)

@auth.route('/home')
@login_required
def home():
    # Get the current user's sessions and sessions from people they follow
    following_ids = [user.id for user in current_user.following]
    following_ids.append(current_user.id)  # Include current user's sessions
    
    sessions = Session.query\
        .filter(Session.user_id.in_(following_ids))\
        .order_by(desc(Session.session_date))\
        .limit(10)\
        .all()
        
    return render_template('home.html', sessions=sessions)

@auth.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    return redirect(url_for('auth.home'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register')
def register():
    return render_template('register.html')

@auth.route('/register', methods=['POST'])
def register_post():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    privacy_setting = request.form.get('privacy_setting', 'public')

    if User.query.filter_by(email=email).first():
        flash('Email already exists')
        return redirect(url_for('auth.register'))
        
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('auth.register'))
        
    if len(password) < 8:
        flash('Password must be at least 8 characters long')
        return redirect(url_for('auth.register'))

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=username,
        privacy_setting=privacy_setting,
        level=1,
        exp=0
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))