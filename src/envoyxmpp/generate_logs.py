#!/usr/bin/env python

import logging, oursql, json, os

def get_relative_path(path):
        my_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(my_path, path))

def write_line(logfile, line, timestamp):
        f = open("logs/%s.log" % logfile, "a")
        f.write("[%s] %s\n" % (timestamp.isoformat(), line))
        f.close()
        
def try_create_userdir(user):
        try:
                os.mkdir("logs/%s" % user)
        except OSError, e:
                pass
        
def add_presence(user, room):
        try:
                presences[user].append(room)
        except KeyError, e:
                presences[user] = [room]
                
def remove_presence(user, room):
        try:
                presences[user] = [x for x in presences[user] if x != room]
        except KeyError, e:
                pass  # Quietly ignore, for now

try:
        os.mkdir("logs" % user)
except OSError, e:
        pass

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

configuration = json.load(open(get_relative_path("../config.json"), "r"))

db = oursql.connect(host=configuration['database']['hostname'], user=configuration['database']['username'], 
                    passwd=configuration['database']['password'], db=configuration['database']['database'],
                    autoreconnect=True)

cursor = db.cursor()
cursor.execute("SELECT `Id`, `Type`, `Sender`, `Recipient`, `Date`, `Event` AS `Payload`, `Extra`, 1 AS `IsEvent` FROM log_events \
                UNION SELECT `Id`, `Type`, `Sender`, `Recipient`, `Date`, `Message` AS `Payload`, '' AS `Extra`, 0 AS `IsEvent` FROM log_messages \
                ORDER BY `Date` ASC;")
                
status_names = {
        1: "Available",
        2: "Away",
        3: "Extended away",
        4: "Do not disturb",
        5: "Chatty"
}

presences = {}
                
for row in cursor:
        sender = row[2].split("/", 1)[0]
        recipient = row[3].split("/", 1)[0]
        
        if row[1] == 1:
                # Group message
                write_line(recipient, "<%s> %s" % (sender, row[5]), row[4])
        elif row[1] == 2:
                # Private message
                try_create_userdir(sender)
                try_create_userdir(recipient)
                write_line("%s/%s" % (sender, recipient), "<%s> %s" % (sender, row[5]), row[4])
                write_line("%s/%s" % (recipient, sender), "<%s> %s" % (sender, row[5]), row[4])
        elif row[1] == 5:
                # Topic change
                write_line(recipient, "* %s changed the topic to '%s'" % (sender, row[5]), row[4])
        elif row[1] == 3:
                # Status
                if row[6] != "":
                        msg = "*** %s just changed their status to %s (%s)." % (sender, status_names[int(row[5])], row[6])
                else:
                        msg = "*** %s just changed their status to %s." % (sender, status_names[int(row[5])])
                        
                write_line(sender, msg, row[4])
                try:
                        for presence in presences[sender]:
                                write_line(presence, msg, row[4])
                except KeyError, e:
                        pass
        elif row[1] == 4:
                # Presence
                if int(row[5]) == 1:
                        # Login
                        write_line(sender, "*** %s just logged in." % sender, row[4])
                elif int(row[5]) == 2:
                        # Disconnect
                        write_line(sender, "*** %s just disconnected." % sender, row[4])
                        try:
                                for presence in presences[sender]:
                                        write_line(presence, "*** %s just disconnected." % sender, row[4])
                                        remove_presence(sender, presence)
                        except KeyError, e:
                                pass
                elif int(row[5]) == 3:
                        # Join room
                        write_line(recipient, "*** %s joined." % sender, row[4])
                        add_presence(sender, recipient)
                elif int(row[5]) == 4:
                        # Leave room
                        write_line(recipient, "*** %s left." % sender, row[4])
                        remove_presence(sender, recipient)
