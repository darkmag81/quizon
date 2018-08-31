from os.path import exists
from functools import wraps
from flask import Flask, redirect, jsonify, render_template, request, flash, url_for
import jwt
import os
import json
import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'superpassword1'
app.secret_key = 'some_secret'
riddles_data = []

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')

        if not token:
            return jsonify({'message': 'Token is missing'}), 403
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
        except:
            return jsonify({'message':'Token is invalid'}), 403
        return f(*args, **kwargs)
    return decorated


def create_player_data_file():
    if not exists("data/player_data.json"):
        player_data_default = [{
        "username": "dummy",
        "password": "password",
        "score": 3,
        "game_status": "ingame",
        "current_round": 3,
        "tries": 1,
        "games_played": 2,
        "best_score": 10,
        "bad_answer" : "nothing"   
        }]
        with open('data/player_data.json', 'w') as player_file:
            json.dump(player_data_default, player_file)

"""
Save <data> to <filename>
"""
def saveToFile(filename, data):
    with open(filename, "a") as file:
        file.writelines(data)
        
"""
Check if highscore file exists, if not create dummy JSON file
"""
def initialFileCheck():
    if not exists("data/highscore.json"):
        saveToFile("data/highscore.json", '[{"score":0,"name":"Dummy"}]')
    if not exists("data/score.json"):
        saveToFile("data/score.json", '[{"player":"Dummy", "score":0}]')
"""
Load highscore list from JSON file
"""
def load_highscore():
    with open("data/highscore.json", "r") as high_score_file:
        high_score = json.load(high_score_file)
    high_score_file.close()
    return high_score

"""
Add any bad answer to file "badanswers.txt" and update player log "<player>.txt"
with bad answers
"""
def addBadAnswers(username, message, index, lives):
    if not message:
        answer = "No answer"
    else:
        answer = message
    message_to_save = "Riddle " + str(index +1) + ", tries left " + str(lives) + ": " + answer + "\n"
    saveToFile("data/badanswers.txt", "({0}) - {1}".format(username.title(), answer + "\n"))
    file_name = "data/" + username + ".txt"
    saveToFile(file_name, message_to_save)

"""
Check if player score is higher than any score on current table,
if yes then add player score to list, sort list and cut down to 5 elements
"""
def highscoreUpdate(score, username, high_score):
    for x in range (0,len(high_score)):
        if score > int(high_score[x]["score"]):
            newRecord = {"name": username, "score": score}
            high_score.append(newRecord)
            break
    sorted_high_score = sorted(high_score, key=lambda k: k['score'], reverse=True)
    while len(sorted_high_score) > 5:
        del sorted_high_score[5]
    with open('data/highscore.json', 'w') as outfile:
        json.dump(sorted_high_score, outfile)
    outfile.close()
    with open("data/score.json", "r") as all_scores_file:
        all_scores = json.load(all_scores_file)
    all_scores_file.close()
    new_score_save = {"player": username, "score": score}
    all_scores.append(new_score_save)
    with open('data/score.json', 'w') as score_file:
        json.dump(all_scores, score_file)
    score_file.close()
    
@app.route('/', methods=["GET", "POST"])
def index():
    create_player_data_file()
    initialFileCheck()
    high_score = load_highscore()
    with open("data/player_data.json", "r") as player_file:
        player_data = json.load(player_file)
    player_file.close()
    return render_template("index.html", page_title='Main Page', high_score=high_score, players_registered=len(player_data))

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form['username'] == '':
            redirect(url_for('.login'))
        username = request.form['username']
        return redirect(url_for('.playermenu', username=username))
    return render_template("login.html", page_title='Sign In')

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        return 'registering'
    
    return render_template("register.html", page_title='Register')

@app.route('/<username>', methods=["GET", "POST"])
def playermenu(username):
    with open("data/player_data.json", "r") as player_file:
        player_data = json.load(player_file)
    player_file.close()
    with open("data/riddles.json", "r") as json_data:
        riddles_data = json.load(json_data)
    json_data.close()
    return render_template('player.html', username=username, players_registered=len(player_data), questions=len(riddles_data))


@app.route('/<username>/highscore', methods=["GET", "POST"])
def highscore(username):
    high_score = load_highscore()
    return render_template("highscore.html", high_score=high_score, username=username)


@app.route('/<username>/play', methods=["GET", "POST"])
def user(username):
    initialFileCheck()
    high_score = load_highscore()
    element_wrong_answer_text = ''
    riddles_data = []
    riddle_index = 0
    score = 0
    tries = 1
    with open("data/riddles.json", "r") as json_data:
        riddles_data = json.load(json_data)
    sorted_high_score = sorted(high_score, key=lambda k: k['score'], reverse=True)
    while len(sorted_high_score) > 5:
        del sorted_high_score[5]
    with open('data/highscore.json', 'w') as outfile:
        json.dump(sorted_high_score, outfile)
    if request.method == "POST":
        riddle_index = int(request.form["riddle_index"])                    # get index
        score = int(request.form["score"])                      # get score
        tries = int(request.form["tries"])                      # get remaining tries
        player_response = request.form["message"].lower()          # make answer lowercase
        if riddles_data[riddle_index]["answer"] == player_response:              # correct answer
            riddle_index += 1
            score += 1
            tries = 1
            element_wrong_answer_text = ''
            if riddle_index >= len(riddles_data):                             # if answered last riddle go to end.html
                file_name = "data/" + username + ".txt"
                saveToFile(file_name, "***\nScore: " + str(score) + "\n***")
                highscoreUpdate(score, username, high_score)
                high_score = load_highscore()
                return redirect("/" + username + "/endgame")
        else:                                                   # wrong answer
            addBadAnswers(username, player_response, riddle_index, tries)# add wrong answer to file
            if tries >= 1:                                      # if there is one or  more tries available
                tries -= 1
                element_wrong_answer_text = '"' + player_response + '" is wrong! Please try one more time...'
                return render_template("riddle.html", username=username, 
                       riddles_data=riddles_data, riddle_index=riddle_index, 
                       element_wrong_answer_text=element_wrong_answer_text, 
                       score=score, tries=tries)
            if tries == 0:                                      # if there is no more tries left
                if riddle_index == len(riddles_data)-1:                       # check if last riddle
                    file_name = "data/" + username + ".txt"
                    saveToFile(file_name, "***\nScore: " + str(score) + "\n***")
                    highscoreUpdate(score, username, high_score)
                    high_score = load_highscore()
                    return redirect("/" + username + "/endgame")
                if riddle_index < len(riddles_data):                          # if not last riddle
                    riddle_index += 1
                    tries = 1
                    return render_template("riddle.html", riddle_index=riddle_index, 
                           element_wrong_answer_text=element_wrong_answer_text, 
                           score=score, tries=tries, riddles_data=riddles_data,
                           username=username)
        
    
    return render_template("riddle.html",  
        riddle_index=riddle_index, element_wrong_answer_text=element_wrong_answer_text, 
        score=score, tries=tries, riddles_data=riddles_data, username=username)


@app.route('/<username>/endgame', methods=["GET", "POST"])
def end_game(username):
    high_score = load_highscore()
    with open("data/score.json", "r") as all_scores_file:
        all_scores = json.load(all_scores_file)
    for x in range (0,len(all_scores)):
        if username == all_scores[x]["player"]:
            score = int(all_scores[x]["score"])
    if request.method == "POST":
        return redirect(request.form["username"])
    return render_template("end.html", high_score=high_score, username=username, score=score)


@app.route('/<username>/logoff', methods=["GET", "POST"])
def logoff(username):
    return redirect(url_for('index'))
   
   
if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
    port=int(os.environ.get('PORT')),
    debug=True)