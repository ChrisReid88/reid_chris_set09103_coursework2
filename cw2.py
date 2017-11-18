from flask import Flask, request, redirect, render_template, url_for, session, g
import sqlite3, os, time, bcrypt
from functools import wraps

app = Flask(__name__)
DB_ROOT = os.path.dirname(os.path.realpath(__file__))
DATABASE = os.path.join(DB_ROOT, 'static', 'db.db')
app.secret_key = os.urandom(24)
salt =  bcrypt.gensalt()

def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = sqlite3.connect(DATABASE)
        g.db = db
    return db

@app.teardown_appcontext
def close_db_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('static/schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit


def requires_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        status = session.get('logged_in', False)
        if not status:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        valid = check_auth(username, password)

        if not valid:
            error = 'Sorry, the username or password entered is incorrect. Try again.'
        else:
            session['username'] = username
            session['password'] = password
            session['logged_in'] = True
            return redirect(url_for('wall'))
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = bcrypt.hashpw(request.form['password'].encode('utf8'), salt)
        print new_password
        if new_username in rows[0]:
            error = 'Sorry, that username has been taken. Please try another.'
        else:
            with db:
                cur.execute("INSERT INTO users(username, password) VALUES (?,?)", (new_username, new_password))
                db.commit
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


def check_auth(username, password):
    db = get_db()
    valid = False
    with db:
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=(?)", (username,))
        row = cur.fetchall()
        if row:
            session['user_id'] = row[0][0]
            db_username = row[0][1]
            db_password = row[0][2]
            if db_username == username and db_password == bcrypt.hashpw(password.encode('utf8'), db_password.encode('utf8')):

                valid = True

    return valid


@app.route('/wall', methods=['POST', 'GET'])
@requires_login
def wall():
    comments = None
    users=get_users()
    print users
    id = session['user_id']
    if get_comments(id):
        comments = get_comments(id)
    if request.method == 'POST':
        make_post(id)
        return redirect(url_for('wall'))
    return render_template('wall.html', comments=comments, users=users)


@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))


def make_post(user_id):
    comment = request.form['comment']
    if comment:
        db = sqlite3.connect(DATABASE)
        with db:
            cur = db.cursor()
            cur.execute("INSERT INTO comments(user_id, comment) VALUES (?,?)", (user_id, comment))
            db.commit()


def get_comments(uid):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM users INNER JOIN comments on (users.user_id=comments.user_id) WHERE comments.user_id=(?)",
        (uid,))
    rows = cur.fetchall()
    return rows

def get_users():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT username FROM users")
    rows = cur.fetchall()
    return rows

if __name__ == '__main__':
    app.run(debug=True)
