from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, timedelta
import time

app = Flask(__name__, template_folder='html', static_folder='static')

def get_db_connection():
    conn = sqlite3.connect('shift_scheduler.db')
    conn.row_factory = sqlite3.Row  
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS TeamMembers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS Shifts (id INTEGER PRIMARY KEY, member_id INTEGER, shift_date DATE, shift_type TEXT, FOREIGN KEY (member_id) REFERENCES TeamMembers(id))')
    conn.commit()
    conn.close()

init_db()

# hashmap for hosts that access the webpage 
hostlist = {}
#used for DDOS prevention - collects the IP of each connection and puts it into a hash. If the max amount of entries is more than X, it would return true, else false
def ddos_prevention(source):
    thetime = time.time()
    if source not in hostlist:
        hostlist[source] = []
    hostlist[source] = [current_time for current_time in hostlist[source] if thetime - current_time < 60 ]
    if len(hostlist[source]) >= 20:
        return True
    hostlist[source].append(thetime)
    return False


@app.route('/schedule_and_view_shifts', methods=['GET', 'POST'])
def schedule_and_view_shifts():
    conn_ip = request.remote_addr
    if ddos_prevention(conn_ip):
        return 'Connection limit exceeded, wait a minute and come back',400
    if request.method == 'POST':
        member_id = request.form['member_id']
        if 'shift_dates' not in request.form:
            return "Error: No date range selected.", 400

        start_date, end_date = [datetime.strptime(date.strip(), "%Y-%m-%d") for date in request.form['shift_dates'].split(" to ")]
        shift_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_date - start_date).days + 1) if (start_date + timedelta(days=i)).weekday() < 5]
        shift_type = request.form['shift_type']

        conn = get_db_connection()
        cursor = conn.cursor()

        for shift_date in shift_dates:
            cursor.execute('SELECT COUNT(*) FROM Shifts WHERE member_id = ? AND shift_date = ?', (member_id, shift_date))
            exists = cursor.fetchone()[0]
            if exists:
                cursor.execute('UPDATE Shifts SET shift_type = ? WHERE member_id = ? AND shift_date = ?', (shift_type, member_id, shift_date))
            else:
                cursor.execute('INSERT INTO Shifts (member_id, shift_date, shift_type) VALUES (?, ?, ?)', (member_id, shift_date, shift_type))

        conn.commit()
        conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT Shifts.id, TeamMembers.name, Shifts.shift_date, Shifts.shift_type, TeamMembers.role FROM Shifts JOIN TeamMembers ON Shifts.member_id = TeamMembers.id')
    shifts = cursor.fetchall()

    cursor.execute('SELECT id, name FROM TeamMembers')
    team_members = cursor.fetchall()

    cursor.execute('SELECT DISTINCT role FROM TeamMembers')
    roles = cursor.fetchall()
    
    conn.close()
    return render_template('schedule_and_view_shifts.html', shifts=shifts, team_members=team_members, roles=roles)

@app.route('/')
def init_page():
    return redirect(url_for('schedule_and_view_shifts'))

@app.route('/delete_member/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Shifts WHERE member_id = ?", (member_id,))

    cursor.execute("DELETE FROM TeamMembers WHERE id = ?", (member_id,))
    
    conn.commit()
    conn.close()
    return redirect(url_for('manage_team_members'))

@app.route('/manage_team_members', methods=['GET', 'POST'])
def manage_team_members():
    conn_ip = request.remote_addr
    if ddos_prevention(conn_ip):
        return 'Connection limit exceeded, wait a minute and come back',400
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.args.get('data') == 'events':
        cursor.execute("SELECT S.shift_date, S.shift_type, S.member_id, T.name FROM Shifts S JOIN TeamMembers T ON S.member_id = T.id")
        shifts = cursor.fetchall()
        events = [{'title': shift[1], 'start': shift[0], 'resourceId': str(shift[2]), 'memberName': shift[3], 'shiftType': shift[1]} for shift in shifts]
        conn.close()
        return jsonify(events)
    
    elif request.args.get('data') == 'members':
        cursor.execute("SELECT id, name FROM TeamMembers")
        members = cursor.fetchall()
        resources = [{'id': str(member[0]), 'title': member[1]} for member in members]
        conn.close()
        return jsonify(resources)

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        cursor.execute('SELECT COUNT(*) FROM TeamMembers WHERE name = ?', (name,))
        exists = cursor.fetchone()[0]
        if exists:
            conn.close()
            return "Can't do: Team member already exists.", 400
        else:
            cursor.execute('INSERT INTO TeamMembers (name, role) VALUES (?, ?)', (name, role))
            conn.commit()

    cursor.execute('SELECT id, name, role FROM TeamMembers')
    team_members = cursor.fetchall()
    conn.close()
    return render_template('team_members.html', team_members=team_members)



if __name__ == '__main__':
    app.run(debug=True)
