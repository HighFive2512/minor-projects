from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify
import os
from datetime import datetime, timedelta
import csv
from collections import defaultdict
import uuid
import io

app = Flask(__name__)
app.secret_key = os.urandom(24)
os.chdir(r'C:\Users\Ancho\Desktop\New folder')
# Data storage (in-memory for simplicity, could be replaced with a database)
team_members = []
holidays = defaultdict(list)  # date -> list of members on holiday
rota_assignments = {}  # date+timeframe -> member

# Time frames
TIMEFRAMES = {
    "Weekday Night": "20:00 to 08:00",
    "Saturday Morning": "00:00 to 12:00",
    "Saturday Afternoon": "12:00 to 24:00"
}

def is_weekend(date):
    return date.weekday() >= 5  # 5 is Saturday, 6 is Sunday

def get_next_workdays(start_date, days=30):
    """Get the next N workdays excluding Sundays."""
    workdays = []
    current_date = start_date
    
    while len(workdays) < days:
        if current_date.weekday() != 6:  # Not a Sunday
            workdays.append(current_date)
        current_date += timedelta(days=1)
    
    return workdays

def get_timeframes_for_date(date):
    """Return appropriate timeframes for the given date."""
    if date.weekday() == 5:  # Saturday
        return ["Saturday Morning", "Saturday Afternoon"]
    elif date.weekday() != 6:  # Not Sunday
        return ["Weekday Night"]
    return []

def generate_rota(start_date, days=30):
    """Generate a rota for the specified number of days."""
    workdays = get_next_workdays(start_date, days)
    rota = {}
    
    # Track assignments to ensure fair distribution
    assignment_count = {member: 0 for member in team_members}
    
    for date in workdays:
        date_str = date.strftime("%Y-%m-%d")
        timeframes = get_timeframes_for_date(date)
        
        for timeframe in timeframes:
            key = f"{date_str}_{timeframe}"
            
            # Get available members (excluding those on holiday)
            available_members = [m for m in team_members if m not in holidays[date_str]]
            
            if not available_members:
                rota[key] = "NO COVERAGE"
                continue
            
            # Sort by number of assignments to prioritize those with fewer
            available_members.sort(key=lambda m: assignment_count[m])
            
            # Assign the member with the fewest assignments
            assigned_member = available_members[0]
            rota[key] = assigned_member
            assignment_count[assigned_member] += 1
    
    return rota

def generate_ics_for_member(member_name, rota, start_date, days):
    """Generate ICS calendar file content for a specific team member"""
    workdays = get_next_workdays(start_date, days)
    
    # ICS file header
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//On-Call Rota Manager//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    
    # Add events for each assignment
    for date in workdays:
        date_str = date.strftime("%Y-%m-%d")
        timeframes = get_timeframes_for_date(date)
        
        for timeframe in timeframes:
            key = f"{date_str}_{timeframe}"
            
            # Only include shifts assigned to this member
            if key in rota and rota[key] == member_name:
                event_uuid = str(uuid.uuid4())
                
                # Parse timeframe hours
                time_range = TIMEFRAMES[timeframe]
                start_hour, end_hour = time_range.split(" to ")
                start_hour = start_hour.split(":")[0].zfill(2)
                end_hour = end_hour.split(":")[0].zfill(2)
                
                # Create start and end datetimes
                if timeframe == "Weekday Night":
                    # Night shifts start on the current day and end on the next day
                    start_dt = f"{date_str}T{start_hour}0000"
                    end_date = date + timedelta(days=1)
                    end_dt = f"{end_date.strftime('%Y-%m-%d')}T{end_hour}0000"
                else:
                    # Same day shifts
                    start_dt = f"{date_str}T{start_hour}0000"
                    end_dt = f"{date_str}T{end_hour}0000"
                
                # Add event to calendar
                ics_content.extend([
                    "BEGIN:VEVENT",
                    f"UID:{event_uuid}",
                    f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTSTART:{start_dt}",
                    f"DTEND:{end_dt}",
                    f"SUMMARY:On-Call Duty - {timeframe}",
                    f"DESCRIPTION:You are on-call for the {timeframe} shift ({time_range})",
                    "STATUS:CONFIRMED",
                    "SEQUENCE:0",
                    "BEGIN:VALARM",
                    "TRIGGER:-PT1H",
                    "ACTION:DISPLAY",
                    "DESCRIPTION:On-call shift reminder",
                    "END:VALARM",
                    "END:VEVENT",
                ])
    
    # Close calendar
    ics_content.append("END:VCALENDAR")
    
    # Join all lines with CRLF as per ICS spec
    return "\r\n".join(ics_content)

@app.route('/', methods=['GET', 'POST'])
def index():
    active_tab = request.args.get('tab', 'setup')
    global team_members
    
    # Process form submissions based on the action parameter
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'setup_team':
            members_input = request.form.get('team_members', '')
            team_members = [member.strip() for member in members_input.split(',') if member.strip()]
            flash('Team members updated successfully!', 'success')
            active_tab = 'setup'
            
        elif action == 'add_holiday':
            date = request.form.get('holiday_date')
            members = request.form.getlist('holiday_members')
            
            for member in members:
                if member not in holidays[date]:
                    holidays[date].append(member)
            
            flash('Holiday recorded successfully!', 'success')
            active_tab = 'holidays'
            
        elif action == 'clear_holidays':
            holidays.clear()
            flash('All holidays have been cleared.', 'success')
            active_tab = 'holidays'
            
        elif action == 'generate_rota':
            start_date_str = request.form.get('start_date')
            days = int(request.form.get('days', 30))
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            rota = generate_rota(start_date, days)
            
            # Store in session for download
            session['current_rota'] = rota
            session['rota_start_date'] = start_date_str
            session['rota_days'] = days
            
            flash('Rota generated successfully!', 'success')
            active_tab = 'rota'
    
    # Generate current rota view if available
    current_rota = None
    workdays = []
    current_month = None
    next_month = None
    
    if 'current_rota' in session:
        current_rota = session['current_rota']
        start_date = datetime.strptime(session['rota_start_date'], '%Y-%m-%d')
        days = session['rota_days']
        workdays = get_next_workdays(start_date, days)
        
        # Get current and next month for filtering
        current_month = start_date.strftime('%Y-%m')
        next_month_date = datetime(start_date.year + (start_date.month // 12), 
                                  ((start_date.month % 12) + 1) or 12, 
                                  1)
        next_month = next_month_date.strftime('%Y-%m')
    
    # Default start date is today
    default_start = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('index.html', 
                           active_tab=active_tab,
                           team_members=team_members,
                           holidays=holidays,
                           default_start=default_start,
                           current_rota=current_rota,
                           workdays=workdays,
                           timeframes=TIMEFRAMES,
                           current_month=current_month,
                           next_month=next_month,
                           get_timeframes_for_date=get_timeframes_for_date)

@app.route('/download_rota')
def download_rota():
    if 'current_rota' not in session:
        flash('No rota to download. Please generate a rota first.', 'error')
        return redirect(url_for('index', tab='rota'))
    
    rota = session['current_rota']
    start_date = datetime.strptime(session['rota_start_date'], '%Y-%m-%d')
    days = session['rota_days']
    
    workdays = get_next_workdays(start_date, days)
    
    # Create CSV content
    output = []
    headers = ['Date', 'Day', 'Timeframe', 'On-Call Member', 'Members on Holiday']
    output.append(headers)
    
    for date in workdays:
        date_str = date.strftime("%Y-%m-%d")
        day_name = date.strftime("%A")
        timeframes = get_timeframes_for_date(date)
        
        for timeframe in timeframes:
            key = f"{date_str}_{timeframe}"
            on_holiday = ", ".join(holidays[date_str]) if date_str in holidays else ""
            
            row = [
                date_str,
                day_name,
                f"{timeframe} ({TIMEFRAMES[timeframe]})",
                rota.get(key, "UNASSIGNED"),
                on_holiday
            ]
            output.append(row)
    
    # Return as downloadable CSV
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerows(output)
    
    output = si.getvalue()
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=oncall_rota.csv"}
    )

@app.route('/download_ics/<member_name>')
def download_ics(member_name):
    if 'current_rota' not in session:
        flash('No rota to download. Please generate a rota first.', 'error')
        return redirect(url_for('index', tab='rota'))
    
    rota = session['current_rota']
    start_date = datetime.strptime(session['rota_start_date'], '%Y-%m-%d')
    days = session['rota_days']
    
    ics_content = generate_ics_for_member(member_name, rota, start_date, days)
    
    return Response(
        ics_content,
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment;filename={member_name.replace(' ', '_')}_oncall.ics"}
    )

# Create HTML template
if not os.path.exists('templates'):
    os.makedirs('templates')

# Create index template (single page application)
with open('templates/index.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>On-Call Rota Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css">
    <style>
        body { padding-top: 20px; padding-bottom: 20px; }
        .header { padding-bottom: 20px; margin-bottom: 30px; border-bottom: 1px solid #e5e5e5; }
        .footer { padding-top: 19px; color: #777; border-top: 1px solid #e5e5e5; margin-top: 30px; }
        .container { max-width: 1200px; }
        .nav-tabs { margin-bottom: 20px; }
        .calendar-filter { margin-bottom: 15px; }
        .badge { font-size: 90%; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="text-center">On-Call Rota Manager</h1>
            <p class="lead text-center">
                Manage your team's on-call rotations with ease
            </p>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <ul class="nav nav-tabs" id="mainTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link {{ 'active' if active_tab == 'setup' else '' }}" 
                        id="setup-tab" data-bs-toggle="tab" data-bs-target="#setup" 
                        type="button" role="tab" aria-selected="{{ 'true' if active_tab == 'setup' else 'false' }}">
                    Team Setup
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link {{ 'active' if active_tab == 'holidays' else '' }}" 
                        id="holidays-tab" data-bs-toggle="tab" data-bs-target="#holidays" 
                        type="button" role="tab" aria-selected="{{ 'true' if active_tab == 'holidays' else 'false' }}">
                    Holidays
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link {{ 'active' if active_tab == 'rota' else '' }}" 
                        id="rota-tab" data-bs-toggle="tab" data-bs-target="#rota" 
                        type="button" role="tab" aria-selected="{{ 'true' if active_tab == 'rota' else 'false' }}">
                    Generate Rota
                </button>
            </li>
        </ul>
        
        <div class="tab-content" id="mainTabsContent">
            <!-- Team Setup Tab -->
            <div class="tab-pane fade {{ 'show active' if active_tab == 'setup' else '' }}" id="setup" role="tabpanel">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h3 class="card-title mb-0">Set Up Your Team</h3>
                    </div>
                    <div class="card-body">
                        <form method="POST">
                            <input type="hidden" name="action" value="setup_team">
                            <div class="mb-3">
                                <label for="team_members" class="form-label">Team Members (comma-separated)</label>
                                <textarea class="form-control" id="team_members" name="team_members" rows="3" 
                                          placeholder="John, Jane, Alex, Sarah">{{ ', '.join(team_members) }}</textarea>
                            </div>
                            <button type="submit" class="btn btn-primary">Save Team</button>
                        </form>
                        
                        {% if team_members %}
                        <div class="mt-4">
                            <h4>Current Team</h4>
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
                                        <tr>
                                            <th>Name</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for member in team_members %}
                                        <tr>
                                            <td>{{ member }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            
            <!-- Holidays Tab -->
            <div class="tab-pane fade {{ 'show active' if active_tab == 'holidays' else '' }}" id="holidays" role="tabpanel">
                <div class="row">
                    <div class="col-md-5">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h3 class="card-title mb-0">Add Holiday</h3>
                            </div>
                            <div class="card-body">
                                {% if not team_members %}
                                <div class="alert alert-warning">
                                    Please set up your team members first in the Team Setup tab.
                                </div>
                                {% else %}
                                <form method="POST">
                                    <input type="hidden" name="action" value="add_holiday">
                                    <div class="mb-3">
                                        <label for="holiday_date" class="form-label">Date</label>
                                        <input type="date" class="form-control" id="holiday_date" name="holiday_date" required>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label class="form-label">Members on Holiday</label>
                                        {% for member in team_members %}
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" name="holiday_members" 
                                                   value="{{ member }}" id="holiday_member{{ loop.index }}">
                                            <label class="form-check-label" for="holiday_member{{ loop.index }}">
                                                {{ member }}
                                            </label>
                                        </div>
                                        {% endfor %}
                                    </div>
                                    
                                    <button type="submit" class="btn btn-primary">Add Holiday</button>
                                </form>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-7">
                        <div class="card">
                            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                                <h3 class="card-title mb-0">Team Member Holidays</h3>
                                <form method="POST" class="d-inline">
                                    <input type="hidden" name="action" value="clear_holidays">
                                    <button type="submit" class="btn btn-danger btn-sm" 
                                            onclick="return confirm('Are you sure you want to clear all holidays?')">
                                        Clear All
                                    </button>
                                </form>
                            </div>
                            <div class="card-body">
                                {% if not holidays %}
                                <div class="alert alert-info">
                                    No holidays have been recorded yet.
                                </div>
                                {% else %}
                                <div class="table-responsive">
                                    <table class="table table-striped table-bordered">
                                        <thead class="table-dark">
                                            <tr>
                                                <th>Date</th>
                                                <th>Members on Holiday</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for date, members in holidays.items()|sort %}
                                            <tr>
                                                <td>{{ date }}</td>
                                                <td>{{ ', '.join(members) }}</td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Rota Tab -->
            <div class="tab-pane fade {{ 'show active' if active_tab == 'rota' else '' }}" id="rota" role="tabpanel">
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h3 class="card-title mb-0">Generate Rota</h3>
                            </div>
                            <div class="card-body">
                                {% if not team_members %}
                                <div class="alert alert-warning">
                                    Please set up your team members first in the Team Setup tab.
                                </div>
                                {% else %}
                                <form method="POST">
                                    <input type="hidden" name="action" value="generate_rota">
                                    <div class="mb-3">
                                        <label for="start_date" class="form-label">Start Date</label>
                                        <input type="date" class="form-control" id="start_date" name="start_date" 
                                               value="{{ default_start }}" required>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label for="days" class="form-label">Number of Days</label>
                                        <input type="number" class="form-control" id="days" name="days" 
                                               value="60" min="1" max="90" required>
                                        <div class="form-text">
                                            Recommended: 60 days to show current and next month
                                        </div>
                                    </div>
                                    
                                    <button type="submit" class="btn btn-primary">Generate Rota</button>
                                </form>
                                {% endif %}
                                
                                {% if current_rota %}
                                <div class="mt-4">
                                    <a href="{{ url_for('download_rota') }}" class="btn btn-success w-100">
                                        <i class="bi bi-download"></i> Download Full Rota (CSV)
                                    </a>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-8">
                        {% if current_rota %}
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h3 class="card-title mb-0">On-Call Rota</h3>
                            </div>
                            <div class="card-body">
                                <div class="calendar-filter d-flex justify-content-between align-items-center">
                                    <div>
                                        <span class="fw-bold">Display:</span>
                                        <div class="btn-group" role="group">
                                            <button type="button" class="btn btn-outline-primary active" id="showAll">All</button>
                                            <button type="button" class="btn btn-outline-primary" id="showCurrentMonth">Current Month</button>
                                            <button type="button" class="btn btn-outline-primary" id="showNextMonth">Next Month</button>
                                        </div>
                                    </div>
                                    
                                    <div class="dropdown">
                                        <button class="btn btn-outline-primary dropdown-toggle" type="button" id="downloadCalendarBtn" 
                                                data-bs-toggle="dropdown" aria-expanded="false">
                                            Download Calendar (ICS)
                                        </button>
                                        <ul class="dropdown-menu" aria-labelledby="downloadCalendarBtn">
                                            {% for member in team_members %}
                                            <li>
                                                <a class="dropdown-item" href="{{ url_for('download_ics', member_name=member) }}">
                                                    {{ member }}
                                                </a>
                                            </li>
                                            {% endfor %}
                                        </ul>
                                    </div>
                                </div>
                                
                                <div class="table-responsive">
                                    <table class="table table-striped table-bordered">
                                        <thead class="table-dark">
                                            <tr>
                                                <th>Date</th>
                                                <th>Day</th>
                                                <th>Timeframe</th>
                                                <th>On-Call Member</th>
                                                <th>Members on Holiday</th>
                                                <th>Calendar</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for day in workdays %}
                                                {% set date_str = day.strftime('%Y-%m-%d') %}
                                                {% set day_name = day.strftime('%A') %}
                                                {% set month_str = day.strftime('%Y-%m') %}
                                                
                                                {% set timeframes = get_timeframes_for_date(day) %}
                                                
                                                {% for timeframe in timeframes %}
                                                    {% set key = date_str + '_' + timeframe %}
                                                    <tr class="rota-row" data-month="{{ month_str }}">
                                                        <td>{{ date_str }}</td>
                                                        <td>{{ day_name }}</td>
                                                        <td>{{ timeframe }} ({{ timeframes[timeframe] }})</td>
                                                        <td>
                                                            {% if key in current_rota %}
                                                                <span class="badge {{ 'bg-danger' if current_rota[key] == 'NO COVERAGE' else 'bg-primary' }} p-2">
                                                                    {{ current_rota[key] }}
                                                                </span>
                                                            {% else %}
                                                                <span class="badge bg-secondary p-2">UNASSIGNED</span>
                                                            {% endif %}
                                                        </td>
                                                        <td>
                                                            {% if date_str in holidays %}
                                                                {{ ', '.join(holidays[date_str]) }}
                                                            {% else %}
                                                                -
                                                            {% endif %}
                                                        </td>
                                                        <td>
                                                            {% if key in current_rota and current_rota[key] != 'NO COVERAGE' %}
                                                                <a href="{{ url_for('download_ics', member_name=current_rota[key]) }}" 
                                                                   class="btn btn-sm btn-outline-primary">
                                                                    Calendar
                                                                </a>
                                                            {% else %}
                                                                -
                                                            {% endif %}
                                                        </td>
                                                    </tr>
                                                {% endfor %}
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                        {% else %}
                        <div class="alert alert-info">
                            No rota has been generated yet. Use the form to create a new rota.
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        <footer class="footer">
            <p class="text-center">&copy; {{ current_year }} On-Call Rota Manager</p>
        </footer>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script>
        // Initialize tabs based on active tab
        document.addEventListener('DOMContentLoaded', function() {
            // Tab switching
            const triggerTabList = [].slice.call(document.querySelectorAll('#mainTabs button'));
            triggerTabList.forEach(function(triggerEl) {
                triggerEl.addEventListener('click', function(event) {
                    event.preventDefault();
                    // Update URL with tab parameter
                    const tabId = this.getAttribute('id').replace('-tab', '');
                    const url = new URL(window.location.href);
                    url.searchParams.set('tab', tabId);
                    window.history.pushState({}, '', url);
                });
            });
            
            // Month filtering for rota
            const showAll = document.getElementById('showAll');
            const showCurrentMonth = document.getElementById('showCurrentMonth');
            const showNextMonth = document.getElementById('showNextMonth');
            const rotaRows = document.querySelectorAll('.rota-row');
            
            if (showAll && showCurrentMonth && showNextMonth) {
                showAll.addEventListener('click', function() {
                    updateFilter('all');
                });
                
                showCurrentMonth.addEventListener('click', function() {
                    updateFilter('{{ current_month }}');
                });
                
                showNextMonth.addEventListener('click', function() {
                    updateFilter('{{ next_month }}');
                });
                
                function updateFilter(filter) {
                    // Update button active states
                    showAll.classList.remove('active');
                    showCurrentMonth.classList.remove('active');
                    showNextMonth.classList.remove('active');
                    
                    if (filter === 'all') {
                        showAll.classList.add('active');
                    } else if (filter === '{{ current_month }}') {
                        showCurrentMonth.classList.add('active');
                    } else {
                        showNextMonth.classList.add('active');
                    }
                    
                    // Filter rows
                    rotaRows.forEach(function(row) {
                        if (filter === 'all' || row.getAttribute('data-month') === filter) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                }
            }
        });
    </script>
</body>
</html>
'''.replace('{{ current_year }}', str(datetime.now().year)))

if __name__ == '__main__':
    app.run(debug=True)