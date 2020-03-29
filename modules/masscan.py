import subprocess
import re
import json
import os
from modules.common import get_in_scope_ips, get_default_args_for_command, get_config_param

def run(db_connection, project_name):
	inscope_ips = get_in_scope_ips(db_connection, project_name)
	ips_to_scan = []
	if inscope_ips.count() > 0:
		for inscope_ip in inscope_ips:
			ips_to_scan.append(inscope_ip["ip"])
	project_info = db_connection["projects"].find_one({"project": project_name})
	if "asns" in project_info:
		for asn in project_info["asns"]:
			ips_to_scan.extend(asn["cidrs"])
	if ips_to_scan != []:
		ooc_domains = db_connection[project_name + ".domains"].find({ "out_of_scope": True})
		exclude_ips = []
		for domain in ooc_domains:
			exclude_ip = ip_to_exclude(domain, db_connection, project_name)
			if exclude_ip is not None:
				exclude_ips.extend(exclude_ip)
		default_args = get_default_args_for_command("masscan")
		result_file = get_config_param("masscan", "result file")
		args_fc = [str(arg) if arg != "_resultfile_" else result_file for arg in default_args]
		if exclude_ips != []:
			args_fc.append("--exclude")
			args_fc.append(','.join(exclude_ips))
		args_fc.extend(ips_to_scan)
		masscan_output_parsed = []
		popen = subprocess.run(args_fc)
		for masscan_line in open(result_file, 'r'):
			if not re.search("finished", masscan_line, re.IGNORECASE):
				line_to_add = masscan_line.strip().rstrip(',')
				masscan_output_parsed.append(json.loads(line_to_add))
		os.remove(result_file)
		for result in masscan_output_parsed:
			ip_in_db = db_connection[project_name + ".ips"].find_one({ "ip": result['ip']})
			port_num = result['ports'][0]['port']
			if ip_in_db is not None:
				if "ports" not in ip_in_db:
					db_connection[project_name + ".ips"].update_one({"ip": result['ip']}, { "$set": { "ports": [{"port":  port_num }] }})
				else:
					port = next((port for port in ip_in_db["ports"] if port["port"] == port_num), None)
					if port is None:
						db_connection[project_name + ".ips"].update_one({"ip": result['ip']}, { "$push": { "ports": {"port":  port_num } }})
			else:
				db_connection[project_name + ".ips"].insert_one({"ip": result['ip'], "ports": [{"port":  port_num }]})
			

def ip_to_exclude(domain, db_connection, project_name):
	if "ip" in domain:
		return domain["ip"]
	if "cname" in domain:
		correct_cname = domain["cname"].strip('.')
		ooc_cname = db_connection[project_name + ".domains"].find_one({ "domain": correct_cname })
		if ooc_cname is not None:
			return ip_to_exclude(ooc_cname, db_connection, project_name)
		else:
			return None
	return None
