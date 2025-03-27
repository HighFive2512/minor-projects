from flask import Flask

from dashapp.Dashboard import dashapp

app = Flask(__name__)

app.register_blueprint(dashapp,url_prefix='/dashapp',static_folder='static',template_folder='templates')

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080)