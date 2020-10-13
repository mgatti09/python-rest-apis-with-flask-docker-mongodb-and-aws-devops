"""
Requirements:
Each user gets 10 tokens
Registration of a user 
Store a sentence on our database cost 1 token
Retrieve a sentence from our database cost 1 token
"""

from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

# When the mongoDB client is created //db must be the same name defined in the file 
# docker-compose.yml for the mongoDB container
client = MongoClient("mongodb://db:27017")

#Step 1: create a DB
db = client.SentencesDatabase

# Step 2: create collections
# Collection of users who stores sentences
users = db["Users"]

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

        # Step 3: Hash the password with bcrypt
        hashed_pw = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        # Step 4: Store the username and password into the DB
        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Sentence": "",
            "Tokens": 6

        })

        # Step 5: Return message to the user
        retJson = {
            "status": 200,
            "msg": "You successfully signed up for the API"
        }

        return jsonify(retJson)

def verifyPw(username,password):
    """
        Auxiliar function to verify the username and password. Return True or False
    """
    hashed_pw = users.find({"Username": username})[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'),hashed_pw) == hashed_pw:
        return True
    
    return False

def getTokens(username):
    """
        Auxiliar function returns number of tokens a username have
    """
    tokens = users.find({"Username": username})[0]["Tokens"]
    return tokens

class Store(Resource):
    """
        Class to store sentences
    """
    def post(self):
        """
            POST Function that handles the sentences storing
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]
        sentence = postedData["sentence"]

        # Step 3: Verify the username and password match
        correct_pw = verifyPw(username, password)
        if not correct_pw:
            retJson = {
                "status": 302
            }
            return jsonify(retJson)       

        # Step 4: Verify user has enough tokens
        tokens = getTokens(username)
        if tokens <= 0:
            retJson = {
                "status": 301
            }
            return jsonify(retJson)

        # Step 5: Store the sentence, take one token away and return 200 OK
        SELECTION_CRITERIA = {
            "Username": username
        }
        UPDATED_DATA = {
            "Sentence": sentence,
            "Tokens": tokens - 1
        }
        users.update(SELECTION_CRITERIA,{"$set":UPDATED_DATA})

        retJson = {
            "status": 200,
            "message": "Sentence saved succesfully"
        }
        return jsonify(retJson)

class GetSentence(Resource):
    """
        Retrieve a sentence
    """
    def post(self):
        """
            POST Function that retrieves a sentence
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]

        # Step 3: Verify the username and password match
        correct_pw = verifyPw(username, password)
        if not correct_pw:
            retJson = {
                "status": 302
            }
            return jsonify(retJson)       

        # Step 4: Verify user has enough tokens
        tokens = getTokens(username)
        if tokens <= 0:
            retJson = {
                "status": 301
            }
            return jsonify(retJson)

        # Step 5: Take one token away, retrieve the sentence and return 200 OK
        SELECTION_CRITERIA = {
            "Username": username
        }
        UPDATED_DATA = {
            "Tokens": tokens - 1
        }
        users.update(SELECTION_CRITERIA,{"$set":UPDATED_DATA})

        sentence = users.find(SELECTION_CRITERIA)[0]["Sentence"]

        retJson = {
            "status": 200,
            "message": sentence
        }
        return jsonify(retJson)       

api.add_resource(Register,'/register')
api.add_resource(Store,'/store')
api.add_resource(GetSentence,'/getSentence')

if __name__ == "__main__":
    app.run(host='0.0.0.0')