import socket
from ipwhois import IPWhois
from netaddr import *

def run(db_connection, project_name):
	project = db_connection["projects"].find_one({ "project": project_name})
	nets = {}
	if "asns" in project:
		for asn in project["asns"]:
			if "cidrs" in asn:
				for cidr in asn["cidrs"]:
					nets[IPNetwork(cidr)] = asn["description"]

	for ip in db_connection[project_name + ".ips"].find():
		if "asn" not in ip:
			try:
				if not check_ip_in_net(db_connection, project_name, IPAddress(ip["ip"]), nets):
					whois_obj = IPWhois(ip["ip"])
					whois_results = whois_obj.lookup_rdap()
					if "asn_description" in whois_results:
						db_connection[project_name + ".ips"].update_one({"ip": ip["ip"]}, {'$set': { "asn": whois_results["asn_description"]}})
			except Exception:
				pass
		if "rdns" not in ip:
			try:
				rdns, _, _ = socket.gethostbyaddr(ip["ip"])
				db_connection[project_name + ".ips"].update_one({"ip": ip["ip"]}, {'$set': { "rdns": rdns}})
			except Exception:
				pass


def check_ip_in_net(db_connection, project_name, ip, networks):
	for net, descr in networks.items():
		if ip in net:
			db_connection[project_name + ".ips"].update_one({"ip": str(ip)}, {'$set': { "asn": descr}})
			return True
	return False

