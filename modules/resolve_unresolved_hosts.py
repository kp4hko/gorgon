from modules.common import run_massdns, get_top_level_domains

def run(db_connection, project_name):
	top_domains = get_top_level_domains(db_connection, project_name)
	if top_domains is not None:
		tup_top_domains = tuple([domain + '.' for domain in top_domains])
		subdomains_to_test = []
		for domain in db_connection[project_name + ".domains"].find({'ip': {'$exists': False}, 'cname': {'$exists': False}}):
			subdomains_to_test.append(domain["domain"])
		if len(subdomains_to_test) > 0:
			run_massdns(db_connection, project_name, subdomains_to_test, False)
		company_cnames = get_cnames_to_test(db_connection, tup_top_domains, project_name)
		while len(company_cnames) > 0:
			run_massdns(db_connection, project_name, company_cnames, False)
			company_cnames = get_cnames_to_test(db_connection, tup_top_domains, project_name)
		add_cnamed_to_company_to_ip_col(db_connection, tup_top_domains, project_name)

def find_cnames_pointing_to_company(db_connection, top_domains, project_name):
	cnames_pointing_to_company = {}
	cnamed_domains = db_connection[project_name + ".domains"].find({'ip': {'$exists': False}, 'cname': {'$exists': True}})
	for domain in cnamed_domains:
		cname_to_check = domain["cname"]
		if cname_to_check.endswith(top_domains):
			if cname_to_check not in cnames_pointing_to_company:
				cnames_pointing_to_company[cname_to_check] = [ domain["domain"] ]
			else:
				cnames_pointing_to_company[cname_to_check].append(domain["domain"])
	return cnames_pointing_to_company

def get_cnames_to_test(db_connection, top_domains, project_name):
	cnames_pointing_to_company = find_cnames_pointing_to_company(db_connection, top_domains, project_name)			
	cnames_to_test = []
	for cname in cnames_pointing_to_company:
		correct_cname = cname.strip('.')
		cname_to_test = db_connection[project_name + ".domains"].find_one({'domain': correct_cname})
		if cname_to_test == None:
			cnames_to_test.append(correct_cname)
			db_connection[project_name + ".domains"].insert_one({'domain': correct_cname})
	return cnames_to_test
	
def insert_to_ip_col(pointed_domain, cname, cnames_pointing_to_company, db_connection, project_name):
	for cnamed_domain in cnames_pointing_to_company[cname]:
		for ip in pointed_domain["ip"]:
			ip_entity = db_connection[project_name + ".ips"].find_one({'ip': ip})
			if cnamed_domain not in ip_entity["domain"]:
				db_connection[project_name + ".ips"].update_one({ 'ip': ip}, {'$push': {"domain": cnamed_domain}})
		if cnamed_domain in cnames_pointing_to_company.keys():
			insert_to_ip_col(pointed_domain, cnamed_domain, cnames_pointing_to_company, db_connection, project_name)
	

def add_cnamed_to_company_to_ip_col(db_connection, top_domains, project_name):
	cnames_pointing_to_company = find_cnames_pointing_to_company(db_connection, top_domains, project_name)
	cnamed_domains = [ domain for cname in cnames_pointing_to_company for domain in cnames_pointing_to_company[cname]]
	for cname in cnames_pointing_to_company:
		if cname not in cnamed_domains:
			correct_cname = cname.strip('.')
			pointed_domain = db_connection[project_name + ".domains"].find_one({'domain': correct_cname})
			if "ip" in pointed_domain:
				insert_to_ip_col(pointed_domain, cname, cnames_pointing_to_company, db_connection, project_name)
					
			
		 
