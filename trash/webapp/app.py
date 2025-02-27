from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Sample route to render the dashboard
@app.route('/')
def index():
    return render_template('index.html')

# Sample API route to fetch data from databases
@app.route('/api/data')
def get_data():
    # Sample data to mimic dynamic values for server status
    data = {
        "labels": ["Server 4", "Server 5", "Server 6"],
        "values": [15, 25, 35]
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
