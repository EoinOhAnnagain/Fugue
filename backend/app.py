from textwrap import wrap
from flask import Flask, request, jsonify
import config, uuid, mysql.connector
from mysql.connector import errorcode
from functools import wraps

app = Flask(__name__)


def getStarted(f):
    @wraps(f)
    def getSetUp(*args, **kwargs):

        db = create_db_connection()
        cursor = db.cursor()

        return f(db, cursor, *args, **kwargs)
    return getSetUp

""" Method to create connection with the database. Returns the database connection if successful. Returns False if there is an error and prints the error """
def create_db_connection():
    try:
        db = mysql.connector.connect(host=config.host, user=config.user, password=config.password, database=config.database)
        return db
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            return False
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            return False
        else:
            return False

def getQueueNames(cursor):
    cursor.execute("SELECT * FROM `Queues`")
    queues = cursor.fetchall()
    returnable = []
    for q in queues:
        print(q)
        print(q[0])
        returnable.append(q[0])
    print(queues)
    print(returnable)
    return returnable
    




@app.route('/')
def index():
    return 'Hello :)' + str(uuid.uuid4().hex) + ':P'

@app.route('/getQueueNames')
@getStarted
def getQueues(db, cursor):

    print("test")

    if db != False:

        print('db found')
        # Get Employee data as a list of dictionaries and turn it into a JSON object
        json_dump = jsonify(getQueueNames(cursor))

        print(json_dump)

        # Close db connection
        cursor.close()
        db.close()

        print("oh yeah")

        # Return JSON and status code
        return json_dump, 200
    else:
        cursor.close()
        db.close()
        return jsonify({'Error': "Database Connection Error"}), 502

    



@app.route('/checkFullQueue', methods=['GET'])
def checkFullQueue():
    db = create_db_connection()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM `Queue`")
        test = cursor.fetchall()
        # Get Employee data as a list of dictionaries and turn it into a JSON object
        json_dump = jsonify(test)

        # Close db connection
        cursor.close()
        db.close()

        # Return JSON and status code
        return json_dump, 200
    else:
        return "an error occured", 404


@app.route('/enterQueue', methods=['POST'])
def enterQueue():
    db = create_db_connection()
    if db:
        try:
            cursor = db.cursor()
            UUID = str(uuid.uuid4().hex)
            
            entryQuery = ("INSERT INTO Queue (`UUID`, `Ticket`, `Description`, `Componant`, `Team Name`, `Email`, `First Name`, `Last Name`, `Active`, `Position`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            entryData = (UUID, request.json['Ticket'], request.json['Description'], request.json['Componant'], request.json['Team Name'], request.json['Email'], request.json['First Name'], request.json['Last Name'], 1, request.json['Position'])

            print('test2')
            cursor.execute(entryQuery, entryData)
            print('test3')
            db.commit()
            print('test4')

            # Close db connection
            cursor.close()
            db.close()
        except:
            print("something went wrong")
            return "something went wrong", 

        return "Successfully intered in queue, your posiiton is " + request.json['Position'], 200

    else:
        return 'an error occured', 404


if __name__ == '__main__':
    app.run(port=4400)