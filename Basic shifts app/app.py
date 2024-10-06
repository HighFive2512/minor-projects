from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3

app = Flask(__name__, template_folder='html', static_folder='static')

def init_db():
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS TeamMembers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Shifts (
        id INTEGER PRIMARY KEY,
        member_id INTEGER,
        shift_date DATE,
        shift_type TEXT,
        FOREIGN KEY (member_id) REFERENCES TeamMembers(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Holidays (
        id INTEGER PRIMARY KEY,
        holiday_date DATE UNIQUE,
        holiday_name TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS DaysOff (
        id INTEGER PRIMARY KEY,
        member_id INTEGER,
        day_off_date DATE,
        reason TEXT,
        FOREIGN KEY (member_id) REFERENCES TeamMembers(id)
    )
    ''')

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/team_members')
def view_team_members():
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM TeamMembers')
    team_members = cursor.fetchall()
    conn.close()
    return render_template('view_team_members.html', team_members=team_members)

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']

        conn = sqlite3.connect('shift_scheduler.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO TeamMembers (name, role) VALUES (?, ?)', (name, role))
        conn.commit()
        conn.close()
        return redirect(url_for('view_team_members'))
    return render_template('add_member.html')

@app.route('/schedule_shift', methods=['GET', 'POST'])
def schedule_shift():
    if request.method == 'POST':
        member_id = request.form['member_id']
        shift_date = request.form['shift_date']
        shift_type = request.form['shift_type']

        conn = sqlite3.connect('shift_scheduler.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO Shifts (member_id, shift_date, shift_type) VALUES (?, ?, ?)', 
                       (member_id, shift_date, shift_type))
        conn.commit()
        conn.close()
        return redirect(url_for('view_shifts'))

    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM TeamMembers')
    team_members = cursor.fetchall()
    conn.close()
    return render_template('schedule_shift.html', team_members=team_members)

@app.route('/view_shifts')
def view_shifts():
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Shifts.id, TeamMembers.name, Shifts.shift_date, Shifts.shift_type 
    FROM Shifts 
    JOIN TeamMembers ON Shifts.member_id = TeamMembers.id
    ''')
    shifts = cursor.fetchall()
    conn.close()
    return render_template('view_shifts.html', shifts=shifts)

@app.route('/delete_member/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TeamMembers WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_team_members'))

@app.route('/get_events')
def get_events():
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT S.shift_date, S.shift_type, S.member_id, T.name
        FROM Shifts S
        JOIN TeamMembers T ON S.member_id = T.id
    """)
    shifts = cursor.fetchall()

    events = [
        {
            'title': shift[1],
            'start': shift[0],
            'resourceId': str(shift[2]),
            'memberName': shift[3],
            'shiftType': shift[1]
        }
        for shift in shifts
    ]

    conn.close()
    return jsonify(events)

@app.route('/get_team_members')
def get_team_members():
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM TeamMembers")
    members = cursor.fetchall()
    resources = [{'id': str(member[0]), 'title': member[1]} for member in members]
    conn.close()
    return jsonify(resources)

if __name__ == '__main__':
    app.run(debug=True)
