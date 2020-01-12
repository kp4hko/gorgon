from modules.common import find_subdomains_run

def run(db_connection, project_name):
	find_subdomains_run(db_connection, project_name, "subfinder")