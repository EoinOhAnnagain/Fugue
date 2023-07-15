from flask import Flask, request, jsonify
import config, uuid, mysql.connector, hashlib
from mysql.connector import errorcode
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)



# Methods

def p(p):
    print(p)


""" Wrapped method to setup endpoint """
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


""" Method to get the names of all componants users can queue in. Returns an array of all queue names as strings. Takes in the cursor """
def getQueueNames(cursor):
    cursor.execute("SHOW TABLES;")
    queues = cursor.fetchall()
    returnable = []
    for q in queues:
        if q[0] not in ('Users', 'masterQueue'):
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


""" Method to check if a generated UUID is already present in the database. Returns a boolean. Takes in the cursor and a UUID in one of the optional arguements """
def checkUUID(cursor, employeeUUID=False, ticketUUID=False, freezeUUID=False):
    if employeeUUID:
        cursor.execute("SELECT COUNT(*) from Users WHERE `UUID` = %s", (employeeUUID,))
    elif ticketUUID:
        cursor.execute("SELECT COUNT(*) from masterQueue WHERE `UUID` = %s", (ticketUUID,))
    elif freezeUUID:
        cursor.execute("SELECT COUNT(*) from CodeFreezes WHERE `UUID` = %s", (employeeUUID,))

    if cursor.fetchall()[0][0] == 1:
        return True
    else:
        return False


""" Method to check if a user exists in the database """
def checkForUser(cursor, email, hashedPassword=False):
    if hashedPassword:
        print('HP')
    else:
        cursor.execute("SELECT COUNT(*) from `Users` WHERE `email` = %s", (email,))

    if cursor.fetchall()[0][0] == 1:
        return True
    else:
        return False


""" Method to close the database connection. Takes in the cursor and the db connection. Return is void """
def closeConnection(db, cursor):
    cursor.close()
    db.close()


""" Method to test the users input string. Ta """
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


""" Method to log a user in. Returns a boolean. Takes in the cursor, the users email and password, and an optional boolean indicating if the user needs admin privileges """
def loginUser(cursor, email, password, admin=False):
    cursor.execute("SELECT isAdmin from `Users` WHERE `email` = %s AND `password` = %s", (email, password_hash(email, password)))
    result = cursor.fetchall()

    if len(result) == 0:
        return False
    elif admin and result[0][0] == 1:
        return True
    elif not admin and len(result) == 1:
        return True
    else:
        print("Unexpected")
        return False
        

""" Method to check if there is a general code freeze in effect. Returns True if there is a code freeze. Takes in the cursor """
def checkForCodeFreeze(cursor):
    
    cursor.execute("SELECT COUNT(*) FROM `CodeFreezes` WHERE begins <= CURDATE() AND ends >= CURDATE() AND inEffect = true;")
    return True if (cursor.fetchall())[0][0] != 0 else False 





# Endpoints

@app.route('/', methods=['GET'])
@getStarted
def index(db, cursor):

    cursor.execute("SELECT COUNT(*) FROM `auth-web` WHERE (`position` IN (0, 1))")
    count = cursor.fetchall()[0][0]
    # cursor.execute("SET SQL_SAFE_UPDATES = 0")
    # db.commit()

    # queues = getQueueNames(cursor)

    # for componant in queues:
    #     print(componant)
    #     cursor.execute("DELETE FROM `" + componant + "`")
    #     db.commit()

    # query = "DELETE FROM `masterQueue`"
    # cursor.execute(query)
    # db.commit()

    # cursor.execute("SET SQL_SAFE_UPDATES = 1")
    # db.commit()

    closeConnection(db, cursor)
    return "Success: " + str(count), 200




# User management endpoints

@app.route('/register', methods=['POST'])
@getStarted
def registerNewUser(db, cursor):

    if db:

        UUID = str(uuid.uuid4().hex)
        while checkUUID(cursor, employeeUUID=UUID):
            UUID = str(uuid.uuid4().hex)

        if checkForUser(cursor, request.json['email']):
            return "email is already in use", 400
        
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


@app.route('/toggleAdmin', methods=['PUT'])
@getStarted
def toggleAdmin(db, cursor):
    if db:
        try:

            cursor.execute("SELECT COUNT(*) FROM Users WHERE isAdmin = 1")
            adminCount = cursor.fetchall()[0][0]
            
            print(adminCount)

            if adminCount == 0:
                print("0 found")
                if not loginUser(cursor, request.json['email'], request.json['password']):
                    print("not log in")
                    closeConnection(db, cursor)
                    return "Login Failed", 400

                cursor.execute("UPDATE `Users` SET `isAdmin` = 1 WHERE (`email` = %s)", (request.json['targetEmail'],))
                db.commit()

                print("woop")
                closeConnection(db, cursor)
                print("woop")
                
                return "Emergency admin succesfully created", 200

            else:


                if not loginUser(cursor, request.json['email'], request.json['password'], True):
                    closeConnection(db, cursor)
                    return "Login Failed", 400

                if adminCount == 1 and request.json['email'] == request.json['targetEmail']:
                    closeConnection(db, cursor)
                    return "Cannot toggle as you are the only admin. Create another admin first", 403

                cursor.execute("SELECt COUNT(*), isAdmin FROM `Users` WHERE `email` = %s", (request.json['targetEmail'],))
                userFound = cursor.fetchall()[0]

                if userFound[0] == 0:
                    closeConnection(db, cursor)
                    return "Target not found", 403

                if userFound[1] == 1:
                    cursor.execute("UPDATE `Users` SET `isAdmin` = 0 WHERE (`email` = %s)", (request.json['targetEmail'],))
                    db.commit()
                    closeConnection(db, cursor)
                    return "Target is no longer an Admin", 200
                else:
                    cursor.execute("UPDATE `Users` SET `isAdmin` = 1 WHERE (`email` = %s)", (request.json['targetEmail'],))
                    db.commit()
                    closeConnection(db, cursor)
                    return "Target is now an Admin", 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/deleteSelf', methods=['DELETE'])
@getStarted
def deleteSelf(db, cursor):
    if db:
        try:

            if not loginUser(cursor, request.json['email'], request.json['password']):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT COUNT(*), isAdmin FROM `Users` WHERE (`email` = %s)", (request.json['email'],))
            userFound = cursor.fetchall()[0]

            if userFound[0] == 0:
                closeConnection(db, cursor)
                return "User not found", 403

            if userFound[1] == 1:

                cursor.execute("SELECT COUNT(*) FROM `Users` WHERE (`isAdmin` = 1)")
                if cursor.fetchall()[0][0] == 1:
                    closeConnection(db, cursor)
                    return "Deleting yourself would leave no Admins. Please create a new admin first", 403

            cursor.execute("SELECT UUID FROM Users WHERE email = %s", (request.json['email'],))
            userUUID = cursor.fetchall()[0][0]
            cursor.execute("DELETE FROM `Users` WHERE (`UUID` = %s);", (userUUID,))
            db.commit()

            closeConnection(db, cursor)
            return "You are deleted", 200



                





            
        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/deleteUser', methods=['DELETE'])
@getStarted
def deleteUser(db, cursor):
    if db:
        try:

            if not loginUser(cursor, request.json['email'], request.json['password'], True):
                closeConnection(db, cursor)
                return "Login Failed", 400

            if request.json['email'] == request.json['targetEmail']:
                closeConnection(db, cursor)
                return "This endpoint is not fo deleting oneslef", 403

            cursor.execute("SELECT COUNT(*) FROM `Users` WHERE (`email` = %s)", (request.json['targetEmail'],))
            userFound = cursor.fetchall()[0]

            if userFound[0] == 0:
                closeConnection(db, cursor)
                return "User not found", 403

            cursor.execute("SELECT UUID FROM Users WHERE email = %s", (request.json['targetEmail'],))
            userUUID = cursor.fetchall()[0][0]
            cursor.execute("DELETE FROM `Users` WHERE (`UUID` = %s);", (userUUID,))
            db.commit()

            closeConnection(db, cursor)
            return "User deleted", 200



                





            
        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502



# Queue endpoints

@app.route('/getQueueNames', methods=['GET'])
@getStarted
def getQueues(db, cursor):

    if db:

        # Get Employee data as a list of dictionaries and turn it into a JSON object
        json_dump = jsonify(getQueueNames(cursor))

        # Close db connection
        closeConnection(db, cursor)

        # Return JSON and status code
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
            
            if not request.json['simple']:
                cursor.execute("SELECT * FROM `" + queueName + "`")
            else:
                cursor.execute("SELECT email, ticket, position FROM `" + queueName + "`")
            
            entries = cursor.fetchall()

            if len(entries) == 0:
                closeConnection(db, cursor)
                return queueName.lower() + " is empty", 200
    
            entriesArray = []
            entry = {}
            
            if not request.json['simple']: 

                cursor.execute("DESCRIBE `" + queueName + "`")
                names = cursor.fetchall()
                
                for e in entries:
                    for i in range(0, len(e)):
                        entry[names[i][0]] = e[i]
                    entriesArray.append(entry.copy())

                returnable = sorted(entriesArray, key=lambda x: x['position'])

                returnable[0]['position'] = "Releasing" if returnable[0]['position'] == 0 else returnable[0]['position']
                
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

                print(returnable[0]['position'])
                returnable[0]['position'] = "Releasing" if returnable[0]['position'] == 0 else returnable[0]['position']

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
            
            if not loginUser(cursor, request.json['email'], request.json['password']):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT isAdmin, bypassCodeFreeze, team FROM `Users` WHERE `email` = %s", (request.json['email'],))
            userDetails = cursor.fetchall()[0]

            canBypassCodeFreezes = False if not tiny_to_bool(userDetails[0]) and not tiny_to_bool(userDetails[1]) else True
        
            if datetime.now().weekday() in (4, 5, 6) and not canBypassCodeFreezes:
                closeConnection(db, cursor)
                return "Releases may only be done Monday -> Thursday. Please enter the queue again on Monday morning", 400
        
            if checkForCodeFreeze(cursor) and not canBypassCodeFreezes:
                return "There is a code freeze in effect. New entries cannot be added to the queue until the code freeze ends", 403

            if len(request.json['description']) > 400:
                closeConnection(db, cursor)
                return "Description is too long. Please limit it to 400 charracters or less", 403


            if request.json['componant'].lower() not in getQueueNames(cursor):
                closeConnection(db, cursor)
                return "Unknown componant", 403

            if canBypassCodeFreezes:
                cursor.execute("UPDATE `Users` SET `bypassCodeFreeze` = 0 WHERE `email` = %s", (request.json['email'],))

            cursor.execute("SELECT COUNT(*) FROM `" + request.json['componant'].lower() + "` WHERE `ticket` = %s", (request.json['ticket'],))
            occurancesOfTicket = cursor.fetchall()[0][0]

            if occurancesOfTicket != 0:
                closeConnection(db, cursor)
                return "Ticket already in queue. There may only be one occurance of a ticket at a time", 403


            cursor.execute("SELECT COUNT(*) FROM `" + request.json['componant'].lower() + "`")
            numberInQueue = cursor.fetchall()

            UUID = str(uuid.uuid4().hex)
            while checkUUID(cursor, ticketUUID=UUID):
                UUID = str(uuid.uuid4().hex)

            now = datetime.now()
            currentDT = now.strftime("%Y-%m-%d %H:%M:%S")

            entryQuery = ("INSERT INTO `" + request.json['componant'].lower() + "` (`UUID`, `ticket`, `description`, `email`, `teamName`, `opened`, `position`) VALUES (%s, %s, %s, %s, %s, %s, %s)")
            entryData = (UUID, request.json['ticket'].upper(), request.json['description'], request.json['email'], userDetails[2], currentDT, numberInQueue[0][0]+1)

            cursor.execute(entryQuery, entryData)

            entryQuery = ("INSERT INTO masterQueue (`UUID`, `ticket`, `description`, `componant`, `email`, `teamName`, `active`, `opened`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
            entryData = (UUID, request.json['ticket'].upper(), request.json['description'], request.json['componant'], request.json['email'], userDetails[2], bool_to_tiny(True), currentDT)

            cursor.execute(entryQuery, entryData)
            db.commit()
            
            closeConnection(db, cursor)
            return "Successfully in queue. your posiiton is " + str(numberInQueue[0][0]+1), 200
        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/updateTicketDescription', methods=['PUT'])
@getStarted
def updateTicketDescription(db, cursor):
    if db:
        try:
            if not loginUser(cursor, request.json['email'], request.json['password']):
                closeConnection(db, cursor)
                return "Login Failed", 400

            print('egfyiewgi')

            if len(request.json['description']) > 400:
                closeConnection(db, cursor)
                return "Description is too long. Please limit it to 400 charracters or less", 403

            p("fnrwuoghour")

            query = "SELECT COUNT(*) FROM `" + request.json['componant'] + "` WHERE (`ticket` = %s AND `email` = %s)"
            print(query)
            cursor.execute(query, (request.json['ticket'], request.json['email'],))
            
            if cursor.fetchall()[0][0] == 0:
                closeConnection(db, cursor)
                return "No matching ticket found", 403

            query = "UPDATE `" + request.json['componant'] + "` SET `description` = %s WHERE (`ticket` = %s AND `email` = %s);"
            cursor.execute(query, (request.json['description'], request.json['ticket'], request.json['email'],))
            db.commit()



            closeConnection(db, cursor)
            return "Done", 200
        except:
            closeConnection(db, cursor)
            return "something went wrong", 500
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

            if len(request.json['reason']) > 100:
                closeConnection(db, cursor)
                return "Reason is too long. Please limit it to 400 charracters or less", 403

            if request.json['componant'].lower() not in getQueueNames(cursor):
                closeConnection(db, cursor)
                return "Unknown componant", 403

            cursor.execute("SELECT UUID, position FROM `" + request.json['componant'].lower() + "` WHERE `ticket` = %s", (request.json['ticket'],))
            entry = cursor.fetchall()

            if len(entry) != 1:
                closeConnection(db, cursor)
                return "No matching ticket found", 403

            UUID = entry[0][0]
            position = entry[0][1]
                
            now = datetime.now()
            currentDT = now.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("SELECT COUNT(*) FROM `" + request.json['componant'].lower() + "` WHERE (`position` IN (0, 1))")
            queueHeadCount = cursor.fetchall()[0][0]
                
            cursor.execute("DELETE FROM `" + request.json['componant'].lower() + "` WHERE `UUID` = %s", (UUID,))
            db.commit()
            
            
            print(queueHeadCount)
            if queueHeadCount != 2:
                cursor.execute("UPDATE `" + request.json['componant'].lower() + "` SET position = position - 1 WHERE (`position` > %s)", (position,))
                db.commit()
            
            cursor.execute("UPDATE `masterQueue` SET `active` = 0, `closed` = %s, `reasonClosed` = %s WHERE (`UUID` = %s);", (currentDT, request.json['reason'], UUID,))
            db.commit()
            
            closeConnection(db, cursor)
            return "Queue exited", 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520

    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/releasing', methods=['PUT'])
@getStarted
def releasing(db, cursor):
    if db:
        try:
            if not loginUser(cursor, request.json['email'], request.json['password']):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT UUID, position FROM `" + request.json['componant'] + "` WHERE (`email` = %s AND `ticket` = %s);", (request.json['email'], request.json['ticket'],))
            entry = cursor.fetchall()

            if len(entry) == 0:
                closeConnection(db, cursor)
                return "No tickets found in your name", 400
            elif len(entry) > 1:
                closeConnection(db, cursor)
                return "Erroneous number of ticket found", 400

            if entry[0][1] != 1:
                closeConnection(db, cursor)
                return "It is not your turn to release. Please create a priority ticket, after deleting this ticket, if you need to bypass the queue", 400

            cursor.execute("UPDATE `" + request.json['componant'] + "` SET `position` = 0 WHERE (`UUID` = %s)", (entry[0][0],))
            db.commit()

            closeConnection(db, cursor)
            return "Done", 200
        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/priorityQueueEntry', methods=['POST'])
@getStarted
def priorityQueueEntry(db, cursor):
    if db:
        try:

            print('starting')
            if not loginUser(cursor, request.json['email'], request.json['password']):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT isAdmin, bypassCodeFreeze, team FROM `Users` WHERE `email` = %s", (request.json['email'],))
            userDetails = cursor.fetchall()[0]

            canBypassCodeFreezes = False if not tiny_to_bool(userDetails[0]) and not tiny_to_bool(userDetails[1]) else True
        
            if datetime.now().weekday() in (4, 5, 6) and not canBypassCodeFreezes:
                closeConnection(db, cursor)
                return "Releases may only be done Monday -> Thursday. Please enter the queue again on Monday morning", 400
        
            if checkForCodeFreeze(cursor) and not canBypassCodeFreezes:
                return "There is a code freeze in effect. New entries cannot be added to the queue until the code freeze ends", 403

            if len(request.json['description']) > 400:
                closeConnection(db, cursor)
                return "Description is too long. Please limit it to 400 charracters or less", 403

            if request.json['componant'].lower() not in getQueueNames(cursor):
                closeConnection(db, cursor)
                return "Unknown componant", 403

            if canBypassCodeFreezes:
                cursor.execute("UPDATE `Users` SET `bypassCodeFreeze` = 0 WHERE `email` = %s", (request.json['email'],))

            cursor.execute("SELECT COUNT(*) FROM `" + request.json['componant'].lower() + "` WHERE `ticket` = %s", (request.json['ticket'],))
            occurancesOfTicket = cursor.fetchall()[0][0]

            if occurancesOfTicket != 0:
                closeConnection(db, cursor)
                return "Ticket already in queue. There may only be one occurance of a ticket at a time", 403


            cursor.execute("SELECT position, email FROM `" + request.json['componant'].lower() + "` WHERE (`position` IN (0, 1))")
            takenPosition = cursor.fetchall()

            if len(takenPosition) == 2:
                cursor.execute("SELECT firstName, lastName FROM `Users` WHERE (`email` = %s)", (takenPosition[1][1],))
                user = cursor.fetchall()
                closeConnection(db, cursor)
                return "" + user[0][0].capitalize() + " " + user[0][1].capitalize() + " is already awaiting a priority release. Please discuss with them which ticket should take priority", 403

            UUID = str(uuid.uuid4().hex)
            while checkUUID(cursor, ticketUUID=UUID):
                UUID = str(uuid.uuid4().hex)

            now = datetime.now()
            currentDT = now.strftime("%Y-%m-%d %H:%M:%S")

            ticketPosition = 1 if takenPosition[0][0] == 0 else 0

            print(takenPosition)
            print(ticketPosition)

            entryQuery = ("INSERT INTO `" + request.json['componant'].lower() + "` (`UUID`, `ticket`, `description`, `email`, `teamName`, `opened`, `position`) VALUES (%s, %s, %s, %s, %s, %s, %s)")
            entryData = (UUID, request.json['ticket'].upper(), request.json['description'], request.json['email'], userDetails[2], currentDT, ticketPosition)

            p(entryQuery)
            print(entryData)
            cursor.execute(entryQuery, entryData)

            entryQuery = ("INSERT INTO masterQueue (`UUID`, `ticket`, `description`, `componant`, `email`, `teamName`, `active`, `opened`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
            entryData = (UUID, request.json['ticket'].upper(), request.json['description'], request.json['componant'], request.json['email'], userDetails[2], bool_to_tiny(True), currentDT)

            cursor.execute(entryQuery, entryData)
            db.commit()
            
            closeConnection(db, cursor)

            if ticketPosition == 1:
                return "There is currently a ticket being released. You are next in line once they have released.", 200
            return "Your priority ticket has been added to the queue and is set to releasing.", 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


# Master queue endpoints

@app.route('/checkMasterQueue', methods=['GET'])
@getStarted
def checkMasterQueue(db, cursor):
    if db:
        try:

            query = "SELECT "
            query += "email, ticket, componant, active, opened, closed FROM `masterQueue`" if request.json['simple'] else  "* FROM `masterQueue`"
    
            if request.json['daysBack']:
                if isinstance(request.json['daysBack'], int):
                    # Yes I know...SQL Injection and shit....ugh
                    query += " WHERE opened >= ( CURDATE() - INTERVAL " + str(request.json['daysBack']) + " DAY )"
                else:
                    return "Type error. daysBack needs to be an int", 400

            cursor.execute(query)
            entries = cursor.fetchall()

            if len(entries) == 0:
                closeConnection(db, cursor)
                return "Master queue is empty", 200
            
            entriesArray = []
            entry = {}
            
            if request.json['simple']: 

                for e in entries:
                    entry = {
                        "ticket": e[1],
                        "email": e[0],
                        "componant": e[2],
                        "active": tiny_to_bool(e[3]),
                        "opened": e[4],
                    }
                    if not e[3]:
                        entry['closed'] =  e[5]
                    entriesArray.append(entry.copy())

            else:
                cursor.execute("DESCRIBE `masterQueue`")
                names = cursor.fetchall()
                
                for e in entries:
                    for i in range(0, len(e)):
                        entry[names[i][0]] = e[i]
                    entriesArray.append(entry.copy())


            returnable = sorted(entriesArray, key=lambda x: x['componant']) if request.json['byComponant'] else sorted(entriesArray, key=lambda x: x['opened'])
            json_dump = jsonify(returnable)

            closeConnection(db, cursor)
            return json_dump, 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520

    else:
        closeConnection(db, cursor)
        return 'an error occured', 500
    

@app.route('/emptyAllQueues', methods=['DELETE'])
@getStarted
def emptyAllQueues(db, cursor):

    cursor.execute("SET SQL_SAFE_UPDATES = 0")
    db.commit()

    queues = getQueueNames(cursor)

    for componant in queues:
        print(componant)
        cursor.execute("DELETE FROM `" + componant + "`")
        db.commit()

    query = "DELETE FROM `masterQueue`"
    cursor.execute(query)
    db.commit()

    cursor.execute("SET SQL_SAFE_UPDATES = 1")
    db.commit()

    closeConnection(db, cursor)
    return "Success", 200



# Code freeze related endpoints

@app.route('/createCodeFreeze', methods=['POST'])
@getStarted
def createCodeFreeze(db, cursor):

    if db:
        try:
            if not loginUser(cursor, request.json['email'], request.json['password'], True):
                closeConnection(db, cursor)
                return "Login Failed", 400

            UUID = str(uuid.uuid4().hex)
            while checkUUID(cursor, ticketUUID=UUID):
                UUID = str(uuid.uuid4().hex)

            inEffect = True if request.json['startIn'] == 0 else False

            startOfCodeFreeze = (datetime.now() + timedelta(days=request.json['startIn'])).strftime("%Y-%m-%d")
            endOfCodeFreeze = (datetime.now() + timedelta(days=request.json['startIn']) + timedelta(days=request.json['duration'])).strftime("%Y-%m-%d")

            entryQuery = ("INSERT INTO codeFreezes (`UUID`, `begins`, `duration`, `ends`, `inEffect`) VALUES (%s, %s, %s, %s, %s)")
            entryData = (UUID, startOfCodeFreeze, request.json['duration'], endOfCodeFreeze, inEffect)

            cursor.execute(entryQuery, entryData)
            db.commit()

            closeConnection(db, cursor)
            return "Done", 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/endActiveCodeFreeze', methods=['DELETE'])
@getStarted
def endActiveCodeFreeze(db, cursor):

    if db:
        try:
            if not loginUser(cursor, request.json['email'], request.json['password'], True):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT UUID FROM `CodeFreezes` WHERE `inEffect` = 1")
            UUIDs = cursor.fetchall()

            print(UUIDs)

            for UUID in UUIDs:
                print(UUID)
                cursor.execute("UPDATE `CodeFreezes` SET `inEffect` = 0 WHERE (`UUID` = %s)", (UUID[0],))    
            db.commit()

            closeConnection(db, cursor)
            return "Done", 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/checkFreezes', methods=['GET'])
@getStarted
def checkFreezes(db, cursor):
    if db:
        try:

            if not loginUser(cursor, request.json['email'], request.json['password']):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("DESCRIBE `CodeFreezes`")
            tableNames = cursor.fetchall()

            query = "SELECT * FROM `CodeFreezes`"

            query += " WHERE `inEffect` = 1" if tiny_to_bool(request.json['activeOnly']) else " WHERE (`begins` > CURDATE() AND `inEffect` = 0)" if tiny_to_bool(request.json['futureOnly']) else ""
            
            print(query)

            cursor.execute(query)
            freezes = cursor.fetchall()

            if len(freezes) == 0:
                closeConnection(db, cursor)
                return "No relevent freezes found", 200

            returnable = []
            entry = {}
            for f in freezes:
                for i in range(0, len(tableNames)):
                    entry[tableNames[i][0]] = f[i]
                returnable.append(entry.copy())

            json_dump = jsonify(returnable)

            closeConnection(db, cursor)
            return json_dump, 200
        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/endCodeFreeze', methods=['DELETE'])
@getStarted
def endFreeze(db, cursor):
    if db:
        try:
            if not loginUser(cursor, request.json['email'], request.json['password'], True):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("DELETE FROM `CodeFreezes` WHERE (`UUID` = %s)", (request.json['codeFreezeUUID'],))
            db.commit()

            closeConnection(db, cursor)
            return "Done", 200
        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502


@app.route('/allowEmployeeBypassCodeFreeze', methods=['PUT'])
@getStarted
def allowEmployeeBypassCodeFreeze(db, cursor):
    if db:
        try:
            if not loginUser(cursor, request.json['email'], request.json['password'], True):
                closeConnection(db, cursor)
                return "Login Failed", 400

            cursor.execute("SELECT UUID, isAdmin, bypassCodeFreeze, firstName, lastName FROM `Users` WHERE `email` = %s", (request.json['employeeEmail'],))
            
            employee = cursor.fetchall()

            if len(employee) != 1:
                closeConnection(db, cursor)
                return "Bad number of employees found", 403
            
            employee = employee[0]

            if tiny_to_bool(employee[1]):
                closeConnection(db, cursor)
                return "Employee is admin and doesn't need override", 200

            if tiny_to_bool(employee[2]):
                cursor.execute("UPDATE `Users` SET `bypassCodeFreeze` = 0 WHERE (`UUID` = %s)", (employee[0],))
                db.commit()

                closeConnection(db, cursor)
                return ("" + employee[3] + " " + employee[4] + " no longer has permission to release today"), 200

            cursor.execute("UPDATE `Users` SET `bypassCodeFreeze` = 1 WHERE (`UUID` = %s)", (employee[0],))
            db.commit()

            closeConnection(db, cursor)
            return ("" + employee[3] + " " + employee[4] + " has permission to release today"), 200

        except:
            closeConnection(db, cursor)
            return "something went wrong", 520
    else:
        closeConnection(db, cursor)
        return jsonify({'Error': "Database Connection Error"}), 502



# Endpoint skeleton

# @app.route('/', methods=[''])
# @getStarted
# def methodName(db, cursor):
#     if db:
#         try:
#             if not loginUser(cursor, request.json['email'], request.json['password'], True):
#                 closeConnection(db, cursor)
#                 return "Login Failed", 400
#             closeConnection(db, cursor)
#             return "Done", 200
#         except:
#             closeConnection(db, cursor)
#             return "something went wrong", 520
#     else:
#         closeConnection(db, cursor)
#         return jsonify({'Error': "Database Connection Error"}), 502


if __name__ == '__main__':
    app.run(port=4400)