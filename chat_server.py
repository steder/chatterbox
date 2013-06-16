import json
import random
import sys

from autobahn.websocket import WebSocketServerFactory
from autobahn.websocket import WebSocketServerProtocol
from autobahn.websocket import listenWS
from twisted.internet import reactor
from twisted.python import log


MESSAGE_TYPE_CHAT = 1
MESSAGE_TYPE_JOIN = 2
MESSAGE_TYPE_PART = 3
MESSAGE_TYPE_USERLIST = 4


class BroadcastServerProtocol(WebSocketServerProtocol):
    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, msg, binary):
        if not binary:
            data = json.loads(msg)
            msg_type = data.get("type", MESSAGE_TYPE_CHAT)
            if msg_type == MESSAGE_TYPE_JOIN:
                response = json.dumps({"nickname": data["nickname"],
                                       "userid": self.peerstr,
                                       "type": MESSAGE_TYPE_JOIN})
                self.nickname = data["nickname"]
                self.factory.broadcast(response)
            elif msg_type == MESSAGE_TYPE_USERLIST:
                # TODO: cache this userlist on the factory, build on demand,
                # invalidate the cache when users join or leave.
                userList = {"type": MESSAGE_TYPE_USERLIST,
                            "users": []}
                for client in self.factory.clients:
                    userList["users"].append({"nickname": client.nickname,
                                              "userid": client.peerstr,
                                              })
                self.sendMessage(json.dumps(userList))
            else:
                message = data["message"]
                if message.startswith("/d6"):
                    response = json.dumps({"nickname": "DM",
                                           "ip": self.peerstr,
                                           "message": "%s rolled a d6 and got %s"%(data["nickname"], random.randint(1, 6))})
                    self.factory.broadcast(response)
                elif message.startswith("/"):
                    response = json.dumps({"nickname": "Computer",
                                           "ip": self.peerstr,
                                           "message": "I don't understand your command: %s"%(message,),
                                           })
                    self.sendMessage(response)
                else:
                    print "%s (%s): %s" % (data["nickname"], self.peerstr, data["message"])
                    response = json.dumps({"nickname": data["nickname"],
                                           "ip": self.peerstr,
                                           "message": data["message"]})
                    self.factory.broadcast(response)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):

    protocol = BroadcastServerProtocol

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []
        self.tickcount = 0
        self.tick()

    def tick(self):
        self.tickcount += 1
        self.broadcast("tick %d" % self.tickcount)
        reactor.callLater(60, self.tick)

    def register(self, client):
        if not client in self.clients:
            print "registered client " + client.peerstr
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print "unregistered client " + client.peerstr
            self.clients.remove(client)
            partMessage = json.dumps({"userid": client.peerstr,
                                      "type": MESSAGE_TYPE_PART})
            self.broadcast(partMessage)

    def broadcast(self, msg):
        print "broadcasting message '%s' .." % (msg,)
        for c in self.clients:
            print "sending to %s... " % (c.peerstr,)
            c.sendMessage(msg.encode("utf-8"))


if __name__ == '__main__':
    log.startLogging(sys.stdout)
    factory = BroadcastServerFactory("ws://localhost:9000")
    listenWS(factory)
    reactor.run()
