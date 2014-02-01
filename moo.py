#!/usr/bin/env python3
import json, sys, time as dt, pprint, urllib
import pymongo
import re
import time as t

from Imgur.Factory import Factory
from Imgur.Auth.Expired import Expired
from bitcoinrpc.authproxy import AuthServiceProxy
from pymongo import MongoClient

fd = open('config.json', 'r')
config = json.loads(fd.read())

factory = Factory(config)
time = int(dt.time())

client = MongoClient()
db = client.mootip
goat = AuthServiceProxy("http://user:pass@127.0.0.1:22555")

def loop():
    while True:
        now = t.time()

        if now >= config['expires']:
            refresh()

        try:
            notifications()
        except:
            print('An exception occurred.')

        try:
            notifications()
        except:
            print('An exception occurred.')

        try:
            conversations()
        except:
            print('An exception occurred.')

        t.sleep(30)

def refresh():
    print("Refreshing token. (" + str(t.time()) + ')')
    token = config['refresh_token']
    imgur = factory.buildAPI()
    req = factory.buildRequestOAuthRefresh(token)
    res = imgur.retrieveRaw(req)

    ts = t.time()
    ts = ts + 3000

    config['access_token'] = res[1]['access_token']
    config['refresh_token'] = res[1]['refresh_token']
    config['expires'] = ts

    with open('config.json', 'w') as outfile:
        json.dump(config, outfile)

def boot():
    if len(sys.argv) == 2:
        auth()
    elif len(sys.argv) == 3:
        auth()
    else:
        print("Switching to main loop.")
        loop()

def auth():
    action = sys.argv[1]

    if action == 'authorize':
        if len(sys.argv) == 2:
            print("Visit this URL to get a PIN to authorize: https://api.imgur.com/oauth2/authorize?client_id=" + config['client_id'] + "&response_type=pin")
        if len(sys.argv) == 3:
            pin = sys.argv[2]
            imgur = factory.buildAPI()
            req = factory.buildRequestOAuthTokenSwap('pin', pin)
            try:
                res = imgur.retrieveRaw(req)
            except urllib.request.HTTPError as e:
                print("Error %d\n%s" % (e.code, e.read().decode('utf8')))
                raise e
                
            print("Access Token: %s\nRefresh Token: %s\nExpires: %d seconds from now." % (
                res[1]['access_token'],
                res[1]['refresh_token'],
                res[1]['expires_in']
            ))
    if action == 'refresh':
        token = config['refresh_token']
        imgur = factory.buildAPI()
        req = factory.buildRequestOAuthRefresh(token)
        res = imgur.retrieveRaw(req)
        print('Access Token: %s\nRefresh Token: %s\nExpires: %d seconds from now.' % (
            res[1]['access_token'],
            res[1]['refresh_token'],
            res[1]['expires_in']
        ))

def createAccount(username, active):
    print("Creating account: " + username)

    collection = db.users

    address = generateAddress(username)

    user = {"username": username, "address": address, "active": active}

    collection.insert(user)

    return address

def generateAddress(username):
    return goat.getnewaddress(username)

def hasAccount(author):
    collection = db.users

    result = collection.find_one({"username": author})

    if result:
        return True
    else:
        return False

def comment(id):
    cid = id

    auth = factory.buildOAuth(config['access_token'], None, time+3600)
    imgur = factory.buildAPI(auth)
    req = factory.buildRequest(('comment/' + str(id),))
    comment = imgur.retrieve(req)

    author = comment['author']

    # Check if the person attempting to tip has a valid account.
    h = hasAccount(author)

    if h == False:
        return False

    message = comment['comment']

    # Attempt to calculate destination
    destination = False

    if comment['parent_id'] == 0:
        destination =  parent(comment['image_id'])

        if destination == None:
            return False
    else:
        destination = commentParent(comment['parent_id'])

    if destination == False:
        return False

    method = 'DOGE'

    # Attempt to calculate amount
    amount = False

    regex = re.search('\d+(\.\d+)?', message)

    if(regex):
        amount = regex.group(0)
    else:
        return False

    # Check if verification requested
    regex = re.search('VERIFY', message.upper())

    if(regex):
        verify = 1
    else:
        verify = 0

    # Check if destination exists
    user = hasAccount(destination)

    if user == True:
        address = getAddress(destination)
        exists = 1
    else:
        address = createAccount(destination, 0)
        exists = 0

    # Attempt to process tip
    tip(author, destination, method, amount, verify, exists, cid, comment['image_id'])

    return True

def getAddress(who):
    collection = db.users
    result = collection.find_one({"username": who})

    return result['address']

def tip(author, destination, method, amount, verify, exists, cid, iid):
    print("Trying to tip " + destination)

    if author == destination:
        message = "Nice try, but you can't tip yourself!"
    else:
        balance = getBalance(author)

        if balance >= float(amount):
            target = getAddress(destination)
            goat.sendfrom(author, target, float(amount))

            if exists == 0:
                message = "Hi " + destination + ",\n\n" + author + " has just sent you a " + str(amount) + " DOGE tip. Yay!\n\nAs this is your first tip, we've created an account for you (linked to your username). If you're new to Dogecoin, take a look at the following sub-reddit for more information.\n\nhttp://www.reddit.com/r/dogeducation\n\nAny concerns? Email tips@moolah.ch"
            else:
                message = "Hi " + destination + ",\n\n" + author + " has just sent you a " + str(amount) + " DOGE tip. Yay!\n\nYou can find out your current balance by sending us a simple 'info' message."

            auth = factory.buildOAuth(config['access_token'], None, time+3600)
            imgur = factory.buildAPI(auth)
            req = factory.buildRequest(('conversations/' + destination,), {
                'recipient': destination,
                'body': message
            })
            res = imgur.retrieve(req)

            balance = getBalance(author)

            message = "You have just sent a " + str(amount) + " DOGE tip to " + destination + ". Your new balance is " + str(balance) + " DOGE."

            auth = factory.buildOAuth(config['access_token'], None, time+3600)
            imgur = factory.buildAPI(auth)
            req = factory.buildRequest(('conversations/' + author,), {
                'recipient': destination,
                'body': message
            })
            res = imgur.retrieve(req)
        else:
            message = "Sorry, you don't have enough funds in your account for the " + str(amount) + " DOGE tip you just tried to send to " + destination + "."

            auth = factory.buildOAuth(config['access_token'], None, time+3600)
            imgur = factory.buildAPI(auth)
            req = factory.buildRequest(('conversations/' + author,), {
                'recipient': author,
                'body': message
            })
            res = imgur.retrieve(req)

def commentParent(id):
    auth = factory.buildOAuth(config['access_token'], None, time+3600)
    imgur = factory.buildAPI(auth)
    req = factory.buildRequest(('comment/' + str(id),))
    comment = imgur.retrieve(req)

    return comment['author']

def conversations():
    auth = factory.buildOAuth(config['access_token'], None, time+3600)
    imgur = factory.buildAPI(auth)
    req = factory.buildRequest(('conversations',))
    res = imgur.retrieve(req)
    
    if(res):
        for conversation in res:
            if conversation['with_account'] is not 'imgur':
                payload = 0

                action = False
                message = conversation['last_message_preview']

                regex = re.search('HELP', message.upper())

                if regex:
                    action = 'help'
                else:
                    regex = re.search('WITHDRAW', message.upper())

                    if regex:
                        action = 'withdraw'

                        auth = factory.buildOAuth(config['access_token'], None, time+3600)
                        req = factory.buildRequest(('conversations/' + str(conversation['id']) + '/',))
                        convo = imgur.retrieve(req)

                        regexAddress = re.compile(re.escape('withdraw '), re.IGNORECASE)
                        payload = regexAddress.sub('', convo['messages'][0]['body'])
                    else:
                        regex = re.search('REGISTER', message.upper())

                        if regex:
                            action = 'register'
                        else:
                            regex = re.search('INFO', message.upper())

                            if regex:
                                action = 'info'

                if action:
                    respond(action, conversation['with_account'], payload)

                req = factory.buildDeleteRequest(('conversations/' + str(conversation['id']),))
                res = imgur.retrieve(req)

def getBalance(who):
    return goat.getbalance(who)

def respond(action, who, payload):
    message = False

    if action == 'help':
        message = "register - register an account.\n\ninfo - retrieve your balance and deposit address.\n\nwithdraw <address> - withdraw to target address."
    elif action == 'info':
        h = hasAccount(who)

        if h == True:
            balance = getBalance(who)

            message = "Your current balances are as follows.\n\nDOGE: " + str(balance) + "\n\nYour deposit addresses are as follows.\n\nDOGE: " + getAddress(who)
        else:
            message = "Sorry, you don't appear to have an account with us. Send `register` to create one."
    elif action == 'register':
        message = register(who)
    elif action == 'withdraw':
        h = hasAccount(who)

        if h == True:
            balance = getBalance(who)
            amount = balance - 1
            amount = float(amount)

            goat.sendfrom(who, payload, amount)

            message = "You have withdrawn " + str(amount) + " DOGE to the following address.\n\n" + payload
        else:
            message = "Sorry, you don't appear to have an account with us. Send `register` to create one."

    if message:
        auth = factory.buildOAuth(config['access_token'], None, time+3600)
        imgur = factory.buildAPI(auth)
        req = factory.buildRequest(('conversations/' + who,), {
            'recipient': 'who',
            'body': message
        })
        res = imgur.retrieve(req)

def register(who):
    user = hasAccount(who)

    if user:
        return "You already have an account, you can't register again ;-)."
    else:
        address = createAccount(who, 1)

        return "Thank you for registering with Dogegive!\n\nYour deposit addresses are as follows, you can top up your account by sending funds to them.\n\nDOGE: " + str(address)

def notifications():
    auth = factory.buildOAuth(config['access_token'], None, time+3600)
    imgur = factory.buildAPI(auth)
    req = factory.buildRequest(('notification',))
    res = imgur.retrieve(req)

    for notification in res['messages']:
        if notification['content']['from'] == 'imgur':
            if notification['viewed'] == '0':
                message = notification['content']['last_message']

                regex = re.search('comment/[0-9]*', message)
                
                if(regex):
                    cid = regex.group()
                    cid = cid.replace('comment/', '')
                    comment(cid)
                    viewed(notification['id'])



def viewed(id):
    auth = factory.buildOAuth(config['access_token'], None, time+3600)
    imgur = factory.buildAPI(auth)
    req = factory.buildRequest(('notification/' + str(id),), {
        'viewed': 'yes'
    })
    res = imgur.retrieve(req)

    return True

def parent(id):
    auth = factory.buildOAuth(config['access_token'], None, time+3600)
    imgur = factory.buildAPI(auth)
    req = factory.buildRequest(('gallery/image/' + str(id),))
    image = imgur.retrieve(req)

    return image['account_url']

if __name__ == "__main__":
    boot()
