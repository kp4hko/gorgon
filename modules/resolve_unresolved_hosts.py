from modules.common import run_massdns, get_top_level_domains

def run(db_connection, project_name):
	top_domains = get_top_level_domains(db_connection, project_name)
	if top_domains is not None:
		subdomains_to_test = []
		for domain in db_connection[project_name + ".domains"].find({'ip': {'$exists': False}, 'cname': {'$exists': False}}):
			subdomains_to_test.append(domain["domain"])
		if len(subdomains_to_test) > 0:
			run_massdns(db_connection, project_name, subdomains_to_test, False)
		company_cnames = find_cnames_pointing_to_company(db_connection, top_domains, project_name)
		while len(company_cnames) > 0:
			run_massdns(db_connection, project_name, company_cnames, False)
			company_cnames = find_cnames_pointing_to_company(db_connection, top_domains, project_name)

def find_cnames_pointing_to_company(db_connection, top_domains, project_name):
	cnames_pointing_to_company = []
	for domain in db_connection[project_name + ".domains"].find({'ip': {'$exists': False}, 'cname': {'$exists': True}}):
		cname_to_check = domain["cname"]
		for top_domain in top_domains:
			if cname_to_check.endswith(top_domain + '.'):
				if cname_to_check not in cnames_pointing_to_company:
					cnames_pointing_to_company.append(cname_to_check)
				break
	cnames_to_test = []
	for cname in cnames_pointing_to_company:
		correct_cname = cname.strip('.')
		cname_to_test = db_connection[project_name + ".domains"].find_one({'domain': correct_cname})
		if cname_to_test == None:
			cnames_to_test.append(correct_cname)
			db_connection[project_name + ".domains"].insert_one({'domain': correct_cname})
	return cnames_to_test

