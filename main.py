from dotenv import load_dotenv
import os
import base64
from requests import post, get
import json
import http.client
import time
import random
from tqdm import tqdm

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

def get_token():
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def get_recco_header():
    payload = ''
    headers = {
        'Accept': 'application/json'
    }
    return payload, headers


def get_playlist_track_ids(token, playlist_id):
    headers = get_auth_header(token)
    offset = 0
    limit = 100
    track_ids = []
    while True:
        url= f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={offset}&limit={limit}"
        result = get(url, headers=headers)
        data = result.json()
        tracks_len = len(track_ids)

        items = data.get("items")
        for item in items:
            track_ids.append(item["track"]["id"])
        if len(track_ids) == tracks_len:
            break
        json_result = json.loads(result.content)

        offset += limit
    return track_ids


def get_track_id(token, track_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={track_name}&type=track&limit=1"
    
    query_url = url + query
    result = get(query_url, headers = headers)

    json_result = json.loads(result.content)["tracks"]["items"]
    return json_result[0]["id"]


def spo_to_recc(spo_id):
    conn = http.client.HTTPSConnection("api.reccobeats.com")
    payload, headers = get_recco_header()
    conn.request("GET", f"/v1/track?ids={spo_id}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = json.loads(data)['content'][0]['id']
    return result


def playlist_spo_to_recc(spo_playlist_track_ids):
    playlist_track_ids = []
    conn = http.client.HTTPSConnection("api.reccobeats.com")
    payload, headers = get_recco_header()
    i = 0
    print('Converting IDs...')
    for id in tqdm(spo_playlist_track_ids):
        conn.request("GET", f"/v1/track?ids={id}", payload, headers)
        res = conn.getresponse()
        data = res.read()
        result = json.loads(data).get('content',[])
        if result:
            playlist_track_ids.append(result[0]['id'])
        i+=1
        if (i-1)%100 == 0:
            time.sleep(15)
        time.sleep(0.01)
    return playlist_track_ids

def get_track_stats(track_id):
    conn = http.client.HTTPSConnection("api.reccobeats.com")
    payload, headers = get_recco_header()
    conn.request("GET", f"/v1/track/{track_id}/audio-features", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = json.loads(data)
    return result

def get_playlist_stats(playlist_track_ids):
    conn = http.client.HTTPSConnection("api.reccobeats.com")
    payload, headers = get_recco_header()
    playlist_stats = {'acousticness': 0,'danceability': 0, 'energy': 0, 'instrumentalness': 0, 'liveness': 0, 'loudness': 0, 'speechiness': 0, 'tempo': 0, 'valence': 0}
    i = 0
    print('Retrieving track data...')
    for item in tqdm(playlist_track_ids):
        conn.request("GET", f"/v1/track/{item}/audio-features", payload, headers)
        res = conn.getresponse()
        data = res.read()
        result = json.loads(data)
        for key in playlist_stats:
            playlist_stats[key] = (playlist_stats[key] + result[key]) 
        i+=1
        if (i-1)%100 == 0:
            time.sleep(15)
        time.sleep(0.01)
    for key in playlist_stats:
        playlist_stats[key] = (playlist_stats[key]/len(playlist_track_ids))
    return playlist_stats


def get_reco(track_stats, track_id):
    conn = http.client.HTTPSConnection("api.reccobeats.com")
    payload, headers = get_recco_header()
    conn.request("GET", f"/v1/track/recommendation?size=5&seeds={track_id}&acousticness={track_stats['acousticness']}&danceability={track_stats['danceability']}&energy={track_stats['energy']}&instrumentalness={track_stats['instrumentalness']}&liveness={track_stats['liveness']}&loudness={track_stats['loudness']}&speechiness={track_stats['speechiness']}&tempo={track_stats['tempo']}&valence={track_stats['valence']}", 
                 payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = json.loads(data)['content']
    return result


def main():
    token = get_token()
    while True:
        choice = input("\nSpotify Song Recommender"
                       "\n1) Get Recommendations From Song"
                       "\n2) Get Recommendations From Playlist" \
                       "\n3) Exit" \
                       "\nEnter Choice: ")
        if choice == "1":
            song = input("\nEnter name of song: ")
            spo_id = get_track_id(token, song)
            track_id = spo_to_recc(spo_id)
            stats = get_track_stats(track_id)
            reco = get_reco(stats, track_id)
            print('\nPrinting Recommendations:')
            for item in reco:
                print(f"{item['trackTitle']} by {item['artists'][0]['name']}")
        elif choice == "2":
            playlist_id = input("\nInput playlist id: ")
            spo_playlist_track_ids = get_playlist_track_ids(token, playlist_id)
            playlist_track_ids = playlist_spo_to_recc(spo_playlist_track_ids)
            playlist_stats = get_playlist_stats(playlist_track_ids)
            playlist_reco = get_reco(playlist_stats, random.choice(playlist_track_ids))
            print('\nPrinting Recommendations:')
            for item in playlist_reco:
                print(f"{item['trackTitle']} by {item['artists'][0]['name']}")
        elif choice == "3":
            break
        else:
            print("Invalid option")
    print("\nGoodbye")


if __name__ == "__main__":
    main()

