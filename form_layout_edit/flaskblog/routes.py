from flask import render_template, url_for, flash, redirect, request, session, jsonify
from flaskblog import app, bcrypt
from flaskblog.__init__ import db
from flaskblog.forms import RegistrationForm, LoginForm
from flaskblog.models import User, Books, Reviews
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import json
import requests

posts = Books.query.all()


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/search", methods=['GET','POST'])
def search():
    if request.method == "POST":
        searchQuery = request.form.get("searchQuery")
        print(searchQuery)

        # Avoid SQL Injection Using Bindings
        sql = "SELECT isbn, author, title \
               FROM Books \
               WHERE isbn LIKE :x \
               OR author LIKE :y \
               OR title LIKE :z"

        # I spent an hour wondering why I couldnt put the bindings inside the wildcard string...
        # https://stackoverflow.com/questions/3105249/python-sqlite-parameter-substitution-with-wildcards-in-like
        matchString = "%{}%".format(searchQuery)

        stmt = db.text(sql).bindparams(x=matchString, y=matchString, z=matchString)

        results = db.session.execute(stmt).fetchall()
        print(results)

        session["books"] = []

        for row in results:
            # A row is not JSON serializable so we pull out the pieces
            book = dict()
            book["isbn"] = row[0]
            book["author"] = row[1]
            book["title"] = row[2]
            session["books"].append(book)
        return render_template("search.html", searchedFor=searchQuery, books=session["books"])

    return render_template("search.html", title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/search/api/<string:isbn>")
def api(isbn): 
    data = "SELECT isbn, author, title \
               FROM Books \
               WHERE isbn LIKE :x \
               OR author LIKE :y \
               OR title LIKE :z"
    if data==None:
        return render_template('404.html')

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "YegUTeGTeZBfvDwYok7xg", "isbns": isbn})
    average_rating=res.json()['books'][0]['average_rating']
    work_ratings_count=res.json()['books'][0]['work_ratings_count']
    x = {
    "title": data.title,
    "author": data.author,
    "year": data.year,
    "isbn": isbn,
    "review_count": work_ratings_count,
    "average_rating": average_rating
    }

    return jsonify(x)
    # api = json.dumps(x)
    # return render_template("api.json",api=api)


@app.route("/account")
@login_required
def account():
    return render_template('account.html', title='Account')

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))
