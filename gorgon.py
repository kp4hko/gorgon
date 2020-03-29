import cmd2
from pymongo import MongoClient
import argparse
import argcomplete
import os
import importlib
import yaml
from modules.common import parse_config_file

class gorgon_cli(cmd2.Cmd):

	project = None
	client = MongoClient('localhost', 27017)
	db = client.reconData
	modules = []
	def __init__(self):
		super().__init__()
		self.intro = """
                ▄████  ▒█████   ██▀███    ▄████  ▒█████   ███▄    █ 
               ██▒ ▀█▒▒██▒  ██▒▓██ ▒ ██▒ ██▒ ▀█▒▒██▒  ██▒ ██ ▀█   █ 
              ▒██░▄▄▄░▒██░  ██▒▓██ ░▄█ ▒▒██░▄▄▄░▒██░  ██▒▓██  ▀█ ██▒
              ░▓█  ██▓▒██   ██░▒██▀▀█▄  ░▓█  ██▓▒██   ██░▓██▒  ▐▌██▒
              ░▒▓███▀▒░ ████▓▒░░██▓ ▒██▒░▒▓███▀▒░ ████▓▒░▒██░   ▓██░
               ░▒   ▒ ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░ ░▒   ▒ ░ ▒░▒░▒░ ░ ▒░   ▒ ▒ 
                ░   ░   ░ ▒ ▒░   ░▒ ░ ▒░  ░   ░   ░ ▒ ▒░ ░ ░░   ░ ▒░
              ░ ░   ░ ░ ░ ░ ▒    ░░   ░ ░ ░   ░ ░ ░ ░ ▒     ░   ░ ░ 
                    ░     ░ ░     ░           ░     ░ ░           ░ 
                                ,⌐«φm&&φ&φ&╗m»⌐.                                
                         ┌mX▓▓▓▒▓▓▀▌▓▒▓▒║╫▓▓▒▓▓▓▓▓▓#h╖.                         
                    .φR▓▓▓▓▓▓▓▓▒▒▒╫╫╢║╠╠#ÑÑÑ╠║╢▒▒▀▓▓▓█▓▓▒m,                     
                 ┌ß██▓██▓▒▒▒▒▒▒╢║║║╠╠╠╠╚╚ÑÑ╠║║▒▒▒▒▒▓▓▓▒▓████▓n.                 
              ,#▓▓██▓▓▒▒▒╫╢╢║║╠╠╠╠╠ÑÑÑ╙N┤░╚╣▒▓▓▒▓▓▓█▓▒▒▒▒▒▓▓██▓▓╗               
            «▒▓█▓▓▓▓▒▒▒▒╫║║╠╠░╙┤├╠╡╡░N├╙╞│╙Ñ╢▒▓▓▒▒▓▓▒╢▒▒▒▒▒▒▓▒▓▓▓▓▓,            
          ┌▒▀▓█▓▓▓▒▒▒▒▒╫▒╢╠╠╠Ñ╡╠╠╠Ñ╠Ñ░││┼#╓▓▓▓███▓▓██▒║▓▒▓▓▒▓▓▒▒▒▓▓▓▓,          
         ⌠╝▓╣▓▒▒▒▒▓▒▒▓▒▓▒▒╢╫╫╢║╠╠▒▒▒▓▓▓░▐@╫▒▓████▓████▒▒▒▒▓▓▒▒▒▒▒▒▒▓▓▓▓         
       /╢Q#▓▒▒▒▒▒▒▓▓▓▓▓▓▓▓▒▒╫║@▒▓▒╚┴╫▓▓▌Ñ▒N└▀█▓▓▓██████▓▓██▒▒▒▓▓▒▒▒▒▒▓█▓▄       
      }─▌╫▒▒▒▒▒▒▒▓▓▒▒▒▒▒▒╢▀▀▓▓█▌╠#▓▓▓▓█▓▓▓█▓▌▒▓▓▒▓▓████▓▒▒▒▒███████▒▒▒▒▓▓m      
     ╠E╢▓▒▒▒▒▒▒▒▒▒▓▒╫▒╛`┬∩j▒▓▓▓╠██▓▒▓╬▒▒▒▒▓▓█████▓▓▓█▓╫▓██████▒▒▒▒██▒▒▒▓▓▓▌     
    Ñ╣▄▓▒▒▒▒▒▒▒▒▒▒▒▒▒#▒▒╢{╢▒▒▒▒██▀║│å▒▓▓▓██████▓██▓▓█▓▓██▀▓▓▀▒▒▒▒▒▒▓▓▒▒▒▓▓▓▌    
   ├É└▒╢▒▒▒▒▒▒▒▒▒▒▒▒▒╫▒├╓▒▓▀██▌▓▓▓▒▓▓▓▓▓▓▓▓▓▓█▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒M▒█▒▒▓▓▓██]   
  ⌠╝'▒╢▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▒▓█▓▓▀▒▒▓▒▓▓▒╝`         `╙║▓▓▓▓▓▓▓███▓▒░/Ñ▒▒╢▓▓▒▒▓▓▓█▓,  
  ╚┘#Ñ╢▒▒▒▒▒▒▒▒▒▒▒▒▓█▓▓▓▓█▒▓▓██▓▒▀                └╫█▓▓██████▒▒▒M╪Ñ▒▒▓▒▒▒▓▓██▓  
 │ú╠╜╠▒▒▒▒▒▒▒▒▒▒▓█▓▒▒╙┘7▄»≈»▒▓▓▒▓      `╢▓▄.     ┌N▓██▒▓▓███▀▓█▓▓▒▒▒▒▓▒▒▒▒▓▓█▓, 
 ▒,BH║▒▒▒▒▒▒▒▓▓▒█▒▒▒m▒▒▓██▓▓▓▓█▌     ½╗J╫▓▓▀Ñ╓#▓█▓▓█████████▓╫▓████▓▓▓▒▒╫╫▒▓█▓▓ 
 1─▐░╢▒▒▒▒▒▒▒▒▒▒█▓▓▓▓▓▓▓▓▀▀█▀▓┘        º`    █▌║╫█▓████▓▓█▓▒▓████▓███▓▓▒╫╢▒▓▓▓▒ 
 «U⌠#▒▒▒▒▒▒▒▒▒▓▒▓███▓█▒▓█▒├Ñ╚                ▌└▀██▓▓████▓▒╙▀╢▓█████████▓▒▒▒▓▓▓▒ 
 ║.║▐▒▒▒▓▓▒▒▒▓▓▓█║█▌▀▓▓▓▓██▓             .  ,▓ :┤╢▒████▓▓█▓▓▒▓▓▒▓▓█████▓▒▒▒▒▓▓╠ 
 ÑÇ▒▒▒▓▒▓▓▒▒▒▒▓▓█å╩▓▓▒▀██▌▓█              `▀▀▒╠NN╠╫███▀▒██████▓▓████████▓▒▒▒▓▒┤ 
 │▒▓▓▒▓▓▓▓▓▒▒▒▒▓▓▓▓▓█▓╬████▀          .»M»#╡╠╠║╠║▒████▒▓███▀▒▒▓██▒▓█████▓▒▒▒▓╬╠ 
  ╠▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▓▓█▓▓▒▓▓▓,          █████▒╠║▒▒▓██████▓▓▓╓▒▒▓█▓▓██████▓▒▒▒▓▒╩  
  │╪║▓▓▓▓▓▓▓▓▓▓▒▓▓▒▀▓▒▒██▓▓▓▒▄.       ╙╠▀██▒▒▒▓███████████▒▒█▌▒████████▓▒▒▒▓▒╬  
   ║▓▓▓▓▓▓▓▓▓▓▓▓▒▒▓███Ω▓▓▒▓▒▓▒▓▒▄      M#▓▒▓▓████▓▓██▓▓███╢║║▀ÜÑ╚████▓▓▒▒▒▓╣║   
    ▓▓▓▒▓▓▓▓▓▓▓▓▓████▓▒▒▓▓▓▓▓▒▒▓█▓▒~,,yy╠▒███████▓▓▓█▓▒▓█▌╓▓▓║▓█████▓▓▒▒▒▓▓▒╚   
     ▓▓▓▓▓▓▓▓▓█▓██▓▒▒▒▓▓▓╜▓▓▓▒▓▓▓▓▓▓███████▀╠▒╫████▓▓║▒▓█▌╡▒▓█████▓▓▓▒▒▒▓▓▒╝    
      ▓▓█▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▀∩▒▓▓▒▓▒▒█▓▓▓██████µ╠▒███▀▀▀╢▒▓█████████▓▓▒▒▒▒▒▓▓╜╙     
       ▀███▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓▓▒▒▒▓▓█████████▒╠#╗▄╫▒▓███▀██████▓▓▒▒▒▒▒▓▓▒▒'      
        "███▓▓▓▓▓▓▓▓▓▓▒▒▒▓Ñ╚▀▓▓▒▓▓▓████▓▓▒▒▓▓██████████É╢████▓▓▒▒╢▒▒▀▓▓╝        
          ╙▓█▓▓▓▓▓▓▓▓▓▒▒▒▓▒▒#» ╚▓▒▓██▓▓▒╠╠╠Ñ╠╠▒▒▒▓▓▓▓▓▓▒▒╠▓▓▓▒▒╢║▒▓▓▓▓          
            ╙▓▓▓▓▓▓▓▓▓▒▓▓▒▒▓   │▓▓██▓▌║Ñ┤Ñ│├░├░╚Ñ╠╠╢▒║ÑÑÑ:╠║╢╫╫▓▓▒▒▌            
              "▀▓▓▓▓▓▒▒▓▓▓▒▌.»»╫▓▓▓▓▒Ñ∩Ñ│Ñ∩∩│∩└┐∩└J░└└└│┤╠╠╢▓▓▓▓▓▀              
                 º▀▓▓▓▓▓▓▒▒▒▒▒▒▒▓▓▓▒▒╔∩│∩∩∩L∩²(,.┌└├░⌠QN╢╫▒╫▒▒▀`                
                    `╜▓▓▒▒▓▒▒▒▒▒▓▒▓▒ÑÑ└╔∩∩⌠│∩∩NQ╔N║╢▒▒▒▒▀▓▒º                    
                         º╜╚▒▒▒║╩║╠╚╙m┤╠╙╩╢▒▒▒▒▒▒▒▓╬▓╝╜"                        
                                ``º└└╚╘└╚╚╚╚╜╜ºº"                               """
		self.prompt = '> '
		self.timing = True
		self.load_modules_info()

	def load_modules_info(self):
		self.modules = parse_config_file()
	
	def list_of_projects(self, text, line, begidx, endidx):
		return [project["project"] for project in self.db.projects.find() if project["project"].startswith(text)]
	
	set_project_parser = argparse.ArgumentParser()
	set_project_parser.add_argument('project', help='name of a project', completer_method=list_of_projects)
	@cmd2.with_argparser(set_project_parser)
	def do_set_project(self, args):
		"""Sets a project to work with."""
		project = args.project
		project_collection = self.db.projects
		if project_collection.find_one({"project": project}) == None:
			project_collection.insert_one({"project": project})
		self.project = project
		self.prompt = '(' + project + ') > '

	def do_list_projects(self, args):
		"""Lists all the projects already created."""
		for project in self.db.projects.find():
			print(project["project"])

	delete_project_parser = argparse.ArgumentParser()
	delete_project_parser.add_argument('project', help='name of a project', completer_method=list_of_projects)
	@cmd2.with_argparser(delete_project_parser)
	def do_delete_project(self, args):
		"""Deletes the specified project."""
		project = args.project
		project_collection = self.db.projects
		project_collection.remove({"project": project})
		self.db[project + ".domains"].drop()
		self.db[project + ".ips"].drop()

	def list_modules(self, text, line, begidx, endidx):
		return [module["name"] for category in self.modules for module in category["modules"] if module["name"].startswith(text)]
	 
	def do_list_modules(self, args):
		"""Lists availble modules."""
		for category in self.modules:
			print("---------------------------")
			print(category["category"].upper())
			print("---------------------------")
			for module in category["modules"]:
				print(module["name"].lower())
	
	run_module_parser = argparse.ArgumentParser()
	run_module_parser.add_argument('module', help='module to run', completer_method=list_modules)
	@cmd2.with_argparser(run_module_parser)
	def do_run_module(self, args):
		if self.check_project_to_be_set():
			module = importlib.import_module("modules." + args.module)
			module.run(self.db, self.project)

	def check_project_to_be_set(self):
		if self.project is not None:
			return True
		else:
			print("specify a project first (set_project)")
			return False

	set_top_level_domain_parser = argparse.ArgumentParser()
	set_top_level_domain_parser.add_argument('domain', help='top level domain to add')
	@cmd2.with_argparser(set_top_level_domain_parser)
	def do_set_top_level_domain(self, args):
		"""Adds top level domain to DB"""
		if self.check_project_to_be_set():
			domain = self.db[self.project + ".domains"].find_one({ "domain": args.domain })
			if domain == None:
				self.db[self.project + ".domains"].insert_one({ "domain": args.domain, "found_from": [ "manually" ], "top_level": True})
			else:
				self.db[self.project + ".domains"].update_one({ "domain": args.domain }, {'$set': { "top_level": True }})
				
	set_ooc_domain_parser = argparse.ArgumentParser()
	set_ooc_domain_parser.add_argument('domain', help='out of scope domain to set')
	@cmd2.with_argparser(set_ooc_domain_parser)
	def do_set_ooc_domain(self, args):
		"""Sets domain as out of scope"""
		if self.check_project_to_be_set():
			domain = self.db[self.project + ".domains"].find_one({ "domain": args.domain })
			if domain == None:
				self.db[self.project + ".domains"].insert_one({ "domain": args.domain, "found_from": [ "manually" ], "out_of_scope": True})
			else:
				self.db[self.project + ".domains"].update_one({ "domain": args.domain }, {'$set': { "out_of_scope": True }})

	set_company_name_parser = argparse.ArgumentParser()
	set_company_name_parser.add_argument('company', help='company name to add')
	@cmd2.with_argparser(set_company_name_parser)
	def do_set_company_name(self, args):
		"""Adds company name to DB"""
		if self.check_project_to_be_set():
			project = self.db["projects"].find_one({ "project": self.project })
			if "company_names" not in project:
				self.db["projects"].update_one({ "project": self.project }, {'$set': { "company_names": [ args.company ] } })
			elif args.company not in project["company_names"]:
				self.db["projects"].update_one({ "project": self.project }, {'$push': { "company_names": args.company } })

	def do_exit(self, args):
		"""Exits the program."""
		print("nya, bye")
		return True

if __name__ == '__main__':
	cli = gorgon_cli()
	cli.cmdloop()
