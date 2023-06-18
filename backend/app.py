from itertools import count
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
        returnable.append(q[0])
    return returnable

""" Method to convert a bool to a tinyint for storage in mysql database. True becomes 1 and Flase becomes 0. Expects a boolean """
def bool_to_tiny(x):
    if str(x).lower() == "true":
        return "1"
    else:
        return "0"

""" Method to convert a tinyint to a bool for returning to the user. 0 becomes False. Anything else becomes True. Expects an int """
def tiny_to_bool(x):
    if x == 0:
        return False
    else:
        return True





@app.route('/')
def index():
    return 'Hello :)' + str(uuid.uuid4().hex) + ':P'

@app.route('/getQueueNames', methods=['GET'])
@getStarted
def getQueues(db, cursor):

    if db:

        # Get Employee data as a list of dictionaries and turn it into a JSON object
        json_dump = jsonify(getQueueNames(cursor))

        print(json_dump)

        # Close db connection
        cursor.close()
        db.close()

        # Return JSON and status code
        return json_dump, 200
    else:
        cursor.close()
        db.close()
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/checkMasterQueue', methods=['GET'])
@getStarted
def checkFullQueue(db, cursor):
    if db:

        if request.json['simple'].lower() == 'true':
            cursor.execute("SELECT ticket, email, active, componant FROM `masterQueue`")
        elif request.json['simple'].lower() != 'false':

            cursor.close()
            db.close()

            return "True or false? Your Spelling Sucks", 403
        else:
            cursor.execute("SELECT * FROM `masterQueue`")

        entries = cursor.fetchall()


        returnable = []
        entry = {}
        
        if request.json['simple'].lower() == 'false': 

            cursor.execute("DESCRIBE `masterQueue`")
            names = cursor.fetchall()
            
            for e in entries:
                for i in range(0, len(e)):
                    entry[names[i][0]] = e[i]
                returnable.append(entry.copy())
            returnable.reverse()

            json_dump = jsonify(returnable)

        else:

            for e in entries:
                entry = {
                    "ticket": e[0],
                    "email": e[1],
                    "active": tiny_to_bool(e[2]),
                    "componant": e[3]
                }

                returnable.append(entry.copy())
            returnable.reverse()

            json_dump = jsonify(returnable)

        cursor.close()
        db.close()

        return json_dump, 200

    else:

        cursor.close()
        db.close()
        return "an error occured", 404


@app.route('/checkQueue', methods=['GET'])
@getStarted
def checkQueue(db, cursor):
    if db:
        try:
            
            queueName = request.json['queueName'].lower()

            
            if request.json['simple'].lower() == 'false':
                cursor.execute("SELECT * FROM `" + queueName + "`")
            elif request.json['simple'].lower() != 'true':

                cursor.close()
                db.close()

                return "True or false? Your Spelling Sucks", 403
            else:
                cursor.execute("SELECT email, ticket, position FROM `" + queueName + "`")
            
            entries = cursor.fetchall()

            if len(entries) == 0:
            
                cursor.close()
                db.close()

                return queueName.lower() + " is empty", 200
    
            returnable = []
            entry = {}
            
            if request.json['simple'].lower() == 'false': 

                cursor.execute("DESCRIBE `" + queueName + "`")
                names = cursor.fetchall()
                
                for e in entries:
                    for i in range(0, len(e)):
                        entry[names[i][0]] = e[i]
                    returnable.append(entry.copy())
                returnable.reverse()

                json_dump = jsonify(returnable)

            else:

                for e in entries:
                    entry = {
                        "ticket": e[0],
                        "email": e[1],
                        "position": e[2],
                    }
                    
                    returnable.append(entry.copy())
                returnable.reverse()

                json_dump = jsonify(returnable)


            cursor.close()
            db.close()
            return json_dump, 200

        except:
            cursor.close()
            db.close()
            print("something went wrong")
            return "something went wrong", 520

    else:
        cursor.close()
        db.close()
        return 'an error occured', 500
    



@app.route('/enterQueue', methods=['POST'])
@getStarted
def enterQueue(db, cursor):
    if db:
        try:
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

            return "Successfully intered in queue, your posiiton is " + request.json['Position'], 200
        except:
            cursor.close()
            db.close()
            print("something went wrong")
            return "something went wrong", 520

        

    else:
        cursor.close()
        db.close()
        return 'an error occured', 500


if __name__ == '__main__':
    app.run(port=4400)