from modules.common import get_config_param, get_top_level_domains, run_massdns


def run(db_connection, project_name):
	top_domains = get_top_level_domains(db_connection, project_name)
	if top_domains is not None:
		for top_domain in top_domains:
			list_of_subdomains_to_test = []
			for lines in open(get_config_param("massdns", "subdomain list")):
				if lines.strip() != "":
					list_of_subdomains_to_test.append(lines.strip() + "." + top_domain)
			run_massdns(db_connection, project_name, list_of_subdomains_to_test, True)