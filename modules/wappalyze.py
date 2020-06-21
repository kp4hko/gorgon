from modules.common import get_top_level_domains, get_config_param
import re
import concurrent.futures
import http.client
import ssl as ssl_lib
from pprint import pprint
import json
from bs4 import BeautifulSoup
import js_regex

def run(db_connection, project_name):
	top_domains = get_top_level_domains(db_connection, project_name)
	if top_domains is not None:
		tup_top_domains = tuple(top_domains)
		applications = []
		scanned_hosts_with_http = db_connection[project_name + ".ips"].find({ "$or": [{ "ports.service": "http" }, { "ports.service": "https" }, { "ports.service": "http-proxy" }] })
		if scanned_hosts_with_http.count() > 0:
			for scanned_host in scanned_hosts_with_http:
				vhosts = set()
				vhosts.add(scanned_host["ip"])
				if "domain" in scanned_host:
					for domain in scanned_host["domain"]:
						vhosts.add(domain)
				if "certs" in scanned_host:
					for cert in scanned_host["certs"]:
						cert_domain = re.sub('^\*\.', '', cert)
						if cert_domain.endswith(tup_top_domains):
							vhosts.add(cert_domain)
				if "rdns" in scanned_host:
					if scanned_host["rdns"].endswith(tup_top_domains):
						vhosts.add(scanned_host["rdns"])
				for port in scanned_host["ports"]:
					if port["service"] == "http" or port["service"] == "https" or port["service"] == "http-proxy":
						for vhost in vhosts:
							if "tunnel" in port:
								if port["tunnel"] == "ssl":
									applications.append({"host": scanned_host["ip"], "vhost": vhost, "port": port["port"], "ssl": True})
								else:
									applications.append({"host": scanned_host["ip"], "vhost": vhost, "port": port["port"], "ssl": False})
							else:
								applications.append({"host": scanned_host["ip"], "vhost": vhost, "port": port["port"], "ssl": False})
		out_of_scope_rules = get_config_param("masscan", "do not scan")
		query_string = { "$or": [] }
		for rule in out_of_scope_rules:
			for key in rule:
				expr = re.compile(rule[key], re.IGNORECASE)
				query_string["$or"].append( { key : { "$regex": expr } } )
		do_not_scanned_hosts = db_connection[project_name + ".ips"].find(query_string)
		if do_not_scanned_hosts.count() > 0:
			do_not_scanned_vhost = set()
			for do_not_scanned_host in do_not_scanned_hosts:
				if "domain" in do_not_scanned_host:
					for domain in do_not_scanned_host["domain"]:
						do_not_scanned_vhost.add(domain)
			for vhost in do_not_scanned_vhost:
				applications.append({"host": vhost, "vhost": vhost, "port": 443, "ssl": True})
		cnamed_domains = db_connection[project_name + ".domains"].find({ "cname" : { "$exists": True }, "out_of_scope": { "$ne": True }})
		cnames_struct = {}
		for domain in cnamed_domains:
			cname_to_check = domain["cname"].strip('.')
			if cname_to_check not in cnames_struct:
				cnames_struct[cname_to_check] = [ domain["domain"] ]
			else:
				cnames_struct[cname_to_check].append(domain["domain"])
		for cname in cnames_struct:
			if not cname.endswith(tup_top_domains):
				for domain in cnames_struct[cname]:
					domains = add_cname_to_apps(domain, cnames_struct)
					for cnamed_domain in domains:
						applications.append({"host": cnamed_domain, "vhost": cnamed_domain, "port": 443, "ssl": True})
						applications.append({"host": cnamed_domain, "vhost": cnamed_domain, "port": 80, "ssl": False})
		wappalyze_data = []
		max_redirects = get_config_param("wappalyze", "max redirects")
		max_concurrent_requests = get_config_param("wappalyze", "max concurrent requests")
		request_timeout = get_config_param("wappalyze", "request timeout")
		with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
			for app in applications:
				executor.submit(get_wappalyze_data, app["host"], app["vhost"], app["ssl"], app["port"], wappalyze_data, max_redirects, request_timeout)
		wappalyzer_rules_file = open('apps.json')
		wappalyzer_rules = json.load(wappalyzer_rules_file)
		categories = {}
		for cat in wappalyzer_rules["categories"]:
			categories[cat] = wappalyzer_rules["categories"][cat]["name"]
		for app in wappalyze_data:
			if app["status"] is None:
				continue
			if app["cookie"] is not None and app["cookie"] != '':
				cookies = dict(x.split("=", 1) for x in app["cookie"].split("; "))
			else:
				cookies = None
			if app["headers"] is not None:
				headers = dict(app["headers"])
			else:
				headers = None
			if app["body"] is not None:
				body_parsed = BeautifulSoup(app["body"], 'html.parser')
				body_string = app["body"]
			else:
				body_parsed = None
				body_string = None
			for tech_name, rules in wappalyzer_rules["apps"].items():
				if check_tech(tech_name, rules, cookies, headers, body_parsed, body_string):
					if "tech" not in app:
						app["tech"] = {}
					category = ''
					for cat in rules["cats"]:
						cat = str(cat)
						if category == '':
							category = categories[cat]
						else:
							category = category + ', ' + categories[cat]
					
					app["tech"][category] = tech_name
				if body_parsed is not None:
					if body_parsed.title is not None:
						app["title"] = body_parsed.title.string
		for app in wappalyze_data:
			if app["ssl"]:
				application = 'https://'
			else:
				application = 'http://'
			application = application + app["vhost"]
			if not (app["ssl"] and app["port"] == 443 or not app["ssl"] and app["port"] == 80):
				application = application + ':' + str(app["port"])
			app_in_db = db_connection[project_name + ".applications"].find_one( {'host': app["host"], 'app': application} )
			app_doesnt_exist = app_in_db is None
			app_scan_errored = app["failed"] is not None
			redir_outside = app["failed"] == "redirect outside app"
			techs_recognized = "tech" in app
			title_found = "title" in app
			app_to_insert = {'host': app["host"], 'app': application }
			if app_scan_errored and not redir_outside:
				app_to_insert["failed"] = app["failed"]
			else:
				if redir_outside:
					app_to_insert["failed"] = app["failed"]
					app_to_insert["redirect_url"] = app["path"]
				else:
					app_to_insert["start_url"] = app["path"]
				app_to_insert["status"] = app["status"]
				app_to_insert["headers"] = app["headers"]
				if techs_recognized:
					app_to_insert["techs"] = app["tech"]
				if title_found:
					app_to_insert["title"] = app["title"]
			if app_doesnt_exist:			
				db_connection[project_name + ".applications"].insert_one(app_to_insert)
			else:
				db_connection[project_name + ".applications"].update_one({'host': app["host"], 'app': application }, app_to_insert)
			
		
def check_tech(tech_name, wapp_rules, cookies, headers, body_parsed, body_string):
	if "cookies" in wapp_rules and cookies is not None:
		if set(cookies.keys()) & set(wapp_rules["cookies"].keys()):
			return True
	if "headers" in wapp_rules and headers is not None:
		matching_headers = set(headers.keys()) & set(wapp_rules["headers"].keys())
		for matching_header in matching_headers:
			header_rule_value = get_valid_regex(wapp_rules["headers"][matching_header])
			if header_rule_value == "" or get_compiled_regex(header_rule_value).search(headers[matching_header]):
				return True
	if "html" in wapp_rules and body_string is not None:
		html_regexes = get_list_of_regexes(wapp_rules["html"])
		for html_regex in html_regexes:
			html_regex = get_valid_regex(html_regex)
			if get_compiled_regex(html_regex).search(body_string):
				return True
	if "meta" in wapp_rules and body_parsed is not None:
		for meta_rule_name, meta_rule_value in wapp_rules["meta"].items():
			attrs = { "name": meta_rule_name, 'content' : get_compiled_regex(get_valid_regex(meta_rule_value)) }
			if search_parsed_body("meta", attrs, body_parsed):
				return True
	if "script" in wapp_rules and body_parsed is not None:
		script_regexes = get_list_of_regexes(wapp_rules["script"])
		for script_regex in script_regexes:
			attrs = { "src": get_compiled_regex(get_valid_regex(script_regex)) }
			if search_parsed_body("script", attrs, body_parsed):
				return True
	if "url" in wapp_rules and body_parsed is not None:
		attrs = { "href": get_compiled_regex(get_valid_regex(wapp_rules["url"])) }
		if search_parsed_body("a", attrs, body_parsed):
			return True
	return False

def get_compiled_regex(regex):
	try:
		regex_to_return = js_regex.compile(regex)
	except Exception as e:
		try:
			regex_to_return = re.compile(regex)
		except Exception as a:
			regex_to_return = re.compile('a^')
	return regex_to_return
	

def search_parsed_body(tag, attrs, parsed_page):
	if len(parsed_page.find_all(tag, attrs)) > 0:
		return True
	else:
		return False

def get_list_of_regexes(regex_to_list):
	regexes = []
	if isinstance(regex_to_list, str):
		regexes.append(regex_to_list)
	else:
		for regex in regex_to_list:
			regexes.append(regex)
	return regexes		
	
def get_valid_regex(regex):
	return regex.split('\\;')[0]	

def get_wappalyze_data(host, vhost, ssl, port, results, max_redirects, request_timeout):
	status, url, headers, body, cookie, failed_reason = get_target_info(host, vhost, ssl, port, "/", max_redirects, request_timeout)
	results.append({ "host": host, "vhost": vhost, "ssl": ssl, "port": port, "status": status, "path": url, "failed": failed_reason, "headers": headers, "body": body, "cookie": cookie })
	
		
def get_target_info(host, vhost, ssl, port, url, max_redirects, request_timeout, recursion_count=0, cookie=''):
	if recursion_count >= max_redirects:
		return None, None, None, None, None, "recursion redirects"
	
	if not ssl:
		h1 = http.client.HTTPConnection(host, port, timeout=request_timeout)
	else:
		h1 = http.client.HTTPSConnection(host, port, timeout=request_timeout , context=ssl_lib._create_unverified_context())
	
	vhost_header = vhost	
	if not (ssl and port == 443 or not ssl and port == 80):
		vhost_header = vhost_header + ':' + str(port)
		
	headers =	{
				'Host' : vhost_header,
				'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0',
				'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
				'Accept-Language' : 'en-US,en;q=0.5',
				'Connection': 'keep-alive',
				'Upgrade-Insecure-Requests': 1
			}
	if cookie != '':
		headers["Cookie"] = cookie
	try:		
		h1.request("GET", url, body=None, headers=headers)
		r1 = h1.getresponse()
	except Exception as e:
		print(e, host, vhost, port, "SSL: ", ssl)
		failed_reason = "connection failed " + str(e)
		return None, None, None, None, None, failed_reason
	response_body = r1.read().decode()
	for header in r1.getheaders():
		if header[0].lower() == 'set-cookie':
			cookie_value = header[1].split('; ')[0]
			if cookie == '':
				cookie = cookie_value
			else:
				cookie = cookie + '; ' + cookie_value
	h1.close()
	if r1.status == 301 or r1.status == 302 or r1.status == 303 or r1.status == 305 or r1.status == 307:
		location = r1.getheader('Location')
		link = ''
		if not ssl:
			link = 'http://' + vhost_header + '/'
		else :
			link = 'https://' + vhost_header + '/'
		if location.startswith(link) or location.startswith('/') or location.startswith(vhost_header + '/'):
			reg = "^(https?:\/\/)?" + vhost_header.replace('.', '\\.')
			path = re.sub(reg, '',location)
			rec_count = recursion_count + 1
			status, url, headers, body, cookie, failed_reason = get_target_info(host, vhost, ssl, port, path, max_redirects, request_timeout,  rec_count, cookie)
			return status, url, headers, body, cookie, failed_reason
		else:
			return r1.status, r1.getheader('Location'), r1.getheaders(), response_body, cookie, "redirect outside app"
	else:
		return r1.status, url, r1.getheaders(), response_body, cookie, None

def add_cname_to_apps(domain, cnames_struct):
	domains = [ domain ]
	if domain in cnames_struct:
		for rec_domain in cnames_struct[domain]:
			cnamed_domains = add_cname_to_apps(rec_domain, cnames_struct)
			domains.extend(cnamed_domains)
	return domains
