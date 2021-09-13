from thespian.actors import Actor, ActorSystem, ActorExitRequest, ChildActorExited
import threading


class Hello(Actor):
    def __init__(self):
        self.zzz = None

    def receiveMessage(self, msg, sender):
        if isinstance(msg, dict):
            #print(msg.keys())
            if 'die' in msg:
                #raise NotImplementedError()
                pass
            if 'szzz' in msg:
                self.zzz = msg['szzz']
                return
            if 'gzzz' in msg:
                self.send(sender,self.zzz)
                return
                
        
        self.send(sender, 'Hello, World!')

class DLH(Actor):
    def __init__(self):
        super().__init__()
        
                
    def receiveMessage(self, msg, sender):
        #print(msg)
        if isinstance(msg, dict):
            if 'hdl' in msg:
                self.handleDeadLetters(msg['hdl'])
                return
            if 'new' in msg:
                self.hello = self.createActor(Hello)
                self.send(sender,self.hello)
                return
        if isinstance(msg, ChildActorExited):
            print(msg.childAddress)
            return
        
        print("Got Dead Letter from {}: {}".format(sender,msg))
        

if __name__ == "__main__":
    hello = ActorSystem().createActor(Hello)
    dlh = ActorSystem().createActor(DLH)
    hello2 = ActorSystem().ask(dlh,{'new':True})
    print(ActorSystem().ask(hello2,{'gzzz':True}))
    print(ActorSystem().tell(hello2,{'szzz':'123'}))
    print(ActorSystem().ask(hello2,{'gzzz':True}))
    ActorSystem().tell(hello2,{'die':True})
    print(ActorSystem().ask(hello2,{'gzzz':True}))
    ActorSystem().tell(hello2,ActorExitRequest())
    