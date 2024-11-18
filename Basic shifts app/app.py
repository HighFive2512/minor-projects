from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, timedelta
import time

app = Flask(__name__, template_folder='html', static_folder='static')


# database connection
def get_db_connection():
    conn = sqlite3.connect('shift_scheduler.db')
    conn.row_factory = sqlite3.Row
    return conn


# initializes/creates databases if they dont exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS TeamMembers (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, role TEXT, application TEXT)')
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS Shifts (id INTEGER PRIMARY KEY, member_id INTEGER, shift_date DATE, shift_type TEXT, FOREIGN KEY (member_id) REFERENCES TeamMembers(id))')
    conn.commit()
    conn.close()


init_db()


@app.route('/schedule_and_view_shifts', methods=['GET', 'POST'])
def schedule_and_view_shifts():
    selected_role = request.args.get('role', '')
    selected_application = request.args.get('application', '')

    if request.method == 'POST':
        member_id = request.form['member_id']
        if 'shift_dates' not in request.form:
            return "Error: No date range selected.", 400
        selected_date = [datetime.strptime(date.strip(), "%Y-%m-%d") for date in
                         request.form['shift_dates'].split(" to ")]
        if len(selected_date) > 1:
            start_date, end_date = selected_date
        else:
            start_date = end_date = selected_date

        shift_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in
                       range((end_date - start_date).days + 1) if (start_date + timedelta(days=i)).weekday() < 5]
        shift_type = request.form['shift_type']

        conn = get_db_connection()
        cursor = conn.cursor()

        for shift_date in shift_dates:
            cursor.execute('SELECT COUNT(*) FROM Shifts WHERE member_id = ? AND shift_date = ?',
                           (member_id, shift_date))
            exists = cursor.fetchone()[0]
            if exists:
                cursor.execute('UPDATE Shifts SET shift_type = ? WHERE member_id = ? AND shift_date = ?',
                               (shift_type, member_id, shift_date))
            else:
                cursor.execute('INSERT INTO Shifts (member_id, shift_date, shift_type) VALUES (?, ?, ?)',
                               (member_id, shift_date, shift_type))

        conn.commit()
        conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
       SELECT Shifts.id, TeamMembers.name, Shifts.shift_date, Shifts.shift_type, 
              TeamMembers.role, TeamMembers.application 
       FROM Shifts 
       JOIN TeamMembers ON Shifts.member_id = TeamMembers.id 
       '''

    if selected_role:
        query += ' WHERE TeamMembers.role = ?'
        params = [selected_role]
    elif selected_application:
        query += ' WHERE TeamMembers.application = ?'
        params = [selected_application]
    else:
        params = []

    cursor.execute(query, params)
    shifts = cursor.fetchall()
    cursor.execute('SELECT id, name, role, application FROM TeamMembers')
    team_members = cursor.fetchall()

    cursor.execute('SELECT DISTINCT role FROM TeamMembers')
    roles = cursor.fetchall()

    cursor.execute('SELECT DISTINCT application FROM TeamMembers')
    applications = cursor.fetchall()

    query = '''
    SELECT Shifts.id, TeamMembers.name, Shifts.shift_date, Shifts.shift_type, 
           TeamMembers.role, TeamMembers.application 
    FROM Shifts 
    JOIN TeamMembers ON Shifts.member_id = TeamMembers.id 
    '''

    if selected_role:
        query += ' WHERE TeamMembers.role = ?'
        params = [selected_role]
    elif selected_application:
        query += ' WHERE TeamMembers.application = ?'
        params = [selected_application]
    else:
        params = []

    cursor.execute(query, params)
    shifts = cursor.fetchall()

    return render_template('schedule_and_view_shifts.html',
                           shifts=shifts,
                           team_members=team_members,
                           roles=roles,
                           applications=applications,
                           selected_role=selected_role,
                           selected_application=selected_application)
@app.route('/')
def init_page():
    return redirect(url_for('schedule_and_view_shifts'))


@app.route('/delete_member/<int:member_id>', methods=['POST'])
# deletes team member data and the corresponding scheduled shifts
def delete_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Shifts WHERE member_id = ?", (member_id,))
    cursor.execute("DELETE FROM TeamMembers WHERE id = ?", (member_id,))

    conn.commit()
    conn.close()
    return redirect(url_for('schedule_and_view_shifts'))


@app.route('/manage_team_members', methods=['GET', 'POST'])
def manage_team_members():
    conn = get_db_connection()
    cursor = conn.cursor()


    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        application = request.form.get('application', '')
        cursor.execute('SELECT COUNT(*) FROM TeamMembers WHERE name = ?', (name,))
        exists = cursor.fetchone()[0]
        if exists:
            conn.close()
            return "Can't do: Team member already exists.", 400
        else:
            cursor.execute('INSERT INTO TeamMembers (name, role, application) VALUES (?, ?, ?)',
                           (name, role, application))
            conn.commit()

    # Omdify the schedule_and_view_shifts route to pass applications
    cursor.execute('SELECT DISTINCT application FROM TeamMembers')
    applications = cursor.fetchall()

    cursor.execute('SELECT id, name, role, application FROM TeamMembers')
    team_members = cursor.fetchall()
    conn.close()
    return render_template('schedule_and_view_shifts.html',
                           team_members=team_members,
                           applications=applications)


if __name__ == '__main__':
    app.run(debug=True)