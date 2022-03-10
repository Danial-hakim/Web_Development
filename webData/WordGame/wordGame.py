from os import name
from flask import Flask, request, render_template , redirect , session
from flask_session import Session

from datetime import date, datetime, timedelta 
import random
import requests

import socket

from collections import Counter

from werkzeug.user_agent import UserAgent

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

import DBcm

config = {
    'host': '127.0.0.1',
    'database': 'leaderboardDB',
    'user': 'leaderuser',
    'password': 'leaderpasswd',
}

@app.route("/")
@app.route("/home")
def index():
    return render_template("home.html", the_title="Welcome")

@app.route("/game")
def game():
    sourceWord = random.choice(open("big.txt").read().split())
    session["sourceWord"] = sourceWord
    startTime = datetime.now()
    session["startTime"] = startTime
    return render_template("game.html", the_tile="Game", sourceWord = sourceWord, startTime = startTime)

@app.post("/gameWon")

def processWords():
    result = True
    smallWordList = []

    with open("small.txt") as sf:
        for words in sf:
            words = words.strip("\n").lower()
            smallWordList.append(words)

    guesses = request.form['test']
    session["guesses"] = guesses
    sourceWord = session.get("sourceWord")
    sourceWord = sourceWord.lower()
    guesses = guesses.lower()
    guesses = guesses.split(" ")
    
    invalidWords = []
    invalidLetters = []

    invalidWords = isWordsValid(guesses , smallWordList)
    session["invalidWords"] = invalidWords
    invalidLetters = isWordFromSource(guesses,sourceWord)
    session["invalidLetters"] = invalidLetters
    isSource = isPlayerUsingSourceWord(guesses,sourceWord)
    session["isSource"] = isSource
    isDups = isThereDuplicates(guesses)
    session["isDups"] = isDups
    smallWord = wordMoreThanFour(guesses)
    session["smallWord"] = smallWord

    result1 = session.get("shortWord")
    result2 = session.get("validWord")
    result3 = session.get("fromSource")
    result4 = session.get("noDuplicates")
    result5 = session.get("notSource")

    option = ["",""]
    
    if result1 and result2 and result3 and result4 and result5 == True:
        result = True
        option[0] = "none" 
        option[1] = "block"
        session["option"] = option

    else:
        result = False
        option[0] = "block"
        option[1] = "none"
        session["option"] = option

    print (option[0])
    print (option[1])

    session["result"] = result

    startTime = session.get("startTime")
    finishedTime = datetime.now()
    timeTaken = finishedTime - startTime
    timeTaken = timeTaken.total_seconds()
    session["timeTaken"] = timeTaken

    insertToLog()
    
    return render_template("gameWon.html", the_title="Game finished",sourceWord = sourceWord,
    guesses = guesses,invalidWords = invalidWords,invalidLetters = invalidLetters,isSource = isSource,
    isDups = isDups, smallWord = smallWord , option = option , timeTaken = timeTaken)

def wordMoreThanFour(guesses):
    for words in guesses:
        if len(words) < 4:
            result = False
            session["shortWord"] = result
            return ("Word is too small")    
        else:    
            result = True
            session["shortWord"] = result
            return ""

def isWordsValid(guesses , smallTextList):
    
    notRealWords = []
    for words in guesses:
        if words in smallTextList:
            continue
        else:
            notRealWords.append(words)

    if not notRealWords:
        result = True
    else:
        result = False

    session["validWord"] = result

    return notRealWords

def isWordFromSource(guesses , sourceWord):
    
    sourceWordCounter = Counter(sourceWord)
    listOfCounter = []
    notFromSource = []

    for words in guesses:
        listOfCounter.append(Counter(words))

    for current in listOfCounter:
        for letter in current:
            if current[letter] > sourceWordCounter[letter]:
                notFromSource.append(letter)
            else:
                continue
    
    if not notFromSource:
        result = True
    else:
        result = False

    session["fromSource"] = result
    return notFromSource

def isThereDuplicates(values):
    
    if len(values) != len(set(values)): #if true , means there is duplicates
        result = False
        session["noDuplicates"] = result
        return "There is duplicates in your guesses"
    else:
        result = True
        session["noDuplicates"] = result
        return ""
    
def isPlayerUsingSourceWord(guesses,sourceWord):
    for words in guesses:
        if words == sourceWord:
            result = False
            session["notSource"] = result
            return "You cannot use the sourceword"
        else:
            result = True
            session["notSource"] = result
            return ""

def insertToDatabase():  
    timeTaken = session.get("timeTaken")
    sourceWord = session.get("sourceWord")
    guesses = session.get("guesses")
    name = request.form['name']

    SQL = """
        insert into leaderboard (time_taken, name, source,matches) values ( %s, %s, %s, %s)
    """
    with DBcm.UseDatabase(config) as db:
        db.execute(SQL, (timeTaken,name,sourceWord,guesses))

def showLeaderbord():
    with DBcm.UseDatabase(config) as db:
        SQL = """
            select * from leaderboard order by time_taken
        """
        db.execute(SQL)

        data = db.fetchall()

        if len(data) < 10:
            data.append([])

    return data[:10]        

def insertToLog():
    result = session.get("result")
    if result == False:
        succeed = "Fail"
    else:
        succeed = "Pass"

    sourceWord = session.get("sourceWord")
    guesses = session.get("guesses")
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    browser = request.headers.get('User-Agent')

    SQL = """
        insert into log (result, source, matches, ip, browser) 
        values ( %s, %s, %s, %s, %s)
    """
    with DBcm.UseDatabase(config) as db:
        db.execute(SQL, (succeed,sourceWord,guesses,ip,browser))

def showLog():
    with DBcm.UseDatabase(config) as db:
        SQL = """
            select * from log
        """
        db.execute(SQL)

        data = db.fetchall()

    return data 


@app.post("/leaderboard")
def loadLeaderboard():
    top10 = []

    insertToDatabase()
    top10 = showLeaderbord()

    return render_template("leaderboard.html", the_title="Congratulations", top10 = top10)

@app.route("/log")
def log():
    logs = []
    logs = showLog()

    logsLine = ""
    for x in logs:
        logsLine += x[0] + "||" + x[1] + "||" + x[2] + "||" + str(x[3]) + "||" + x[4] + "||" + x[5] + "<br>" + "=========================================================================================================" + "<br>"

    return render_template("log.html", the_title="logs", logsLine = logsLine)


if __name__ == "__main__":
    app.run(debug=True)

