#!/usr/bin/env python3

import socket
import os
import argparse
from threading import Thread
from gpiozero import PWMLED
from daemonize import Daemonize
from time import sleep
from dotenv import load_dotenv

pid = "/tmp/.rgbled-controller.pid"

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--address", help="Specify address used for daemon process, falls back to .env file, defaults to 127.0.0.1", action="store")
parser.add_argument("-p", "--port", help="Specify port used for daemon process, falls back to .env file, defaults to 5807", action="store", type=int)
parser.add_argument("-f", "--foreground", help="Runs application in foreground for debugging", action="store_true")

args = parser.parse_args()
load_dotenv()

# Load address and port from argument, if that fails, .env, if that fails, fall back to 127.0.0.1
if args.address is not None:
	address = args.address
else:
	address = os.getenv('LISTEN_ADDRESS')
	if address is None:
		address = '127.0.0.1'

if args.port is not None:
	port = args.port
else:
	port = int(os.getenv('LISTEN_PORT'))
	if port is None:
		port = 5807

# Function which sets the LED strips according to a given hex colour
def set(hex):
	hex = hex.lstrip('#')
	length = len(hex)
	rgbv = tuple(int(hex[i:i + length // 3], 16) for i in range(0, length, length // 3))
	r.value = rgbv[0]/255
	g.value = rgbv[1]/255
	b.value = rgbv[2]/255

# Function to strobe colours, calls on the set function to apply them
def strobe(instructions):
	while True:
		for colour in instructions[2:]:
			set(colour)
			sleep(float(instructions[1]))
			if stopthread is True:
				return

def main():
	# Set r, g and b as global variables and define them
	# I had to define them here because of a weird quirk in the Daemonize library, this was a headache
	global r
	global g
	global b
	r = PWMLED(os.getenv('GPIO_RED'))
	g = PWMLED(os.getenv('GPIO_GREEN'))
	b = PWMLED(os.getenv('GPIO_BLUE'))
	
	# Define UDP socket and bind to it
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind((address, port))

	# Create variable which is checked by threads to see if they should stop
	global stopthread

	# Continue listening for input
	while True:
		data, addr = sock.recvfrom(1024)
		instructions = data.decode('ascii').split(",")
		print(instructions)

		if 'cthread' in locals():
			stopthread = True
			cthread.join()
		if instructions[0] == 'single':
			set(instructions[1])
		if instructions[0] == 'strobe':
			stopthread = False
			cthread = Thread(target=strobe, args=(instructions,))
			cthread.start()

if args.foreground:
	main()

# Start the daemon process
daemon = Daemonize(app="rgbled-controller", pid=pid, action=main)
daemon.start()