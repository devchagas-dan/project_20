#FALTA POUCO, FALTA SÓ VERIFICAR ERRO EM BUY HANDELS FRACTIONAL, NEGATIVE AND NON-NUMERIC SHARES EXPECTED STATUS CODE 400 BUT GOT 200

import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user = session["user_id"]

    rows = db.execute(
        "SELECT symbol , SUM(shares) AS shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING (shares) > 0",
        user,
        )
    holdings = []
    grand_total = 0
    for row in rows:
        stock = lookup(row["symbol"])
        holdings.append(
            {
                "symbol": stock["symbol"],
                "name": stock["name"],
                "shares": row["shares"],
                "price": stock["price"],
                "total": stock["price"] * row["shares"],
            }
        )
        grand_total += stock["price"] * row["shares"]
    rows = db.execute("SELECT cash FROM users WHERE id = ?", user)
    cash = rows[0]["cash"]
    grand_total += cash

    return render_template(
        "index.html", cash=cash, holdings=holdings, grand_total=grand_total
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        share = float(request.form.get("shares"))
        shares = round(share)

        if shares < 0:
            return apology("might be greater than zero", 400)

        if not symbol:
            return apology("must provide a symbol", 400)

        stock = lookup(symbol)

        if stock == None:
            return apology("symbol doesn't exist", 400)


        user = session["user_id"]

        rows = db.execute("SELECT cash FROM users WHERE id = ?", user)
        user_money = rows[0]["cash"]

        cash = user_money - shares * stock["price"]
        if cash < 0:
            return apology("can't afford it", 400)

        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, user)

        now = datetime.now()

        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price, date, name) VALUES (?,?,?,?,?,?)",
            user,
            stock["symbol"],
            shares,
            stock["price"],
            now,
            stock["name"],
        )

        flash("Bought")

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user = session["user_id"]
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ?", user)
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("must provide a symbol", 400)

        shares = lookup(symbol)

        if shares == None:
            return apology("symbol doesn't exist", 400)

        return render_template(
            "quoted.html",
            name=shares["name"],
            price=shares["price"],
            symbol=shares["symbol"],
        )

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
    else:
        return render_template("register.html")

    if not request.form.get("username"):
        return apology("must provide username", 400)

    elif not request.form.get("password"):
        return apology("must provide password", 400)
    elif password != confirmation:
        return apology("passwords don't match", 400)

    hash_password = generate_password_hash(password)

    try:
       prim_key = db.execute(
        "INSERT INTO users (username, hash) VALUES(?, ?)", username, hash_password
        )
    except:
        return apology("username already exists", 400)
    if prim_key is None:
        return apology("registration error", 400)

    return redirect("/login")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = int(request.form.get("shares"))

        if not symbol:
            return apology("must provide a symbol", 400)

        stock = lookup(symbol)

        user = session["user_id"]

        rows = db.execute(
            "SELECT symbol , SUM(shares) AS shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING (shares) > 0",
            user,
        )
        for row in rows:
            if row["symbol"] == symbol:
                if shares > row["shares"]:
                    return apology("too many shares, 403")

        rows = db.execute("SELECT cash FROM users WHERE id = ?", user)
        cash = rows[0]["cash"]

        updated_cash = cash + shares * stock["price"]

        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user)

        now = datetime.now()

        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price, date, name) VALUES (?,?,?,?,?,?)",
            user,
            stock["symbol"],
            -1 * shares,
            stock["price"],
            now,
            stock["name"],
        )

        flash("Sold")

        return redirect("/")

    else:
        user = session["user_id"]
        rows = db.execute(
            "SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0",
            user,
        )
        return render_template("sell.html", symbols=[row["symbol"] for row in rows])


@app.route("/add_money", methods=["GET", "POST"])
@login_required
def add_money():
    if request.method == "POST":
        amount = float(request.form.get("quantity"))

        user = session["user_id"]

        if amount > 0:
            session["cash"] = session.get("cash", 0) + amount

            db.execute("UPDATE users SET cash = ? WHERE id = ?", session["cash"], user)

            return redirect("/")

        else:
            return apology("amount might be positive")

    else:
        return render_template("add_money.html")
