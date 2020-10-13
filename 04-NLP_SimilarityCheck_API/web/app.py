"""

"""

from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import spacy

app = Flask(__name__)
api = Api(app)

# When the mongoDB client is created //db must be the same name defined in the file 
# docker-compose.yml for the mongoDB container
client = MongoClient("mongodb://db:27017")

#Step 1: create a DB
db = client.SimilarityDB

# Step 2: create collections
users = db["Users"]

""" 
****************************AUXILIAR FUNTCIONS***********************************
"""
def userExist(username):
    """
        Auxiliar function to check if a username already exists in the DB.
        Return True if exists, otherwise returns False
    """
    SELECTION_CRITERIA = {
        "Username": username
    }
    if users.find(SELECTION_CRITERIA).count() > 0:
        return True
    else:
        return False

def verifyPw(username,password):
    """
        Auxiliar function to verify the username and password. Return True or False
    """
    if not userExist(username):
        return False

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
        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 6

        })

        # Step 5: Return message to the user
        retJson = {
            "status": 200,
            "msg": "You successfully signed up for the API"
        }

        return jsonify(retJson)
""" 
************************end AUXILIAR FUNTCIONS***********************************
"""

""" 
************************API Resources Class definition****************************
"""
class Detect(Resource):
    """
        Class to detect the similarity of two texts
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
        text1    = postedData["text1"]
        text2    = postedData["text2"]

        # Step 3: Check if user already exists
        if not userExist(username):
            retJson = {
                "status": 301,
                "msg": f"Invalid username. User {username} already exists"
            }
            return jsonify(retJson)

        # Step 4: Verify if the username and password match
        correct_pw = verifyPw(username, password)
        if not correct_pw:
            retJson = {
                "status": 302,
                "msg": "Invalid password"
            }
            return jsonify(retJson)       

        # Step 5: Verify user has enough tokens
        tokens = getTokens(username)
        if tokens <= 0:
            retJson = {
                "status": 303,
                "msg": "You are out of tokens, please refill"
            }
            return jsonify(retJson)

        # Step 6: Calculate the similarity between text1 and text2 
        # Step 6.1: Calculating the Edit Distance with spacy
        nlp = spacy.load('en_core_web_sm')

        text1 = nlp(text1)
        text2 = nlp(text2)

        # Step 6.2: Calculate the ratio. Ratio is a number between 0 and 1.
        # The closer to 1, the more similar text1 and text2 are
        ratio = text1.similarity(text2)

        # Step 7: Take one token away and return 200 OK
        takeOneToken(username)

        retJson = {
            "status": 200,
            "similarity": ratio,
            "msg": "Similarity score calculated successfully"
        }

        return jsonify(retJson)

class Refill(Resource):
    """
        An Admin can refill the amount of tokens to a specific user
    """
    def post(self):
        """
            POST Function that retrieves a sentence
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        admPsswd = postedData["admin_pw"]
        refillAmount = postedData["refill"]

        # Step 3: Check if user already exists
        if not userExist(username):
            retJson = {
                "status": 301,
                "msg": f"Invalid username. User {username} already exists"
            }
            return jsonify(retJson)

        # Step 4: Verify if the admin password match
        correct_admPsswd = "abc123" #later make a collection to store the correct admin pw. Now is hardcoded
        if correct_admPsswd != admPsswd: 
            retJson = {
                "status": 304,
                "msg": "Invalid Admin password"
            }
            return jsonify(retJson)

        # Step 5: Refill tokens and return 200 OK
        newTokens = refillTokens(username, refillAmount)

        retJson = {
            "status": 200,
            "msg": f"Tokens Refill successful. User {username} now have {newTokens} tokens"
        }
        return jsonify(retJson)       

""" 
********************end API Resources Class definition****************************
"""


""" 
********************Adding the resources to the API****************************
"""
api.add_resource(Register,'/register')
api.add_resource(Detect,'/detect')
api.add_resource(Refill,'/refill')
""" 
****************end Adding the resources to the API****************************
"""

if __name__ == "__main__":
    app.run(host='0.0.0.0')