from flask import Blueprint, Flask, render_template, url_for
import re
import datetime
import os
import glob

# Create the blueprint
dashapp = Blueprint('dash', __name__, template_folder='templates', static_folder='static')

# Get the application name and set current directory
appname = os.path.basename(__file__)

current_path = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_path, 'data')
application_file = os.path.join(data_dir, 'applications.txt')

# Ensure data directory exists
if not os.path.exists(data_dir):
    print(f"WARNING: Data directory does not exist: {data_dir}")
    os.makedirs(data_dir)


# Define file paths
data_dir = os.path.join(current_path, 'data')
application_file = os.path.join(current_path, 'data', 'applications.txt')

def parse_applications(file_path):
    """
    Parse applications from a file
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        applications = file.read().splitlines()
    return applications

def parse_table_file(file_path):
    """
    Parse a single table file into a table format
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read().split('\n')
        
    # Remove empty lines and lines that are just separators
    content = [line for line in content if line.strip() and not set(line.strip()) <= {'-', '='}]
    
    # Find the header line (first line that contains '|')
    header_index = next((i for i, line in enumerate(content) if '|' in line), None)
    
    if header_index is None:
        raise ValueError(f"No valid header found in {file_path}")
    
    # Split the header line by '|'
    headers = [h.strip() for h in content[header_index].split('|')]
    
    # Process data rows
    data_rows = [
        [col.strip() for col in line.split('|')]
        for line in content[header_index+1:] if '|' in line
    ]
    
    # Combine headers and data rows into a single table
    table = [headers] + data_rows
    
    return table

def get_tables_for_applications():
    """
    Find and parse table files for each application
    """
    # Get list of applications (convert to lowercase for case-insensitive matching)
    applications = parse_applications(application_file)
    print("Applications from file:", applications)
    
    # Print the current working directory and data directory
    print("Current working directory:", os.getcwd())
    print("Data directory:", data_dir)
    
    # Find all table files in the data directory
    table_files = glob.glob(os.path.join(data_dir, '*.txt'))
    print("All table files found:", table_files)
    
    # Dictionary to store tables for each application
    application_tables = {}
    
    for file_path in table_files:
        # Skip the applications.txt file
        if os.path.basename(file_path) == 'applications.txt':
            continue
        
        # Extract filename without extension
        filename = os.path.splitext(os.path.basename(file_path))[0]

        # Check if the filename matches any application
        matching_apps = [app for app in applications if app.lower() in filename.lower()]
        
        if matching_apps:
            application = matching_apps[0]
            

            # Attempt to parse the table file
            table = parse_table_file(file_path)

            # Add to application tables
            if application not in application_tables:
                application_tables[application] = []
            
            # Add query name as the first element of the table
            query_name = filename
            table_with_query_name = [[query_name] + table[0]] + table[1:]
            application_tables[application].append(table_with_query_name)

    return application_tables

def get_modified_time():
    """
    Get current time adjusted by 2 hours
    """
    current_time = datetime.datetime.now()
    modified_time = current_time - datetime.timedelta(hours=2)
    return modified_time.strftime("%Y-%m-%d %H:%M:%S")

def split_header(value):
    """
    Extract header from a list or string
    """
    if isinstance(value, list):
        joined_value = " ".join(value)
    else:
        joined_value = str(value)
    
    check_for_quotes = re.findall(r'"([^"]+)"', joined_value)
    return check_for_quotes[0] if check_for_quotes else joined_value

def splitpart(value):
    """
    Split a value by '|'
    """
    if isinstance(value, list):
        value = " ".join(value)
    return str(value).split('|')

@dashapp.route('/All_tables')
def all_tables_page():
    """
    Route for all tables page
    """
    # Get applications and their tables
    tables = get_tables_for_applications()
    print("Tables in route:", tables)
    
    # Get list of applications 
    applications = parse_applications(application_file)
    # Get modified time
    modified_time = get_modified_time()
    
    return render_template('all_tables.html', 
                           tables=tables, 
                           modified_time=modified_time,
                           applications=applications)

# Register template filters
dashapp.add_app_template_filter(split_header,'split_header')
dashapp.add_app_template_filter(splitpart,'splitpart')