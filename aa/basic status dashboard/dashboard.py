from flask import Flask, render_template
import datetime
import os
import json

script_path = os.path.dirname(__file__)
os.chdir(script_path)

def get_file_data(filename, file_type):
    filepath = os.path.join('source', filename)
    title = os.path.splitext(os.path.basename(filename))[0]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read().strip()
    except FileNotFoundError:
        return [f"{filename} not found", [], []]
    
    if not content:
        return [title, [], []]

    parsing_methods = {
        'table': _parse_table,
        'error_table_or_status_box': _parse_error_table,
        'log': _parse_log,
        'batch': _parse_batch,
        'status_box': _parse_status_box
    }
    
    parse_func = parsing_methods.get(file_type, lambda c, t: [title, [], []])
    return parse_func(content, title)

def _parse_status_box(content, title):
    try:
        # Try parsing as JSON first
        status_data = json.loads(content)
        
        # Check if it's a status box with 'status' key
        if isinstance(status_data, dict) and 'status' in status_data:
            status = status_data.get('status', 'unknown').lower()
            
            # Modify title based on status
            if status == 'healthy':
                return [f"{title} - Status (Healthy)", [], []]
            else:
                return [f"{title} - Status (Unhealthy)", [], []]
        
    except json.JSONDecodeError:
        # Fallback to original parsing if not valid JSON
        return [f"{title} - Status", ["Metric", "Value"], 
                [[key, str(value)] for key, value in status_data.items()]]
def _parse_table(content, title):
    lines = content.split('\n')
    read_data = [line.split('|') for line in lines if line.strip()]

    return [title, read_data[0] if read_data else [], read_data[1:] if len(read_data) > 1 else []]

def _parse_error_table(content, title):
    lines = content.split('\n')
    read_data = [line.split('|') for line in lines if line.strip()]
    
    return [title, [] if len(read_data) <= 1 else read_data[0], read_data[1:] if len(read_data) > 1 else []]

def _parse_log(content, title):
    lines = content.split('\n')
    log_rows = [[line.strip()] for line in lines if line.strip()]
    
    return [f"{title} - Log", [], log_rows]

def _parse_batch(content, title):
    lines = content.split('\n')
    rows = []
    for line in lines:
        if line.strip():
            parts = line.split('|')
            parts.extend([''] * (3 - len(parts)))
            rows.append(parts[:3])
    
    return [f"{title} - Batch", ["Batch ID", "Status", "Count"], rows]

def get_applications_from_files(file_dict):
    return sorted(set(filename.split('_')[0] for filename in file_dict.keys()))

def get_tables_for_application(application, file_dict):
    return [
        get_file_data(filename, file_type)
        for filename, file_type in file_dict.items()
        if filename.startswith(f"{application}_")
    ]

def get_modified_time():
    return (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

def create_app(file_dict=None):
    app = Flask(__name__)
    app.config['FILE_DICT'] = file_dict or {}

    @app.route('/dashboard')
    def dashboard():
        current_file_dict = app.config.get('FILE_DICT', {})
        applications = get_applications_from_files(current_file_dict)
        all_tables = [
            table for app_name in applications 
            for table in get_tables_for_application(app_name, current_file_dict)
        ]
        
        return render_template('All_tables.html', 
                               tables=all_tables, 
                               modified_time=get_modified_time(), 
                               applications=applications)

    @app.route('/All_tables')
    def all_tables():
        return dashboard()
    
    @app.route('/')
    def welcome_page():
        return dashboard()
    
    return app

if __name__ == '__main__':
    example_file_dict = {
        'Application1_DailyStats.txt': 'table',
        'Application1_ErrorLog.txt': 'log',
        'Application2_BatchProcess.txt': 'batch',
        'Application2_SystemStatus.txt': 'status_box',
        'Application3_Performance.txt': 'table',
        'Application1_Test.txt': 'table'
    }
    flask_app = create_app(example_file_dict)
    flask_app.run(debug=True)