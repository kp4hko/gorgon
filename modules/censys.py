import censys.ipv4
import json
from modules.common import get_top_level_domains, get_config_param
import re

def run(db_connection, project_name):
	top_domains = get_top_level_domains(db_connection, project_name)
	if top_domains is not None:
		tup_top_domains = tuple(top_domains)
		censys_keys = get_config_param("censys", "path to keys")
		with open(censys_keys) as json_file:
			api_keys = json.load(json_file)
			censys_conn = censys.ipv4.CensysIPv4(api_id=api_keys["censysUsername"], api_secret=api_keys["censysSecret"])
			for top_domain in top_domains:
				domain_to_search = re.sub('\.', '\\.', top_domain)
				try:
					for censys_search_result in censys_conn.search("443.https.tls.certificate.parsed.extensions.subject_alt_name.dns_names: /.*\." + domain_to_search + "/", ['ip', '443.https.tls.certificate.parsed.extensions.subject_alt_name.dns_names']):
						host = db_connection[project_name + ".ips"].find_one({ "ip": censys_search_result['ip']})
						certs = censys_search_result['443.https.tls.certificate.parsed.extensions.subject_alt_name.dns_names']
						if host is None:
							db_connection[project_name + ".ips"].insert_one({ "ip": censys_search_result['ip'] })
							host = db_connection[project_name + ".ips"].find_one({ "ip": censys_search_result['ip']})

						for cert in certs:
							if 'certs' in host:
								if cert not in host['certs']:
									db_connection[project_name + ".ips"].update_one({"ip": censys_search_result['ip']}, {'$push': {"certs": cert}})
							else:
								db_connection[project_name + ".ips"].update_one({"ip": censys_search_result['ip']}, {'$set': {"certs": [cert] }})

							host = db_connection[project_name + ".ips"].find_one({ "ip": censys_search_result['ip']})

							cert_domain = re.sub('^\*\.', '', cert)
							if cert_domain.endswith(tup_top_domains):
								domain = db_connection[project_name + ".domains"].find_one({"domain": cert_domain })
								if domain is None:
									db_connection[project_name + ".domains"].insert_one({ "domain": cert_domain, "found_from": [ "censys" ] })
				except Exception as e:
					print(e.__class__, e)
