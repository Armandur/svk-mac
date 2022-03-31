#!/usr/bin/env python3
# Author: Rasmus Pettersson Vik
# Version: 1.0.2

import requests
import sys
import getopt
from enum import Enum
from bs4 import BeautifulSoup


# Viewstate and validation updates on every page, need to get them from the GET-html
def findEventValidationViewstate(html):
	soup = BeautifulSoup(html, "html.parser")
	validation = soup.find(id='__EVENTVALIDATION').attrs['value']
	viewstate = soup.find(id='__VIEWSTATE').attrs['value']
	viewstategen = soup.find(id='__VIEWSTATEGENERATOR').attrs['value']
	return {"validation": validation, "viewstate": viewstate, "viewstategen": viewstategen}


def login(session, credentials):
	url = "http://bestallningsportal.system.svenskakyrkan.se/Inloggning.aspx"
	req = session.get(url)
	html = req.text  # Get the initial page to get viewstate and other aspx
	if req.status_code >= 400: #Check if page errored, most likely not connected to KNET
		print(f"Error {req.status_code}, connected to KNET?")
		exit(1)

	aspx = findEventValidationViewstate(html)
	data = {
		"__EVENTVALIDATION": aspx["validation"],
		"__VIEWSTATEGENERATOR": aspx["viewstategen"],
		"__VIEWSTATE": aspx["viewstate"],
		"ctl00$cph1$ctrlInloggningView$txtUsername": credentials["username"],
		"ctl00$cph1$ctrlInloggningView$txtPassword": credentials["password"],
		"ctl00$cph1$ctrlInloggningView$u2.x": "0",
		"ctl00$cph1$ctrlInloggningView$u2.y": "0"
	}

	req = session.post(url, data=data)
	html = req.text

	if html.find("Du har inga rättigheter till detta system") != -1:
		print("Login failed, check access and credentials")
		exit(1)

	#TODO Add support for choosing between multiple economic units.


def logout(session):
	#TODO implement
	#Navigate to http://bestallningsportal.system.svenskakyrkan.se/Bestallning.aspx and press "Logga ut"
	url = "http://bestallningsportal.system.svenskakyrkan.se/Bestallning.aspx"
	navigate(session, url)
	return


def navigate(session, url):
	html = session.get(url).text
	#print(f"Now at {url}")
	# print(html)
	return findEventValidationViewstate(html), html


def getCompanyName(html):
	soup = BeautifulSoup(html, "html.parser")
	company = soup.find(id='cph1_ctrlMacCreateView_txtCompany').attrs['value']
	return company


class Type(Enum):
	LAPTOP = 0
	PHONE = 1
	TABLET = 2
	OTHER = 3


def registerMAC(session, mac, name, type):
	url = "http://bestallningsportal.system.svenskakyrkan.se/MacSkapa.aspx"
	aspx, html = navigate(session, url)
	company = getCompanyName(html)

	headers = {
		"Cache-Control": "no-cache",
		"Accept": "*/*",
		"Accept-Encoding": "gzip, deflate",
		"Accept-Language": "sv,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55",
		"X-Requested-With": "XMLHttpRequest",
		"Content-Length": "2000",
		"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
		"Origin": "http://bestallningsportal.system.svenskakyrkan.se",
		"Referer": "http://bestallningsportal.system.svenskakyrkan.se/MacSkapa.aspx",
		"X-MicrosoftAjax": "Delta=true"
	}

	data = {
		"ctl00$cph1$ctrlMacCreateView$MainScriptManager": "ctl00$cph1$ctrlMacCreateView$pnlGastnatCreate|ctl00$cph1$ctrlMacCreateView$btnCreate",
		"__LASTFOCUS": "",
		"__EVENTTARGET": "",
		"__EVENTARGUMENT": "",
		"__VIEWSTATE": aspx["viewstate"],
		"__VIEWSTATEGENERATOR": aspx["viewstategen"],
		"__EVENTVALIDATION": aspx["validation"],
		"ctl00$cph1$ctrlMacCreateView$ctrlLoggedInBarView$lstSmartpasskonto": "11111111-1111-1111-1111-111111111111",
		"ctl00$cph1$ctrlMacCreateView$txtMacadress": mac,
		"ctl00$cph1$ctrlMacCreateView$txtPerson": name,
		"ctl00$cph1$ctrlMacCreateView$txtEmail": "",
		"ctl00$cph1$ctrlMacCreateView$txtCompany": company,
		"ctl00$cph1$ctrlMacCreateView$txtPhone": "",
		"ctl00$cph1$ctrlMacCreateView$ddlMobilTyp": type.value,
		"__ASYNCPOST": "true",
		"ctl00$cph1$ctrlMacCreateView$btnCreate": "Skapa användare"
	}

	req = session.post(url, data=data, headers=headers)

	#TODO Add check to see if registering fails due to MAC already existing, check the req.text for error message?


def verifyMACExists(session, mac):
	url = "http://bestallningsportal.system.svenskakyrkan.se/GastnatLista.aspx"
	aspx, html = navigate(session, url)
	mac = mac.lower()
	return bool((html.find(mac))) #TODO Improve this to return info on line about the registered device (name, type, last used etc)


def main(argv):
	usage = "svk-mac.py -u <username> -p <password> -m <mac-address> -n <name> -t <LAPTOP/PHONE/TABLET/OTHER> -i/--input <list-of-mac-adresses.txt>, --check <checks if MAC in -m exists>"

	if len(argv) == 0:
		print("No parameters given")
		print(usage)
		exit(1)

	credentials = {
		"username": "",
		"password": ""
	}

	mac = ""
	name = ""
	device = Type.OTHER
	inputFile = ""

	operation = "register"
	multiple = False

	try:
		opts, args = getopt.getopt(argv, "hu:p:m:n:t:i:", ["input=", "check"])
	except getopt.GetoptError:
		print(usage)
		exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print(usage)
			exit(2)

		elif opt == "-u":
			credentials["username"] = arg

		elif opt == "-p":
			credentials["password"] = arg

		elif opt == "-m":
			mac = arg

		elif opt == "-n":
			name = arg

		elif opt == "-t":
			if arg in ("LAPTOP", "PHONE", "TABLET", "OTHER"):
				device = Type[arg]
			else:
				print(f"Wrong type: {arg}")
				exit(1)

		elif opt in ("-i", "--input"):
			inputFile = arg
			multiple = True

		elif opt == "--check":
			operation = "check"

		else:
			print(f"Illegal option: {opt} : {arg}")
			print(usage)
			exit(1)

	sess = requests.Session()
	login(sess, credentials)
	
	if operation == "register":
		registerMAC(sess, mac, name, device)
		print(f"{name} {mac} {device} registered: {verifyMACExists(sess, mac)}")
		exit(0)
	
	elif operation == "check":
		print(f"MAC {mac} registered: {verifyMACExists(sess, mac)}")
		exit(0)
	
	elif operation == "register" and multiple:
		#MAC	NAME	TYPE
		with open(inputFile, 'r') as file:
			for line in file:
				split = line.strip().split('\t')
				mac = split[0]
				name = split[1]
				device = Type[split[2]]
				registerMAC(sess, mac, name, device)
				print(f"{name} {mac} {device} registered: {verifyMACExists(sess, mac)}")
	
	elif operation == "check" and multiple:
		#MAC	(NAME	TYPE)
		with open(inputFile, 'r') as file:
			for line in file:
				split = line.strip().split('\t')
				mac = split[0]
				print(f"MAC {mac} registered: {verifyMACExists(sess, mac)}")


if __name__ == '__main__':
	main(sys.argv[1:])

