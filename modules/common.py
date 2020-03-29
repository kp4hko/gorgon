import subprocess
import yaml
import re

def get_top_level_domains(db_connection, project_name):
	top_domains = find_top_level_domains(db_connection, project_name)
	if top_domains.count() == 0:
		print("specify a top level domain for the project first (set_top_level_domain)")
		return None
	else:
		return [top_domain["domain"] for top_domain in top_domains]
		
def find_subdomains_run(db_connection, project_name, module_name):
	top_domains = get_top_level_domains(db_connection, project_name)
	if top_domains is not None:
		for top_domain in top_domains:
			default_args = get_default_args_for_command(module_name)
			args_fc = [arg if arg != "_domain_" else top_domain for arg in default_args]
			popen = subprocess.Popen(args_fc, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
			for line in  popen.stdout:
				ln = line.decode().strip().lower().lstrip('.')
				if (ln != ''):
					domain = db_connection[project_name + ".domains"].find_one({ "domain": ln})
					if domain is None:
						db_connection[project_name + ".domains"].insert_one({"domain": ln, "found_from": [ module_name ] })
					elif module_name not in domain["found_from"]:
						db_connection[project_name + ".domains"].update_one({"domain": ln}, {'$push': {"found_from": module_name}})
		
		
def find_top_level_domains(db_connection, project_name):
	return db_connection[project_name + ".domains"].find( { "top_level": True } )
	
def get_in_scope_ips(db_connection, project_name):
	out_of_scope_rules = get_config_param("masscan", "do not scan")
	query_string = { "$nor": [] }
	for rule in out_of_scope_rules:
		for key in rule:
			expr = re.compile(rule[key], re.IGNORECASE)
			query_string["$nor"].append( { key : { "$regex": expr } } )
	domains_out_of_scope = db_connection[project_name + ".domains"].find({ "out_of_scope": True})
	for ooc_domain in domains_out_of_scope:
		query_string["$nor"].append( { "domain" : ooc_domain["domain"] } )
	return db_connection[project_name + ".ips"].find(query_string)
	
	
def parse_config_file():
	with open("modules/modules.yaml") as config:
		return yaml.load(config)
		
def get_default_args_for_command(module_name):
	config = parse_config_file()
	default_args = []
	for category in config:
		for module in category["modules"]:
			if module["name"] == module_name:
				default_args.append(module["executable"])
				default_args.extend(module["default options"])
	return default_args

def get_config_param(module_name, param):
	config = parse_config_file()
	for category in config:
		for module in category["modules"]:
			if module["name"] == module_name:
				return module[param]
				
def run_massdns(db_connection, project_name, domains_to_test, massdns_module):
	args_fc = get_default_args_for_command("massdns")
	subdomains_to_test = '\n'.join(domains_to_test)
	popen = subprocess.Popen(args_fc, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, _ = popen.communicate(input=subdomains_to_test.encode())
	str_output = stdout.decode()
	for line in str_output.splitlines():
		if line != None:
			ln = line.strip()
			if ln != '':
				new_entry = ln.split()
				new_entry[0] = re.sub('\.$', '', new_entry[0])
				domains = db_connection[project_name + ".domains"]
				ips = db_connection[project_name + ".ips"]
				domain = domains.find_one({ "domain": new_entry[0]})
				if domain is not None:
					if new_entry[1] == 'A':
						if 'ip' in domain:
							if new_entry[2] not in domain['ip']:
								domains.update_one({"domain": new_entry[0]}, {'$push': {"ip": new_entry[2]}})
						else:
							domains.update_one({"domain": new_entry[0]}, {'$set': {"ip": [ new_entry[2] ] } })
						insert_ip_to_db(ips, new_entry[2], new_entry[0])
					elif new_entry[1] == 'CNAME':
						domains.update_one({"domain": new_entry[0]}, {'$set': {"cname": new_entry[2] } })
					if massdns_module:
						if "found_from" in domain:
							if "massdns" not in domain["found_from"]:
								domains.update_one({"domain": new_entry[0]}, {'$push': {"found_from": "massdns"}})
						else:
							domains.update_one({"domain": new_entry[0]}, {'$set': {"found_from": [ "massdns" ]}})
				else:
					if new_entry[1] == 'A':
						domains.insert_one({"domain": new_entry[0], "found_from": [ "massdns" ], "ip": [ new_entry[2] ] })
						insert_ip_to_db(ips, new_entry[2], new_entry[0])
					elif new_entry[1] == 'CNAME':
						domains.insert_one({"domain": new_entry[0], "found_from": [ "massdns" ], "cname": new_entry[2] })

def insert_ip_to_db(ip_collection, ip_addr, domain_name):
	ip = ip_collection.find_one({ "ip": ip_addr })
	if ip is None:
		ip_collection.insert_one({ "ip": ip_addr, "domain": [ domain_name ] })
	else:
		if 'domain' in ip:
			if domain_name not in ip['domain']:
				ip_collection.update_one({ "ip": ip_addr }, {'$push': { "domain": domain_name }})
		else:
			ip_collection.update_one({ "ip": ip_addr }, {'$set': { "domain": [ domain_name ] }})
