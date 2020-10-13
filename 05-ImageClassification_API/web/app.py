"""
    API for image Classification
"""

from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
import json
import numpy
import tensorflow

app = Flask(__name__)
api = Api(app)

# When the mongoDB client is created //db must be the same name defined in the file 
# Default mongoDB port is 27017
# docker-compose.yml for the mongoDB container
client = MongoClient("mongodb://db:27017")

#Step 1: create a DB
db = client.ClassifyDB

# Step 2: create collections
users = db["Users"]

""" 
****************************AUXILIAR FUNTCIONS***********************************
"""
def genJson(errCode, errMsg):
    retJson = {
        "status": errCode,
        "msg": errMsg
    }
    return retJson     

def userExist(username):
    """
        Auxiliar function to check if a username already exists in the DB.
        Return True if exists, otherwise returns False
    """
    SELECTION_CRITERIA = {
        "Username": username
    }
    return users.find(SELECTION_CRITERIA).count() > 0

def verifyCredentials(username,password):
    """
        Auxiliar function to verify the credentials of username and password. 
        Return True or False
    """
    if not userExist(username):
        errJson = genJson(301, f"Invalid username. User {username} already exists")
        return errJson, False

    hashed_pw = users.find({"Username": username})[0]["Password"]
    if bcrypt.hashpw(password.encode('utf8'),hashed_pw) != hashed_pw:
        errJson = genJson(302, f"Invalid password for User {username}")
        return errJson, False
    
    return None, True

def getTokens(username):
    """
        Auxiliar function returns number of tokens a username have
    """
    tokens = users.find({"Username": username})[0]["Tokens"]
    return tokens

def takeOneToken(username):
    """
        Auxiliar function that update the DB taking one token away from the username
    """
    tokens = getTokens(username)
        
    SELECTION_CRITERIA = {
        "Username": username
    }
    UPDATED_DATA = {
        "Tokens": tokens - 1
    }
    users.update(SELECTION_CRITERIA,{"$set":UPDATED_DATA})

def refillTokens(username, tokensAumount):
    """
        Auxiliar function to refill the number of tokens of a specific user
    """
    tokens = getTokens(username) + tokensAumount
        
    SELECTION_CRITERIA = {
        "Username": username
    }
    UPDATED_DATA = {
        "Tokens": tokens
    }
    users.update(SELECTION_CRITERIA,{"$set":UPDATED_DATA})

    return tokens

def verifyTokens(username):
    errCode = 303
    errMsg = "You are out of tokens, please refill"

    tokens = getTokens(username)
    if tokens <= 0:
        errJson = genJson(errCode, errMsg)
        return errJson, False
    
    return None, True

""" 
************************end AUXILIAR FUNTCIONS***********************************
"""

""" 
************************API Resources Class definition****************************
"""

class Register(Resource):
    """
        Class for support registration
    """
    def post(self):
        """
            POST Function that handles the registration of a user
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]

        # Step 3: Check if user already exists
        if userExist(username):
            retJson = {
                "status": 301,
                "msg": f"Invalid username. User {username} already exists"
            }
            return jsonify(retJson)

        # Step 4: Hash the password with bcrypt
        hashed_pw = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        # Step 4: Store the username, password and the amount of tokens into the DB
        tokens = 6
        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": tokens

        })

        # Step 5: Return message to the user
        retJson = {
            "status": 200,
            "msg": f"You successfully signed up for the API. Take this {tokens} free tokens"
        }

        return jsonify(retJson)

class Classify(Resource):
    """
        Class to detect classify an image
    """
    def post(self):
        """
            POST Function that handles the image classification
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]
        imageUrl = postedData["url"]

        # Step 3: Verify credentials
        retJson, validCredentials = verifyCredentials(username,password)
        if not validCredentials:
            return jsonify(retJson)

        # Step 5: Verify user has enough tokens
        retJson, haveTokens = verifyTokens(username)
        if not haveTokens:
            return jsonify(retJson)

        # Step 6: Download the image of the URL in Python and genereta the JSON prediction
        retJson = {}
        r = requests.get(imageUrl)
        with open("temp.jpg","wb") as f:
            f.write(r.content)
            # Step 6.1: Open a Python subprocess to classify the image
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=temp.jpg', shell=True)
            proc.communicate()[0]
            proc.wait()
            with open("text.txt") as g:
                retJson = json.load(g)

        # Step 7: Take one token away and return 200 OK
        takeOneToken(username)
        
        return jsonify(retJson)

class Refill(Resource):
    """
        An Admin can refill the amount of tokens to a specific user
    """
    def post(self):
        """
            POST Function that refill the amount of tokens to a specific user
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        admPsswd = postedData["admin_pw"]
        refillAmount = postedData["refill"]

        # Step 3: Check if user already exists
        if not userExist(username):
            return jsonify(genJson(301, f"Invalid username. User {username} already exists"))

        # Step 4: Verify if the admin password match
        correct_admPsswd = "abc123" #later make a collection to store the correct admin pw. Now is hardcoded
        if correct_admPsswd != admPsswd:
            return jsonify(genJson(304, "Invalid Admin password"))

        # Step 5: Refill tokens and return 200 OK
        amount = refillTokens(username, refillAmount)

        return jsonify(genJson(200, f"Tokens Refill successful. User {username} now have {amount} tokens"))

""" 
********************end API Resources Class definition****************************
"""


""" 
********************Adding the resources to the API****************************
"""
api.add_resource(Register,'/register')
api.add_resource(Classify,'/classify')
api.add_resource(Refill,'/refill')
""" 
****************end Adding the resources to the API****************************
"""

if __name__ == "__main__":
    app.run(host='0.0.0.0')