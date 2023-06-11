from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello, Flask!'

@app.route('/about')
def about():
    return 'about found'


if __name__ == '__main__':
    app.run(port=4400)