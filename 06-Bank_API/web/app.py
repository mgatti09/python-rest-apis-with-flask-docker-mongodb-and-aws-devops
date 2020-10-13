"""
    API for manage Bank transactions
"""

from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

# When the mongoDB client is created //db must be the same name defined in the file 
# Default mongoDB port is 27017
# docker-compose.yml for the mongoDB container
client = MongoClient("mongodb://db:27017")

#Step 1: create a DB
db = client.BankAPI

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

def getMoney(username):
    """
        Auxiliar function returns amount of Money a username have
    """
    return users.find({"Username": username})[0]["Money"]

def getDebt(username):
    """
        Auxiliar function returns amount of Debt a username have
    """
    return users.find({"Username": username})[0]["Debt"]

def setMoney(username, balance):
    """
        Auxiliar function update the amount of Money a username have
    """
    SELECTION_CRITERIA = {
        "Username": username
    }
    UPDATED_DATA = {
        "Money": balance
    }
    users.update(SELECTION_CRITERIA,{"$set":UPDATED_DATA})

def setDebt(username, balance):
    """
        Auxiliar function update amount of Debt a username have
    """
    SELECTION_CRITERIA = {
        "Username": username
    }
    UPDATED_DATA = {
        "Debt": balance
    }
    users.update(SELECTION_CRITERIA,{"$set":UPDATED_DATA})



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
            retJson = genJson(301, f"Invalid username. User {username} already exists")
            return jsonify(retJson)

        # Step 4: Hash the password with bcrypt
        hashed_pw = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        # Step 4: Store in the DB the info of the new user bankAPI        
        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Money": 0,
            "Debt": 0

        })

        # Step 5: Return message to the user
        retJson = genJson(200, "You successfully signed up for the API")
        return jsonify(retJson)

class Add(Resource):
    """
        Class to add money to and account
    """
    def post(self):
        """
            POST Function that handles the adding money to an account
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        # Step 3: Verify credentials
        retJson, validCredentials = verifyCredentials(username,password)
        if not validCredentials:
            return jsonify(retJson)

        # Step 4: Verify money amount to add is less or equal than 0        
        if amount <= 0:
            retJson = genJson(304,"The amount must be greater than 0")
            return jsonify(retJson)

        # Step 5: Get the money of the username, charge 1 USD for every transaction and
        # add that money to the BANK account and the user Account
        balance = getMoney(username) + amount - 1
        setMoney(username, balance)

        bankMoney = getMoney("BANK")
        setMoney("BANK", bankMoney+1)

        # Step 6: return 200 OK
        retJson = genJson(200,f"Amount added succesfully, the new balance is ${balance}")        
        return jsonify(retJson)

class Transfer(Resource):
    """
        Transfer money
    """
    def post(self):
        """
            POST Function that transfer money from an user to another user
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]
        to = postedData["to"]

        # Step 3: Verify credentials
        retJson, validCredentials = verifyCredentials(username,password)
        if not validCredentials:
            return jsonify(retJson)

        # Step 4: Verify money amount to add is less or equal than 0        
        if amount <= 0:
            retJson = genJson(304,"You're are of money, please add or take a loan")
            return jsonify(retJson)
        
        # Step 5: Verify the destiny username exists        
        if not userExist(to):
            retJson = genJson(301, f"User {to} does not exists")
            return jsonify(retJson)

        # Step 6: Verify if the user have enough money to send 
        balanceFrom = getMoney(username) - amount - 1

        if balanceFrom < 0:
            retJson = genJson(306,"Transfer amount is higher than amount in the account. Please add or take a loan")
            return jsonify(retJson)

        # Step 7: Make the transfer and update the amounts
        balanceTo   = getMoney(to) + amount       
        balanceBank = getMoney("BANK") + 1

        setMoney(username, balanceFrom)
        setMoney(to, balanceTo)
        setMoney("BANK", balanceBank)

        # Step 8: return 200 OK
        retJson = genJson(200,f"Amount transfer succesfully, you're new balance is ${balanceFrom}")        
        return jsonify(retJson)

class BalanceCheck(Resource):
    """
        Check balamce
    """
    def post(self):
        """
            POST Function that check the balance
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]

        # Step 3: Verify credentials
        retJson, validCredentials = verifyCredentials(username,password)
        if not validCredentials:
            return jsonify(retJson)

        # Step 4: Get the data of the user using Projections
        retJson = users.find({
            "Username": username
        }, {
            "Password": 0,
            "_id":0
        })[0]      

        # Step 8: return 200 OK
        return jsonify(retJson)

class TakeLoan(Resource):
    """
        Class to take a loan from the Bank
    """
    def post(self):
        """
            POST Function that handles taking a loan
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]
        loanAmount = postedData["amount"]

        # Step 3: Verify credentials
        retJson, validCredentials = verifyCredentials(username,password)
        if not validCredentials:
            return jsonify(retJson)

        # Step 4: Update the cash and the debt for the user. This is out of charges
        cash = getMoney(username)
        debt = getDebt(username)

        setMoney(username, cash+loanAmount)
        setDebt(username, debt+loanAmount)

        # Step 6: return 200 OK
        retJson = genJson(200,f"Load added succesfully, the new balance is ${cash+loanAmount}")        
        return jsonify(retJson)

class PayLoan(Resource):
    """
        Class to pay a loan from the Bank
    """
    def post(self):
        """
            POST Function that handles paying a loan
        """
        # Step 1: Get posted data by the user
        postedData = request.get_json()

        # Step 2: Get the data
        username = postedData["username"]
        password = postedData["password"]
        payAmount = postedData["amount"]

        # Step 3: Verify credentials
        retJson, validCredentials = verifyCredentials(username,password)
        if not validCredentials:
            return jsonify(retJson)

        # Step 4: Verify if the user have enough money to pay the desired amount
        cash = getMoney(username) 

        if cash < payAmount:
            retJson = genJson(303,"Not enough money in your account, please reconsider the amount to pay")
            return jsonify(retJson)

        # Step 4: Verify if the amount money to pay isn't greater than the debt
        debt = getDebt(username)

        if debt < payAmount:
            retJson = genJson(305,f"Please check, you're trying to pay more")
            return jsonify(retJson)    
        
        # Step 6: Update the cash and the debt for the user. This is out of charges
        setMoney(username, cash - payAmount)
        setDebt(username, debt - payAmount)

        # Step 7: return 200 OK
        retJson = genJson(200,"Paid loan succesfully")        
        return jsonify(retJson)


""" 
********************end API Resources Class definition****************************
"""


""" 
********************Adding the resources to the API****************************
"""
api.add_resource(Register,'/register')
api.add_resource(Add,'/add')
api.add_resource(Transfer,'/transfer')
api.add_resource(BalanceCheck,'/balanceCheck')
api.add_resource(TakeLoan,'/takeLoan')
api.add_resource(PayLoan,'/payLoan')
""" 
****************end Adding the resources to the API****************************
"""

if __name__ == "__main__":
    app.run(host='0.0.0.0')