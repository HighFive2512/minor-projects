from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, timedelta

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

@app.route('/schedule_shift', methods=['GET', 'POST'])
def schedule_shift():
    if request.method == 'POST':
        member_id = request.form['member_id']
        
        # Check if 'shift_dates' is in the form data
        if 'shift_dates' not in request.form:
            return "Error: No date range selected.", 400

        shift_dates_range = request.form['shift_dates']  # Get the range input

        # Extract start and end dates
        start_date_str, end_date_str = shift_dates_range.split(" to ")
        start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d")

        # Generate list of all weekdays in the range
        shift_dates = []
        delta = timedelta(days=1)

        while start_date <= end_date:
            if start_date.weekday() < 5:  # 0 = Monday, ..., 4 = Friday
                shift_dates.append(start_date.strftime("%Y-%m-%d"))
            start_date += delta

        shift_type = request.form['shift_type']

        conn = sqlite3.connect('shift_scheduler.db')
        cursor = conn.cursor()
        
        for shift_date in shift_dates:
            # Check if a shift already exists for the member on the given date
            cursor.execute('SELECT COUNT(*) FROM Shifts WHERE member_id = ? AND shift_date = ?',
                           (member_id, shift_date))
            exists = cursor.fetchone()[0]

            if exists:  # If a shift exists, update it
                cursor.execute('UPDATE Shifts SET shift_type = ? WHERE member_id = ? AND shift_date = ?',
                               (shift_type, member_id, shift_date))
            else:  # If no shift exists, insert a new one
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
    SELECT Shifts.id, TeamMembers.name, Shifts.shift_date, Shifts.shift_type, TeamMembers.role
    FROM Shifts 
    JOIN TeamMembers ON Shifts.member_id = TeamMembers.id
    ''')
    
    shifts = cursor.fetchall()

    # Fetch distinct roles for the dropdown
    cursor.execute('SELECT DISTINCT role FROM TeamMembers')
    roles = cursor.fetchall()
    conn.close()
    
    return render_template('view_shifts.html', shifts=shifts, roles=roles)

@app.route('/delete_member/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TeamMembers WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_team_members'))  # Update this line


@app.route('/manage_team_members', methods=['GET', 'POST'])
def manage_team_members():
    conn = sqlite3.connect('shift_scheduler.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Handle adding a new team member
        name = request.form['name']
        role = request.form['role']
        cursor.execute('INSERT INTO TeamMembers (name, role) VALUES (?, ?)', (name, role))
        conn.commit()

    # Fetch all team members to display
    cursor.execute('SELECT id, name, role FROM TeamMembers')
    team_members = cursor.fetchall()
    conn.close()
    
    return render_template('team_members.html', team_members=team_members)

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
