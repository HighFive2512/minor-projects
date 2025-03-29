import os
import datetime

def get_file_data(filename, file_type):
    filepath = os.path.join('source', filename)
    title = os.path.basename(filename)
    title = os.path.splitext(title)[0]
    if not os.path.exists(filepath):
        return [[f"{filename} nto found"], [["no data found"]]]
    
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if file_type == 'table':
        lines = content.strip().split('\n')
        
        read_data = []
        for line in lines:
            if line.strip():
                read_data.append(line.split('|'))
        
        if read_data:
            query_titles = read_data[0]
            rows = read_data[1:] if len(read_data) > 1 else []
            return [title, query_titles, rows]
        else:
            return [title, [], []]
    
    if file_type == 'error_table_or_status_box':
        lines = content.strip().split('\n')
        read_data = []
        for line in lines:
            if line.strip():
                read_data.append(line.split('|'))
        
        if len(read_data) > 1:
            query_titles = read_data[0]
            rows = read_data[1:] if len(read_data) > 1 else []
            return [title, query_titles, rows]
        else:
            return [title, [], []]
        
    elif file_type == 'log':
        lines = content.strip().split('\n')
        title = f"{title} - Log"
        query_titles,rows = [],[]
        for line in lines:
            if line.strip():
                rows.append([line])
        return [title, query_titles, rows]
    
    elif file_type == 'batch':
        lines = content.strip().split('\n')
        title = f"{title} - Batch"

        query_titles = ["Batch ID", "Status", "Count"]

        rows = []
        for line in lines:
            if line.strip():
                parts = line.split('|')
    
                while len(parts) < 3:
                    parts.append("")
                rows.append(parts[:3]) 
        
        return [title, query_titles, rows]
    
    elif file_type == 'status_box':
        lines = content.strip().split('\n')
        title = f"{title} - Status"
        query_titles = ["Metric", "Value"]
        
        rows = []
        for line in lines:
            if line.strip():
                parts = line.split(':', 1) 
                if len(parts) == 2:
                    rows.append([parts[0].strip(), parts[1].strip()])
                else:
                    rows.append([line.strip(), ""])
        
        return [title, query_titles, rows]

def get_applications_from_files(file_dict):
    applications = set()
    for filename in file_dict.keys():
        app_name = filename.split('_')[0]
        applications.add(app_name)
    return sorted(list(applications))

def get_tables_for_application(application, file_dict):
    tables = []
    for filename, file_type in file_dict.items():
        if filename.startswith(f"{application}_"):
            table_data = get_file_data(filename, file_type)
            tables.append(table_data)
    return tables

def get_modified_time():
    current_time = datetime.datetime.now()
    modified_time = current_time - datetime.timedelta(hours=2)
    return modified_time.strftime("%Y-%m-%d %H:%M:%S")