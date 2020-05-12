from libnmap.process import NmapProcess
from libnmap.parser import NmapParser
from modules.common import get_default_args_for_command
from time import sleep

def run(db_connection, project_name):
	hosts = db_connection[project_name + ".ips"].find({"ports": {'$exists': True}})
	if hosts.count() > 0:
		targets = {}
		for host in hosts:
			targets[host["ip"]] = set([str(port["port"]) for port in host["ports"]])
		targets_to_scan = []
		targets_to_skip = []
		for target in targets:
			if target not in targets_to_skip:
				targets_to_skip.append(target)
				targets_to_add = [target] 
				for target_a in targets:
					if target_a not in targets_to_skip:
						if targets[target] == targets[target_a]:
							targets_to_add.append(target_a)
							targets_to_skip.append(target_a)					
				targets_to_scan.append({"ips": targets_to_add, "ports": targets[target]})
		options = get_default_args_for_command("nmap")
		finished = 0
		number_of_targets = len(targets)
		print("total targets: " + str(number_of_targets))
		for target in targets_to_scan:
			opts = " ".join(options) + " -p " + ','.join(target["ports"])
			print(" ".join(target["ips"]))
			under_scan = len(target["ips"])
			waiting = number_of_targets - under_scan - finished
			nmproc = NmapProcess(target["ips"], opts)
			nmproc.run_background()
			while nmproc.is_running():
				print("finished: " + str(finished) + ", under scan: " + str(under_scan) + ", waiting: " + str(waiting) + ", progress of current scan:" + str(nmproc.progress), end="\r", flush=True)
				sleep(2)
			finished = finished + under_scan
			print()
			if nmproc.rc == 0:
				parsed_report = NmapParser.parse(nmproc.stdout)
				for host in parsed_report.hosts:
					for service in host.services:
						db_connection[project_name + ".ips"].update_one({"ip": host.address}, {'$set': {"ports.$[elem].service": service.service}}, array_filters=[ { "elem.port":  service.port} ])
						if service.banner != '':
							db_connection[project_name + ".ips"].update_one({"ip": host.address}, {'$set': {"ports.$[elem].version": service.banner}}, array_filters=[ { "elem.port":  service.port} ])
						if service.tunnel != '':
							db_connection[project_name + ".ips"].update_one({"ip": host.address}, {'$set': {"ports.$[elem].tunnel": service.tunnel}}, array_filters=[ { "elem.port":  service.port} ])
			else:
				print(nmproc.stderr, nmproc.stdout)
