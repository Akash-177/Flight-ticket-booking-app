from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash, g
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
import functools

app = Flask(__name__)

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'flight1'
app.config['MYSQL_HOST'] = 'localhost'
app.config.update(SECRET_KEY='dev')

mysql = MySQL(app)


@app.before_request
def load_logged_in_user():
    uname = session.get('uname')
    g.uname = uname if uname else None

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.uname is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template('home.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    if request.args.get('user_reg'):
        flash('User successfully created!')
    if request.method == 'POST':
        username = request.form['input_uname']
        password = request.form['input_passwd']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE uname = %s", [username])
        user = cur.fetchone()
        cur.close()

        if user is None:
            error = "Incorrect Username!"
        elif not check_password_hash(user[1], password):
            error = "Incorrect Password!"

        if error is None:
            session.clear()
            session['pno'] = user[2]
            session['uname'] = user[0]
            return redirect(url_for('bookticket'))

        flash(error)

    return render_template('login.html', error=error)

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        _pno = request.form['input_pno']
        _fname = request.form['input_fname']
        _lname = request.form['input_lname']
        _dob = request.form['input_dob']
        _address = request.form['input_address']
        _phone = request.form['input_phone']
        _uname = request.form['input_uname']
        _passwd = request.form['input_password']
        _conf_pass = request.form['conf_password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM users WHERE uname = %s or pno = %s or phone_no = %s", (_uname, _pno, _phone)
        )
        if cur.fetchone() is not None:
            error = 'User is already registered'

        if _passwd != _conf_pass:
            error = 'Password and Confirm password fields do not match'

        if error is None:
            cur.execute(
                "INSERT INTO users (uname, passwd, pno, first_name, last_name, DOB, phone_no, address) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (_uname, generate_password_hash(_passwd), _pno, _fname, _lname, _dob, _phone, _address)
            )
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('login', user_reg=True))

        flash(error)
    return render_template('signup.html', error=error)

@app.route("/logout", methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/bookticket", methods=['GET', 'POST'])
@login_required
def bookticket():
    if request.method == 'GET':
        return render_template('app.html')
    else:
        if request.form['submit_button'] == 'select_srcdest':
            _src = request.form['inputsrc']
            _dst = request.form['inputdest']
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT DISTINCT a1.location_code, a2.location_code FROM airport a1, airport a2 WHERE a1.city = %s and a2.city = %s", (_src, _dst)
            )
            airports = cur.fetchone()
            cur.execute(
                """SELECT flight.*, airline_name FROM flight, airline
                   WHERE source = %s and destination = %s AND
                   airline_id = (
                       SELECT DISTINCT flightScheduledForAirline.airline_id from flightScheduledForAirline
                       WHERE flightScheduledForAirline.airline_id = airline.airline_id AND
                       flight.flight_id = flightScheduledForAirline.flight_id
                   ) AND flight_id NOT IN (
                       SELECT ticket.flight_id from ticket
                       WHERE ticket.uname = %s
                    )""", (_src, _dst, session['uname'])
            )
            flights = cur.fetchall()
            cur.close()

            if flights:
                return render_template('app.html', flights=flights, airports=airports)
            else:
                error = 'No flights available'
                flash(error)
                return render_template('app.html', src_dest=(_src, _dst), error=error)
        else:
            fno = request.form['submit_button']
            return redirect(url_for('payment', flight=fno))

@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'GET':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE uname = %s", [session['uname']])
        res = cur.fetchall()
        cur.execute(
            """SELECT * FROM ticket 
               JOIN flight ON ticket.flight_id = flight.flight_id
                WHERE uname = %s""", [session['uname']]
        )
        tkts = cur.fetchall()
        cur.close()
        return render_template('users_view.html', result=res, tickets=tkts)
    else:
        if request.form['submit_button'] == 'update':
            return redirect(url_for('update'))
        else:
            tno = request.form['submit_button']
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE uname = %s", [session['uname']])
            res = cur.fetchall()
            cur.execute(
                """DELETE FROM ticket
                   WHERE ticket_id = %s""", [tno]
            )
            mysql.connection.commit()
            cur.execute(
            """SELECT * FROM ticket 
               JOIN flight ON ticket.flight_id = flight.flight_id
                WHERE uname = %s""", [session['uname']]
            )
            tkts = cur.fetchall()
            cur.close()
            return render_template('users_view.html', result=res, tickets=tkts)

@app.route("/update", methods=['GET', 'POST'])
@login_required
def update():
    if request.method == 'POST':
        _pno = request.form['input_pno']
        _fname = request.form['input_fname']
        _lname = request.form['input_lname']
        _dob = request.form['input_dob']
        _address = request.form['input_address']
        _phone = request.form['input_phone']
        _passwd = request.form['input_password']

        cur = mysql.connection.cursor()
        if request.form.get('input_pno', None):
            cur.execute(
            "UPDATE users SET pno=%s WHERE uname=%s", (_pno, session['uname'])
        )
        if request.form.get('input_fname', None):
            cur.execute(
            "UPDATE users SET first_name=%s WHERE uname=%s", (_fname, session['uname'])
        )
        if request.form.get('input_lname', None):
            cur.execute(
            "UPDATE users SET last_name=%s WHERE uname=%s", (_lname, session['uname'])
        )
        if request.form.get('input_dob', None):
            cur.execute(
            "UPDATE users SET DOB=%s WHERE uname=%s", (_dob, session['uname'])
        )
        if request.form.get('input_address', None):
            cur.execute(
            "UPDATE users SET address=%s WHERE uname=%s", (_address, session['uname'])
        )
        if request.form.get('input_phone', None):
            cur.execute(
            "UPDATE users SET phone_no=%s WHERE uname=%s", (_phone, session['uname'])
        )
        if request.form.get('input_password', None):
            cur.execute(
            "UPDATE users SET passwd=%s WHERE uname=%s", (generate_password_hash(_passwd), session['uname'])
        )
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('profile'))

    return render_template('update.html')

@app.route("/payment", methods=['GET', 'POST'])
@login_required
def payment():
    if request.method == 'GET' and not request.args.get('flight'):
        return redirect(url_for('bookticket'))
    elif request.args['flight']:
        flight_no = request.args['flight']
        username = session['uname']
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM ticket WHERE flight_id = %s", [flight_no])
        count = int(cur.fetchone()[0])
        ticket_id = str(flight_no) + str(count + 2)
        price = 100
        status = 'Booked'

        cur.execute(
            "INSERT INTO ticket (ticket_id, uname, flight_id, status, price) VALUES (%s, %s, %s, %s, %s)",
            (ticket_id, username, flight_no, status, price)
        )
        mysql.connection.commit()

        cur.execute(
            "INSERT INTO booking (ticket_id, flight_id) VALUES (%s, %s)", (ticket_id, flight_no)
        )
        mysql.connection.commit()

        cur.execute(
            "INSERT INTO userMakesPayment (uname, ticket_id) VALUES (%s, %s)", (username, ticket_id)
        )
        mysql.connection.commit()

        cur.execute(
            """SELECT ticket_id, booking.flight_id, source, destination, first_name, last_name
                FROM booking, flight, users WHERE 
                ticket_id = %s AND
                booking.flight_id = flight.flight_id AND 
                users.uname = %s""", (ticket_id, session['uname'])
        )
        payment = cur.fetchone()
        cur.close()
        return render_template('payment.html', payment=payment)

@app.route("/print", methods=['GET', 'POST'])
@login_required
def print():
    if request.method == 'GET':
        return render_template('print.html', payment=payment)

if __name__ == "__main__":
    app.run(debug=True)
