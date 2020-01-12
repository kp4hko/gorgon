import requests
from bs4 import BeautifulSoup
import re

def run(db_connection, project_name):
	project = db_connection["projects"].find_one({ "project": project_name})
	if "company_names" in project:
		cidr_report_page = requests.get('http://www.cidr-report.org/as2.0/autnums.html')
		cidr_report_page_parsed = BeautifulSoup(cidr_report_page.text, 'html.parser')
		asns = cidr_report_page_parsed.pre.contents
		asns.pop(0)
		asns_to_choose = {}
		for company in project["company_names"]:
			for as_num,comp in zip(asns[0::2], asns[1::2]):
				if re.search(company, comp, re.IGNORECASE):
					as_number = as_num.string.strip()
					comp_desc = comp.string.strip()
					asn_to_cidr_page = requests.get('http://www.cidr-report.org/cgi-bin/as-report?as=' + as_number + '&view=2.0')
					asn_to_cidr_page_parsed = BeautifulSoup(asn_to_cidr_page.text, 'html.parser')
					if len(asn_to_cidr_page_parsed.find_all('h3', string="NOT Announced")) == 0:
						cidrs = asn_to_cidr_page_parsed.find_all('pre')[2].find_all('a')
						if len(cidrs) != 0:
							cidrs.pop(0)
							correct_cidrs = []
							for cidr in cidrs:
								correct_cidrs.append(cidr.contents[0].string)
							dict_ind_num = len(asns_to_choose)
							print(dict_ind_num, as_number, comp_desc, ', '.join(correct_cidrs))
							asns_to_choose[dict_ind_num] = {"asn": as_number, "description": comp_desc, "cidrs": correct_cidrs}
		user_choices_of_correct_asns = [int(x) for x in input('Choose what ASNs will be used in futher recon activities: ').split() if x.isdigit()]
		for choice in user_choices_of_correct_asns:
			if choice in asns_to_choose:
				for cidr in asns_to_choose[choice]["cidrs"]:
					project = db_connection["projects"].find_one({ "project": project_name})
					if "asns" not in project:
						db_connection["projects"].update_one({ "project": project_name}, {'$set': {"asns": [ {"asn": asns_to_choose[choice]["asn"], "description": asns_to_choose[choice]["description"], "cidrs": [cidr] } ] }})
					else:
						asn = next((asn for asn in project["asns"] if asn["asn"] == asns_to_choose[choice]["asn"]), None)
						if asn is not None:
							if cidr not in asn["cidrs"]:
								db_connection["projects"].update_one({ "project": project_name}, {'$push': {"asns.$[elem].cidrs": cidr} }, array_filters=[ { "elem.asn": asn["asn"] } ] )
						else:
							db_connection["projects"].update_one({ "project": project_name}, {'$push': {"asns": [ {"asn": asns_to_choose[choice]["asn"], "description": asns_to_choose[choice]["description"], "cidrs": [cidr] } ] }})
	else:
		print("specify company names first (set_company_name)")