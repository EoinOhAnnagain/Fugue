from itertools import count
from textwrap import wrap
from flask import Flask, request, jsonify
import config, uuid, mysql.connector, hashlib
from mysql.connector import errorcode
from functools import wraps
from datetime import datetime

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
    cursor.execute("SHOW TABLES;")
    queues = cursor.fetchall()
    returnable = []
    for q in queues:
        returnable.append(q[0])
    return returnable

""" Method to has password provided by user. Uses username and salts from confid file. Takes in a username and password """
def password_hash(user, password):
    password = hashlib.md5((password+user).encode())
    for salt in config.salts:
        password = hashlib.md5((password.hexdigest()+salt).encode())
    return password.hexdigest()

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

def checkUUID(cursor, employeeUUID=False, ticketUUID=False):
    if employeeUUID:
        cursor.execute("SELECT COUNT(*) from Users WHERE `UUID` = %s", (employeeUUID,))
    elif ticketUUID:
        cursor.execute("SELECT COUNT(*) from masterQueue WHERE `UUID` = %s", (ticketUUID,))

    if cursor.fetchall()[0][0] == 1:
        return True
    else:
        return False

def checkUser(cursor, email, hashedPassword=False):
    if hashedPassword:
        print('HP')
    else:
        cursor.execute("SELECT COUNT(*) from `Users` WHERE `email` = %s", (email,))

    if cursor.fetchall()[0][0] == 1:
        return True
    else:
        return False

def closeConnection(db, cursor):
    cursor.close()
    db.close()

def testUserInputString(db, cursor, string, key, length):
    if type(string) != str:
        closeConnection(db, cursor)
        return key + " isn't string"
    elif len(request.json["firstName"]) > length:
        closeConnection(db, cursor)
        return key + " is too long"
    elif len(request.json["firstName"]) < 3:
        closeConnection(db, cursor)
        return key + " is too short"
    elif key == 'email' and (string[-10:] != '@datto.com' and string[-11:] != '@kaseya.com'):
        closeConnection(db, cursor)
        return "Bad email submitted"
    else:
        return False

def loginUser(cursor, email, password):
    cursor.execute("SELECT COUNT(*) from `Users` WHERE `email` = %s AND `password` = %s", (email, password_hash(email, password)))
    if cursor.fetchall()[0][0] == 1:

        return True
    else:
        return False


@app.route('/')
def index():

    return 'Hello :) ' + password_hash('fdsfds', 'test') + ' :P'

@app.route('/register', methods=['POST'])
@getStarted
def registerNewUser(db, cursor):

    if db:

        UUID = str(uuid.uuid4().hex)
        while checkUUID(cursor, employeeUUID=UUID):
            UUID = str(uuid.uuid4().hex)

        if checkUser(cursor, request.json['email']):
            return "email is already in user", 400
        
        if testUserInputString(db, cursor, request.json['firstName'].lower(), 'firstName', 45) != False:
            return testUserInputString(db, cursor, request.json['firstName'].lower(), 'firstName', 45), 400
        if testUserInputString(db, cursor, request.json['lastName'].lower(), 'lastName', 45) != False:
            return testUserInputString(db, cursor, request.json['lastName'].lower(), 'lastName', 45), 400
        if testUserInputString(db, cursor, request.json['email'], 'email', 100) != False:
            return testUserInputString(db, cursor, request.json['email'], 'email', 100), 400
        if testUserInputString(db, cursor, request.json['team'].lower(), 'team', 45) != False:
            return testUserInputString(db, cursor, request.json['team'].lower(), 'team', 45), 400

        hashedPassword = password_hash(request.json['email'], request.json['password'])

        # Create query
        addUser = ("INSERT INTO Users (`UUID`, `firstName`, `lastName`, `email`, `password`, `team`) VALUES (%s, %s, %s, %s, %s, %s)")
        userData = (UUID, request.json['firstName'].lower(), request.json['lastName'].lower(), request.json['email'], hashedPassword, request.json['team'])

        # Execute and commit query
        cursor.execute(addUser, userData)
        db.commit()

        closeConnection(db, cursor)
        return "User Created", 200

    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/getQueueNames', methods=['GET'])
@getStarted
def getQueues(db, cursor):

    if db:

        # Get Employee data as a list of dictionaries and turn it into a JSON object
        json_dump = jsonify(getQueueNames(cursor))

        print(json_dump)

        # Close db connection
        closeConnection(db, cursor)

        # Return JSON and status code
        return json_dump, 200
    
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/checkMasterQueue', methods=['GET'])
@getStarted
def checkFullQueue(db, cursor):
    if db:

        if request.json['simple'].lower() == 'true':
            cursor.execute("SELECT ticket, email, active, componant FROM `masterQueue`")
        elif request.json['simple'].lower() != 'false':

            closeConnection(db, cursor)

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

        closeConnection(db, cursor)
         

        return json_dump, 200

    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/checkQueue', methods=['GET'])
@getStarted
def checkQueue(db, cursor):
    if db:
        try:
            
            queueName = request.json['componant'].lower()

            
            if request.json['simple'].lower() == 'false':
                cursor.execute("SELECT * FROM `" + queueName + "`")
            elif request.json['simple'].lower() != 'true':

                closeConnection(db, cursor)
                 

                return "True or false? Your Spelling Sucks", 403
            else:
                cursor.execute("SELECT email, ticket, position FROM `" + queueName + "`")
            
            entries = cursor.fetchall()

            if len(entries) == 0:
            
                closeConnection(db, cursor)
                 

                return queueName.lower() + " is empty", 200
    
            entriesArray = []
            entry = {}
            
            if request.json['simple'].lower() == 'false': 

                cursor.execute("DESCRIBE `" + queueName + "`")
                names = cursor.fetchall()
                
                for e in entries:
                    for i in range(0, len(e)):
                        entry[names[i][0]] = e[i]
                    entriesArray.append(entry.copy())

                returnable = sorted(entriesArray, key=lambda x: x['position'])

                returnable[0]['position'] = "Releasing"
                
                json_dump = jsonify(returnable)

            else:

                for e in entries:
                    entry = {
                        "ticket": e[1],
                        "email": e[0],
                        "position": e[2],
                    }
                    
                    entriesArray.append(entry.copy())
                returnable = sorted(entriesArray, key=lambda x: x['position'])

                returnable[0]['position'] = "Releasing"

                json_dump = jsonify(returnable)


            closeConnection(db, cursor)
            return json_dump, 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520

    else:
        closeConnection(db, cursor)
        return 'an error occured', 500
    

@app.route('/enterQueue', methods=['POST'])
@getStarted
def enterQueue(db, cursor):
    if db:
        try:
            '''IS EVERYTHING CHECKED HERE?????'''
            if loginUser(cursor, request.json['email'], request.json['password']) == False:
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT firstName, lastName, team FROM `Users`")
            userDetails = cursor.fetchall()

            if request.json['componant'].lower() not in getQueueNames(cursor):
                closeConnection(db, cursor)
                return "Unknown"

            cursor.execute("SELECT COUNT(*) FROM `" + request.json['componant'].lower() + "`")
            numberInQueue = cursor.fetchall()

            UUID = str(uuid.uuid4().hex)
            while checkUUID(cursor, ticketUUID=UUID):
                UUID = str(uuid.uuid4().hex)

            now = datetime.now()
            print(now.strftime("%d-%m-%Y %H:%M:%S"))
            print(userDetails[0][2])


            cursor.execute("SELECT team FROM Users WHERE `email` = %s", (request.json['email'],))
            teamName = cursor.fetchall()[0][0]

            currentDT = now.strftime("%Y-%m-%d %H:%M:%S")

            
            entryQuery = ("INSERT INTO " + request.json['componant'].lower() + " (`UUID`, `ticket`, `description`, `email`, `teamName`, `opened`, `position`) VALUES (%s, %s, %s, %s, %s, %s, %s)")
            entryData = (UUID, request.json['ticket'].upper(), request.json['description'], request.json['email'], userDetails[0][2], currentDT, numberInQueue[0][0]+1)

            cursor.execute(entryQuery, entryData)


            entryQuery = ("INSERT INTO masterQueue (`UUID`, `ticket`, `description`, `componant`, `email`, `teamName`, `active`, `opened`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
            entryData = (UUID, request.json['ticket'].upper(), request.json['description'], request.json['componant'], request.json['email'], teamName, bool_to_tiny(True), currentDT)
        
            cursor.execute(entryQuery, entryData)


            db.commit()
            
            
            # Close db connection
            closeConnection(db, cursor)

            return "Successfully in queue. your posiiton is " + str(numberInQueue[0][0]+1), 200
        except:
            closeConnection(db, cursor)
            print("something went wrong")
            return "something went wrong", 520

        
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/exitQueue', methods=['DELETE'])
@getStarted
def exitQueue(db, cursor):
    if db:

        try:

            if loginUser(cursor, request.json['email'], request.json['password']) == False:
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT * FROM `" + request.json['componant'].lower() + "` WHERE `ticket` = %s AND `email` = %s", (request.json['ticket'], request.json['email']))
            print(cursor.fetchall())

            cursor.execute("DELETE FROM `" + request.json['componant'].lower() + "` WHERE `ticket` = %s", (request.json['ticket'],))
            db.commit()

            cursor.execute("SELECT * FROM `" + request.json['componant'].lower() + "` WHERE `ticket` = %s", (request.json['ticket'],))
            print(cursor.fetchall())

            closeConnection(db, cursor)
            return "Queue exited", 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520

    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502

            



if __name__ == '__main__':
    app.run(port=4400)