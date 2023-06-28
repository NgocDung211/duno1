import os
import datetime
import pytz
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helper import login_required
from flask_mail import Mail, Message
import random
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import time


# Congifure application
app = Flask(__name__)

app.secret_key = "NgocDung211"

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"

app.config["MAIL_SERVER"] = "smtp-relay.sendinblue.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "dungdodz@gmail.com"
app.config["MAIL_PASSWORD"] = "x3p8TOAsUZhLrqbv"

mail = Mail(app)

db = SQL("sqlite:///project.db")


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "GET":
        current_id = session["user_id"]
        random_quote = get_random_quote(current_id)
        return render_template("index.html", random_quote=random_quote)
    else:
        current_id = session["user_id"]
        quote = request.form.get("quote")
        if not quote:
            flash("Please enter a quote")
            return redirect("/")
        db.execute(
            "INSERT INTO quotes (user_id, quote) VALUES(?, ?)", current_id, quote
        )
        return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        session.clear()
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Please enter your username and password")
            return redirect("/login")  # Redirect to the login page


        user_infor = db.execute("SELECT * FROM users WHERE name = ?", username)
        if len(user_infor) == 0:
            flash("The username does not exsit")
            return redirect("/login")
        hash_password = user_infor[0]["password"]
        if check_password_hash(hash_password, password) == False:
            flash("Password is incorrect. Please try again.")
            return redirect("/login")

        else:
            session["user_id"] = user_infor[0]["id"]
            db.execute("INSERT INTO time (user_id) VALUES (?)", session["user_id"])
            return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        email = request.form.get("email")

        if not username or not password or not confirmation or not email:
            flash("Please enter your username and password and confirmation and email")
            return redirect("/register")
        if len(username) <8 or len(password) < 8:
            flash("User name and password must contain at least 8 characters")
            return redirect("/register")
        if password != confirmation:
            flash("The password and confirmation is not the same")
            return redirect("/register")

        try:
            db.execute(
                "INSERT INTO users (name, password, email) VALUES (?,?,?)",
                username,
                generate_password_hash(password),
                email,
            )
            user_infor = db.execute("SELECT * FROM users WHERE name = ?", username)
            session["user_id"] = user_infor[0]["id"]
            return redirect("/login")
        except:
            flash("The account is already exsist, please try other user name")
            return redirect("/register")

@app.route("/forget", methods=["GET", "POST"])
def forget():
    if request.method == "GET":
        return render_template("forgetpassword.html")
    else:

        input_email = request.form.get("email")
        try:
            user_email = db.execute("SELECT email FROM users WHERE email =?", input_email)[0]["email"]
            print(user_email)
            if user_email is not None:
                send_password(user_email)
            else:
                return flask("Email is not correct")
        except:
            flash("Some thing went wrong please try again in get email")
        return redirect("/login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/quote")
@login_required
def quote():
    current_id = session["user_id"]
    quotes = db.execute("SELECT quote FROM quotes WHERE user_id=?", current_id)
    return render_template("quote.html", quotes=quotes)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    current_id = session["user_id"]
    id = None
    if request.method == "GET":
        quote1 = request.args.get("quote")
        id = db.execute(
            "SELECT id FROM quotes where user_id=? AND quote =?", current_id, quote1
        )[0]["id"]
        return render_template("edit.html", quote=quote1, id=id)
    else:
        quote_changed = request.form.get("quote_changed")
        id = request.form.get("id")  # Retrieve the original quote value
        if not quote_changed:
            flask("You need to give the quote")
            return redirect("/")
        db.execute(
            "UPDATE quotes SET quote = ? WHERE user_id = ? AND id = ?",
            quote_changed,
            current_id,
            id,
        )

        quotes = db.execute("SELECT quote FROM quotes WHERE user_id=?", current_id)
        return render_template("quote.html", quotes=quotes)


@app.route("/delete", methods=["POST"])
@login_required
def delete():
    if request.method == "POST":
        current_id = session["user_id"]
        quote = request.form.get("quote")
        db.execute(
            "DELETE FROM quotes WHERE quote = ? AND user_id =?", quote, current_id
        )
        quotes = db.execute("SELECT quote FROM quotes WHERE user_id=?", current_id)
        return render_template("quote.html", quotes=quotes)


@app.route("/account", methods=["POST", "GET"])
@login_required
def account():
    current_id = session["user_id"]
    if request.method == "GET":
        return render_template("account.html")
    else:
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")
        if old_password == new_password:
            flash("The old password and new is the same")
            return redirect("/account")
        if not new_password or not confirmation:
            flash("Please enter your password and confirmation")
            return redirect("/account")
        if new_password != confirmation:
            flash("The password and confirmation is not the same")
            return redirect("/account")
        password = db.execute("SELECT password from users where id =?", current_id)[0][
            "password"
        ]
        if check_password_hash(old_password, password):
            flash("The password is not correct")
            return redirect("/account")
        try:
            db.execute(
                "UPDATE users SET password =? where id = ?",
                generate_password_hash(new_password),
                current_id,
            )
            flash("Your password has been changed")
            return redirect("/")
        except:
            flash("Get problem please try again")
            return redirect("/")


@app.route("/contact", methods=["GET"])
def contact():
    if request.method == "GET":
        return render_template("contact.html")


@app.route("/general_settings", methods=["GET", "POST"])
def settings():
    current_id = session["user_id"]
    timezones = pytz.all_timezones
    time = db.execute("SELECT* FROM time where user_id = ?", current_id)
    notification_enabled = time[0]["notification_enabled"]
    time_from_db = time[0]["time_notification"]
    pattern = re.compile("^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$")

    if pattern.match(time_from_db):
        time_object = datetime.datetime.strptime(time_from_db, "%H:%M:%S")
        time_notification = time_object.strftime("%H:%M")
    else:
        time_notification = time_from_db

    if request.method == "GET":
        return render_template(
            "general.html",
            timezones=timezones,
            user_timezone=time[0]["timezone"],
            time_notification=time_notification,
            notification_enabled = notification_enabled
        )
    else:
        timezone = request.form.get("timezone")
        time_notifi = request.form.get("time_notification")
        email_enabled = request.form.get("Checkbox")
        if email_enabled == 'on':
            enable = 1
        else:
            enable = 0

        db.execute(
            "UPDATE time SET timezone = ?, time_notification = ?, notification_enabled =?, is_sent = 0  WHERE user_id = ?",
            timezone,
            time_notifi,
            enable,
            current_id
        )
        return redirect("/")


def get_random_quote(user_id):
    quotes = db.execute("SELECT quote FROM quotes WHERE user_id=?", user_id)
    if len(quotes) == 0:
        return
    else:
        random_quote = random.choice(quotes)
    return random_quote["quote"]


@app.route("/send_email", methods=["POST"])
def test_send_email():
    current_id = session["user_id"]
    user_email = db.execute("SELECT * FROM users WHERE id = ?", current_id)[0]["email"]
    send_email(user_email,current_id)
    #send_scheduled_emails()
    return redirect("/")




def send_email(user_email, user_id):
    random_quote = get_random_quote(user_id)
    msg = Message(
        subject="[From DuNo] Your Quote Today",
        recipients=[user_email],
        sender="dungdodz@gmail.com",
    )
    msg.body = random_quote
    mail.send(msg)

def send_password(user_email):
    msg = Message(
        subject="[From DuNo] Reset Password",
        recipients=[user_email],
        sender="dungdodz@gmail.com",
    )
    new_password = str(random.randint(10**6, 10**7))  # Convert the random password to a string
    msg.body = new_password
    print(new_password)
    try:
        db.execute("UPDATE users SET password = ? WHERE email =?", generate_password_hash (new_password),user_email)
        mail.send("Your new password is"+msg)

    except:
        flash("Some thing went wrong please try in send email")

def send_scheduled_emails():
    with app.app_context():
        users_to_email = db.execute(
            "SELECT user_id , time.id as time_id, email, timezone, time_notification, notification_enabled FROM users"
            " INNER JOIN time ON users.id = time.user_id WHERE is_sent == 0 AND notification_enabled ==1"
        )

        for user in users_to_email:
                user_timezone = pytz.timezone(user["timezone"])
                now = datetime.datetime.now(user_timezone)
                now_dt = now.strftime("%H:%M")
                if now_dt > user["time_notification"]:
                    print("=======Email has been send for "+user["email"]+"==========")
                    send_email(user["email"], user["user_id"])
                    db.execute(
                        "UPDATE time SET is_sent = 1 WHERE user_id = ?", (user["user_id"],)
                    )

def reset_sending_status():
    with app.app_context():
        db.execute("UPDATE time SET is_sent = 0")
        db.commit()


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(send_scheduled_emails, IntervalTrigger(minutes=1))
scheduler.add_job(reset_sending_status, CronTrigger(hour=0, minute=0))
scheduler.start()


def to_unix_timestamp(local_time, time_zone):
    dt = datetime.datetime.combine(datetime.datetime.today(), local_time)
    dt = time_zone.localize(dt)
    return int(time.mktime(dt.timetuple()))
