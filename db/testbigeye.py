
import zmq

context = zmq.Context()

sock = context.socket(zmq.PUB)
sock.bind('tcp://127.0.0.1:6666')

def fake_ganeti(message):	
	sock.send(message)