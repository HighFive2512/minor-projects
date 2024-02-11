from flask import Flask, render_template
import re
import datetime  # Import datetime module for getting the current time

app = Flask(__name__)

def parse_tables(file_path, keyword):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    tables = []
    keyword = f'{keyword}(.*?)\n\n'
    all_tables = re.findall(keyword, file_content, re.DOTALL)
    for each_table in all_tables:
        each_table = each_table.split('\n')
        del each_table[1]
        del each_table[2]
        current_table = [line.split() for line in each_table if line]
        tables.append(current_table)
    return tables

def parse_applications(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        applications = file.read().splitlines()
    return applications


@app.template_filter('split_header')
def split_header(value):
    value = str(value)
    match = re.search(r'"([^"]+)"', value)
    if match:
        return match.group(1)

@app.template_filter('splitpart')
def splitpart(value):
    value = ' '.join(value)
    return str(value).split('|')

def get_modified_time():
    current_time = datetime.datetime.now()
    modified_time = current_time - datetime.timedelta(hours=2)
    return modified_time.strftime("%Y-%m-%d %H:%M:%S")

@app.route('/dashboard')
def dashboard():
    tables = parse_tables('data/tables.txt', '_Selected_Table_')
    applications = parse_applications('data/applications.txt')
    modified_time = get_modified_time()
    return render_template('dashboard.html', tables=tables, modified_time=modified_time,applications=applications,parse_tables=parse_tables)

@app.route('/All_tables')
def all_tables():
    tables = parse_tables('data/tables.txt', '_Table_')
    applications = parse_applications('data/applications.txt')
    modified_time = get_modified_time()
    return render_template('all_tables.html', tables=tables, modified_time=modified_time,applications=applications)

@app.route('/')
def welcome_page():
    tables = parse_tables('data/tables.txt', '_Selected_Table_')
    applications = parse_applications('data/applications.txt')
    modified_time = get_modified_time()
    return render_template('dashboard.html', tables=tables, modified_time=modified_time,applications=applications)

if __name__ == '__main__':
    app.run(debug=True)