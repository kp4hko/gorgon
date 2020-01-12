from modules.common import run_massdns

def run(db_connection, project_name):
	subdomains_to_test = []
	for domain in db_connection[project_name + ".domains"].find({'ip': {'$exists': False}, 'cname': {'$exists': False}}):
		subdomains_to_test.append(domain["domain"])
	run_massdns(db_connection, project_name, subdomains_to_test, False)