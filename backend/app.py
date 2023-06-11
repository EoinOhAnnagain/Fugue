from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello :)'

@app.route('/about')
def about():
    return 'about found'

@app.route('/newQueueItem', methods=['GET'])
def newQueueEntry():
    #return "First Name = ", request.json['firstName'] , " Last Name = ", request.json['lastName']
    return jsonify({"test1": "test", "test2": "test2"})


if __name__ == '__main__':
    app.run(port=4400)