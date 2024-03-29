#!/usr/bin/env python3
# Author: Rasmus Pettersson Vik
# Version: 1.2.0

import requests
import sys
from sys import exit
import getopt
from enum import Enum
from bs4 import BeautifulSoup


# Viewstate and validation updates on every page, need to get them from the GET-html
def findEventValidationViewstate(html):
	soup = BeautifulSoup(html, "html.parser")
	validation = ""
	viewstate = ""
	viewstategen = ""
	try: #For findUnits and logging out there will be no validation, viewstate etc so we just try to set them
		validation = soup.find(id='__EVENTVALIDATION').attrs['value']
		viewstate = soup.find(id='__VIEWSTATE').attrs['value']
		viewstategen = soup.find(id='__VIEWSTATEGENERATOR').attrs['value']
	finally:
		return {"validation": validation, "viewstate": viewstate, "viewstategen": viewstategen}


def getSingleEconomicUnit(html):
	soup = BeautifulSoup(html, "html.parser")
	unit = soup.find(id='cph1_ctrlViewsBestallningView_ctrlLoggedInBarView_lblEnhet').contents[0].strip()
	return unit


def getMultipleEconomicUnits(html):
	soup = BeautifulSoup(html, "html.parser")
	options = soup.find_all("option")
	units = []
	for option in options:
		if option.attrs['value'] != "00000000-0000-0000-0000-000000000000":
			units.append((option.contents[0].strip(), option.attrs['value'])) # Unit, ID
	return units


def login(session, credentials, findUnits=False):
	url = "http://bestallningsportal.system.svenskakyrkan.se/Inloggning.aspx"
	req = session.get(url)
	html = req.text  # Get the initial page to get viewstate and other aspx
	if req.status_code >= 400: #Check if page errored, most likely not connected to KNET
		print(f"Error {req.status_code}, connected to KNET?")
		sys.exit(1)

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

	multipleUnits = False
	if html.find("Välj enhet:"): #Multiple economic units use credentials["economicUnit"]
		aspx = findEventValidationViewstate(html)
		multipleUnits = True

	if not multipleUnits and (html.find("form method=\"post\" action=\"./Inloggning.aspx\"") != -1 or \
	   html.find("Du har inga rättigheter till detta system") != -1):
		print("Login failed, check access and credentials")
		sys.exit(1)

	if not html.find("Välj enhet") and multipleUnits: #Wanted to find units, but user only has access to single unit
		print(f"Single economic unit access: {getSingleEconomicUnit(html)}")

	if findUnits and multipleUnits:
		print("Found units:")
		for unit in getMultipleEconomicUnits(html):
			print(f"{unit[0]} : {unit[1]}")

	if multipleUnits:
		data = {
			"__EVENTTARGET": "ctl00$cph1$ctrlInloggningView$lstEnheter",
			"__EVENTVALIDATION": aspx["validation"],
			"__VIEWSTATEGENERATOR": aspx["viewstategen"],
			"__VIEWSTATE": aspx["viewstate"],
			"ctl00$cph1$ctrlInloggningView$lstEnheter": credentials["economicUnit"]
		}
		req = session.post(url, data=data)


def logout(session):
	#Navigate to http://bestallningsportal.system.svenskakyrkan.se/Bestallning.aspx and press "Logga ut"
	url = "http://bestallningsportal.system.svenskakyrkan.se/Bestallning.aspx"
	aspx, html = navigate(session, url)

	data = {
			"ctl00$cph1$ctrlViewsBestallningView$MainScriptManager": "ctl00$cph1$ctrlViewsBestallningView$pnlHelloWorld|ctl00$cph1$ctrlViewsBestallningView$ctrlLoggedInBarView$btnLogout",
			"__EVENTTARGET": "ctl00$cph1$ctrlViewsBestallningView$ctrlLoggedInBarView$btnLogout",
			"__EVENTVALIDATION": aspx["validation"],
			"__VIEWSTATEGENERATOR": aspx["viewstategen"],
			"__VIEWSTATE": aspx["viewstate"],
			"__ASYNCPOST": "true"
	}
	session.post(url, data=data)


def navigate(session, url):
	html = session.get(url).text
	#print(f"Now at {url}")
	# print(html)
	return findEventValidationViewstate(html), html


def getCompanyNameMAC(html):
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
	company = getCompanyNameMAC(html)

	if verifyMACExists(session, mac):
		print(f"MAC {mac} already registered in {company}")
		return
	
	aspx, html = navigate(session, url)	

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
	html = req.text

	search = "Orsak: Error - Problem med att skapa mac-konto, mac-adress: "
	if html.find(search) != -1:
		print(f"MAC {mac} already registered, possibly in another economic unit")
	else:
		print(f"{name} {mac} {type} registered: {verifyMACExists(session, mac)}")


def verifyMACExists(session, mac):
	url = "http://bestallningsportal.system.svenskakyrkan.se/GastnatLista.aspx"
	aspx, html = navigate(session, url)
	mac = mac.lower()
	
	if html.find(mac) == -1:
		return False
	else:
		return True #TODO Improve this to return info on line about the registered device (name, type, last used etc)


def main(argv):
	usage = "svk-mac.py -h -f (Find economic unit IDs) -u <username> -p <password> -e OPTIONAL <economic unit ID in case access to multiple> -m <mac-address> -n <name> -t <LAPTOP/PHONE/TABLET/OTHER> -i/--ifile <list-of-mac-adresses.txt>, --check <checks if MAC in -m exists>"

	if len(argv) == 0:
		print("No parameters given")
		print(usage)
		sys.exit(1)

	credentials = {
		"username": "",
		"password": "",
		"economicUnit": ""
	}

	mac = ""
	name = ""
	device = Type.OTHER
	inputFile = ""

	operation = "register"
	multiple = False

	try:
		opts, args = getopt.getopt(argv, "hfu:p:e:m:n:t:i:", ["ifile=", "check"])
	except getopt.GetoptError:
		print(usage)
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print(usage)
			sys.exit(2)

		elif opt == '-f': #Get choices of different economic units
			operation = "findUnits"

		elif opt == "-u":
			credentials["username"] = arg

		elif opt == "-p":
			credentials["password"] = arg

		elif opt == "-e": #Set economic unit ID
			credentials["economicUnit"] = arg

		elif opt == "-m":
			mac = arg

		elif opt == "-n":
			name = arg

		elif opt == "-t":
			if arg in ("LAPTOP", "PHONE", "TABLET", "OTHER"):
				device = Type[arg]
			else:
				print(f"Wrong type: {arg}")
				sys.exit(1)

		elif opt in ("-i", "--ifile"):
			inputFile = arg
			multiple = True

		elif opt == "--check":
			operation = "check"

		else:
			print(f"Illegal option: {opt} : {arg}")
			print(usage)
			sys.exit(1)

	sess = requests.Session()
	
	if operation == "register" and not multiple:
		login(sess, credentials)
		registerMAC(sess, mac, name, device)
		
		logout(sess)
		sys.exit(0)

	elif operation == "register" and multiple:
		login(sess, credentials)
		#MAC	NAME	TYPE
		with open(inputFile, 'r') as file:
			for line in file:
				split = line.strip().split('\t')
				mac = split[0]
				name = split[1]
				device = Type[split[2]]
				registerMAC(sess, mac, name, device)
		
		logout(sess)
		sys.exit(0)
	
	elif operation == "check" and not multiple:
		login(sess, credentials)
		print(f"MAC {mac} registered: {verifyMACExists(sess, mac)}")
		
		logout(sess)
		sys.exit(0)
	
	elif operation == "check" and multiple:
		login(sess, credentials)
		#MAC	(NAME	TYPE)
		with open(inputFile, 'r') as file:
			for line in file:
				split = line.strip().split('\t')
				mac = split[0]
				print(f"MAC {mac} registered: {verifyMACExists(sess, mac)}")
		
		logout(sess)
		sys.exit(0)
	
	elif operation == "findUnits":
		login(sess, credentials, findUnits=True)
		
		logout(sess)
		sys.exit(0)

if __name__ == '__main__':
	main(sys.argv[1:])

