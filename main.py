from dotenv import main
import os
from requests import post, get
import json
import urllib.parse
import datetime
from flask import Flask, redirect, request, jsonify, session
import flask

app = Flask(__name__)
main.load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
app.secret_key = os.getenv('SECRET_KEY')


@app.route('/')
def index():
    """Index page of app"""
    #return "See Spotify Data <a href='/login'> Login with Spotify </a>"
    return flask.render_template("index.html") 


@app.route('/login')
def login():
    """Login request"""
    scope = "user-read-recently-played user-top-read user-library-read user-read-private user-read-email user-follow-read"
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': 'http://localhost:3000/callback',
        'show_dialog': 'True'
    }

    auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Handle login response"""

    # if there is an error
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})

    if 'code' in request.args:
        body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:3000/callback',
            'client_id': client_id,
            'client_secret': client_secret
        }

        # get request
        url = "https://accounts.spotify.com/api/token"
        response = post(url, data=body)
        token_info = response.json()

        # store important info
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires'] = datetime.datetime.now().timestamp() + token_info['expires_in']
        print(session['access_token'])

        return redirect('/home')
    
@app.route('/home')
def home_page():
    """Landing page"""
     # error checking
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires']:
        return redirect('/refresh-token')
    print(session['access_token'])
    
    return flask.render_template("landing.html") 


@app.route('/playlists')
def get_playlists():
    """Get playlists"""

    # error checking
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    # url = "https://api.spotify.com/v1/me/playlists"

    response = get("https://api.spotify.com/v1/me/playlists", headers=headers)
    playlists = response.json()
    p = []
    for playlist in playlists['items']:
        p.append(playlist['name'])

    context = {"playlists": p}

    return flask.render_template("playlists.html", **context)

@app.route('/songs')
def get_songs():
    """Get top songs"""

    # error checking
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    # url = "https://api.spotify.com/v1/me/top/tracks"

    response = get("https://api.spotify.com/v1/me/top/tracks", headers=headers, timeout=10)
    data = response.json()
    print(data)
    names = [item["name"] + " by " + item["artists"][0]["name"] for item in data["items"]]
    
    context = {"songs": names}

    return flask.render_template("songs.html", **context)

@app.route('/artists')
def get_artists():
    """Get top artists"""

    # error checking
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = get("https://api.spotify.com/v1/me/top/artists", headers=headers, timeout=10)
    data = response.json()
    names = [item["name"] for item in data["items"]]
   
    context = {"artists": names}

    return flask.render_template("artists.html", **context)

@app.route('/recommendations')
def get_recommendations():
    """Get recommended songs"""

    # error checking
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    # get seed artist ids
    response = get("https://api.spotify.com/v1/me/top/artists?limit=5", headers=headers, timeout=10)
    data = response.json()
    ids = [item["id"] for item in data["items"]]
    artist_ids = ','.join(ids)
    print(artist_ids)

    # get recommendations with artist id as input
    response = get(f"https://api.spotify.com/v1/recommendations?seed_artists={artist_ids}", headers=headers, timeout=10)
    recommendations = response.json()

    names = []
    for track in recommendations['tracks']:
        # Extracting name and artist's name
        track_name = track["name"]
        artist_name = track["artists"][0]["name"]  

        # Append to the respective lists
        names.append(track_name + " by " + artist_name)

    context = {"recommendations": names}

    return flask.render_template("recommendations.html", **context)


@app.route('/refresh-token')
def refresh_token():
    """Refresh access token once it has expired"""

    # error checking
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires']:
        body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': client_id,
            'client_secret': client_secret
        }

        response = get("https://accounts.spotify.com/api/token", data=body)
        new_info = response.json()

        session['access_token'] = new_info['access_token']
        session['expires'] = datetime.datetime.now().timestamp() + new_info['expires_in']

        return redirect('/playlists')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=3000)
