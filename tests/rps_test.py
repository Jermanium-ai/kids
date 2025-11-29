import requests
import socketio
import time

# Create a room
resp = requests.post('http://127.0.0.1:5000/api/create-room')
room_id = resp.json()['room_id']
print('Created room', room_id)

client1 = socketio.Client()
client2 = socketio.Client()

player1 = None
player2 = None

@client1.on('connect')
def c1_connect():
    print('[c1] connect')

@client2.on('connect')
def c2_connect():
    print('[c2] connect')

@client1.on('join_room_response')
def j1(d):
    global player1
    player1 = d.get('player_id')
    print('[c1] join', player1)

@client2.on('join_room_response')
def j2(d):
    global player2
    player2 = d.get('player_id')
    print('[c2] join', player2)

@client1.on('game_started')
def gs1(d):
    print('[c1] game_started', d['game_type'])

@client2.on('game_started')
def gs2(d):
    print('[c2] game_started', d['game_type'])

@client1.on('move_made')
def mm1(d):
    print('[c1] move_made', d['player_id'])

@client2.on('move_made')
def mm2(d):
    print('[c2] move_made', d['player_id'])

client1.connect('http://127.0.0.1:5000')
client2.connect('http://127.0.0.1:5000')

client1.emit('join_room_request', {'room_id': room_id, 'display_name': 'A', 'avatar_color': '#111111'})
client2.emit('join_room_request', {'room_id': room_id, 'display_name': 'B', 'avatar_color': '#222222'})

# Wait
for _ in range(30):
    if player1 and player2:
        break
    time.sleep(0.2)

print('players', player1, player2)
client1.emit('start_game_request', {'room_id': room_id, 'game_type': 'rps', 'reset_scores': True})

# Round 1
client1.emit('game_move', {'room_id': room_id, 'move': {'choice': 'rock'}})
client2.emit('game_move', {'room_id': room_id, 'move': {'choice': 'scissors'}})

# Wait to resolve
time.sleep(0.5)

# Round 2 - race
client1.emit('game_move', {'room_id': room_id, 'move': {'choice': 'scissors'}})
# simulate a slight delay before second player
time.sleep(0.2)
client2.emit('game_move', {'room_id': room_id, 'move': {'choice': 'paper'}})

# Wait to resolve
time.sleep(0.5)

client1.disconnect()
client2.disconnect()
print('done')
