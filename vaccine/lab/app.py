"""Application volontairement vulnerable aux injections SQL.

Banc de test pour l'outil vaccine. NE JAMAIS EXPOSER SUR INTERNET.

    VACCINE_DB=sqlite python app.py     (par defaut)
    VACCINE_DB=mysql  python app.py
"""

import os
import sqlite3

from flask import Flask, request

ENGINE = os.environ.get("VACCINE_DB", "sqlite")
app = Flask(__name__)


def connect():
    if ENGINE == "mysql":
        import pymysql
        return pymysql.connect(host="127.0.0.1", port=3306,
                               user="root", password="root", database="shop")
    return sqlite3.connect("shop.db")


def query(sql):
    """Execute le SQL brut. Toute erreur remonte telle quelle a l'appelant."""
    con = connect()
    cur = con.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    con.close()
    return rows


def page(title, sql, rows=None, error=None, note=None):
    html = "<h1>%s</h1>" % title
    html += "<p style='color:#888'>debug SQL: <code>%s</code></p>" % sql
    if error is not None:
        html += "<p>SQL error: %s</p>" % error
    if note is not None:
        html += "<p>%s</p>" % note
    if rows:
        html += "<ul>"
        for row in rows:
            html += "<li>%s</li>" % " | ".join(str(col) for col in row)
        html += "</ul>"
    return html


@app.route("/")
def index():
    return page("Lab (%s)" % ENGINE, "-", note=(
        "<a href='/product?id=1'>/product?id=1</a> (entier)<br>"
        "<a href='/search?name=a'>/search?name=a</a> (chaine)<br>"
        "/login (POST: user, pass)"))


@app.route("/product")
def product():
    """Point d'injection en contexte ENTIER : pas de quote a echapper."""
    pid = request.args.get("id", "1")
    sql = "SELECT id, name, price FROM products WHERE id = " + pid
    try:
        return page("Product", sql, rows=query(sql))
    except Exception as err:
        return page("Product", sql, error=err)


@app.route("/search")
def search():
    """Point d'injection en contexte CHAINE : il faut sortir de la quote."""
    name = request.args.get("name", "")
    sql = "SELECT id, name, price FROM products WHERE name LIKE '%" + name + "%'"
    try:
        return page("Search", sql, rows=query(sql))
    except Exception as err:
        return page("Search", sql, error=err)


@app.route("/login", methods=["POST"])
def login():
    """Point d'injection en POST. La reponse ne varie que par vrai/faux."""
    user = request.form.get("user", "")
    password = request.form.get("pass", "")
    sql = ("SELECT id, username FROM users WHERE username = '" + user +
           "' AND password = '" + password + "'")
    try:
        rows = query(sql)
    except Exception as err:
        return page("Login", sql, error=err)
    if rows:
        return page("Login", sql, note="Welcome back, %s" % rows[0][1])
    return page("Login", sql, note="Bad credentials")


def seed():
    con = connect()
    cur = con.cursor()
    if ENGINE == "mysql":
        cur.execute("CREATE TABLE IF NOT EXISTS products "
                    "(id INT, name VARCHAR(50), price VARCHAR(20))")
        cur.execute("CREATE TABLE IF NOT EXISTS users "
                    "(id INT, username VARCHAR(50), password VARCHAR(50))")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER, name TEXT, price TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, username TEXT, password TEXT)")
    cur.execute("DELETE FROM products")
    cur.execute("DELETE FROM users")
    cur.execute("INSERT INTO products VALUES (1, 'Keyboard', '49')")
    cur.execute("INSERT INTO products VALUES (2, 'Mouse', '19')")
    cur.execute("INSERT INTO products VALUES (3, 'Screen', '199')")
    cur.execute("INSERT INTO users VALUES (1, 'admin', 's3cr3t')")
    cur.execute("INSERT INTO users VALUES (2, 'enzo', 'hunter2')")
    cur.execute("INSERT INTO users VALUES (3, 'guest', 'guest')")
    con.commit()
    con.close()


if __name__ == "__main__":
    seed()
    print("moteur: %s" % ENGINE)
    app.run(host="127.0.0.1", port=5000, debug=False)
