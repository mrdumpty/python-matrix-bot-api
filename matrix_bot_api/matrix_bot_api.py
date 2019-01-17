import traceback
import re
from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError


class MatrixBotAPI:

    # username          - Matrix username
    # password          - Matrix password
    # server            - Matrix server url : port
    # rooms             - List of rooms ids to operate in, or None to accept all rooms
    # accept_invites    - If true, accept invites to rooms
    def __init__(self, username, password, server, rooms=None, accept_invites=True):
        self.username = username

        # Authenticate with given credentials
        self.client = MatrixClient(server)
        try:
            self.client.login(username, password)
        except MatrixRequestError as e:
            print(e)
            if e.code == 403:
                print("Bad username/password")
        except Exception as e:
            print(e)

        # Store allowed rooms. If rooms is None, store empty list
        # of rooms and add all rooms we're currently in
        if rooms:
            self.rooms = rooms
        else:
            self.rooms = []
            for room in self.client.rooms.values():
                self.rooms.append(room)
        print('Total rooms: ', len(self.rooms))
        # Store empty list of handlers
        self.handlers = []

        # we should listen for invites and automatically accept them
        if accept_invites:
            self.client.add_invite_listener(self.handle_invite)

        # Add handlers for all rooms
        for room in self.rooms:
            room.add_listener(self.handle_message)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def handle_message(self, room, event):
        # Make sure we didn't send this message
        if re.match("@" + self.username, event['sender']):
            return

        # Loop through all installed handlers and see if they need to be called
        for handler in self.handlers:
            if handler.test_callback(event):
                # This handler needs to be called
                try:
                    handler.handle_callback(room, event)
                except:
                    traceback.print_exc()

    def handle_invite(self, room_id, state):
        print("Got invite to room: " + str(room_id))
        print("Joining...")
        room = self.client.join_room(room_id)

        # Add message callback for this room
        room.add_listener(self.handle_message)

        # Add room to list
        self.rooms.append(room)

    def send_message(self, message, room_id=None, room_alias=None):
        if not room_id:
            if not room_alias:  # send to all rooms if no room specified
                for room in self.rooms:
                    room.send_text(message)
                return True
            else:  # no ID but we have alias, so get room_id from it
                room_id = self.client.api.get_room_id(room_alias)
        room = self.client.rooms.get(room_id)
        if room and room in self.rooms:
            room.send_text(message)
            return True
        return False

    def start_polling(self):
        # Starts polling for messages
        self.client.start_listener_thread()
        return self.client.sync_thread
