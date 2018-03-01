#!/usr/bin/env python
#
# download all source packages from https://pypi.python.org
import sys
import os
import time
import shutil
import random
import hashlib
import logging
import tempfile
import json
import requests
import multiprocessing as mp
from xml.etree import ElementTree

# logging.basicConfig(level=logging.INFO)

# global variables
# repository folder
REPOSITORY = ''
# temp folder, is needed for temporary files created by parallel processes
TEMP = tempfile.mkdtemp()
# download a max number of packages, useful for testing
MAX = 0
# number of processes to run in parallel
PROCESSES = 10

# filters, only interested in this types
PYTHON_VERSIONS = [
	'2', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.7.6', 
	'3', '3.0', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', 
	'cp26', 'cp27', 'cp3', 'cp32', 'cp33', 'cp34', 'cp35', 
	'cp36', 'cp37', 'py2', 'py2.py3', 'py26', 'py27', 'py3', 
	'py3.5', 'py3.6', 'py3.7', 'py32, py33, py34', 'py35', 'py36', 
	'py37', 'source', 'any']
PACKAGE_TYPES = ['bdist_egg', 'bdist_wheel', 'sdist']
EXTENSIONS = [ 'bz2', 'egg', 'exe', 'gz', 'tgz', 'whl', 'zip']
PLATFORMS = ['linux', 'win32', 'win_amd64', 'macosx']

# only python 3.7 for windows x64
PYTHON_VERSIONS = ['cp37','py3','py2.py3','py3.7','py37','any']
PACKAGE_TYPES = ['bdist_wheel',]
EXTENSIONS = ['whl',]
PLATFORMS = ['win_amd64',]

# I had to do this to setup max_retries in requests
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=2)
session.mount('https://', adapter)

def bytes_human(num):
	for x in ['bytes','KB','MB','GB']:
		if num < 1024.0:
			return "%3.1f%s" % (num, x)
		num /= 1024.0
	return "%3.1f%s" % (num, 'TB')

def get_names():
	# xmlrpc is slower
	# import xmlrpclib
	# xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
	# return client.list_packages()
    
    # use simple API
    # resp = urllib2.urlopen('https://pypi.python.org/simple')
    # tree = ElementTree.parse(resp)
    resp = requests.get('https://pypi.python.org/simple')
    tree = ElementTree.fromstring(resp.content)
    return [a.text for a in tree.iter('a')]

def get_chunks(seq, num):
	"""split seq in chunks of size num,
	used to divide tasks for workers
	"""
	avg = len(seq)/float(num)
	out = []
	last = 0.0
	while last < len(seq):
		out.append(seq[int(last):int(last + avg)])
		last += avg
	return out

def prune(releases, current_version):
	'''
	delete all versions different that current_version
	and return bytes deleted
	'''
	bytes = 0
	for v, dist_list in releases.items():
		if v == current_version:
			continue
		for dist in dist_list:
			path = '%s/%s' % (REPOSITORY, dist['filename']) 
			if os.path.exists(path):
				bytes += os.stat(path).st_size
				os.remove(path)
				logging.warning('Deleted   : %s' % dist['filename'])
	return bytes

def worker(names):
	'''
	function to run in parallel, names is a list of packages names,
	return tuple (pid, total packages, total bytes, total bytes cleaned)
	'''
	package = None
	pid = os.getpid()
	wname = TEMP + '/worker.%s' % pid
	print('starting worker file %s...' % wname)

	afile = open(wname, 'a')

	i = 0
	total = 1.0*len(names)
	packages_downloaded = 0
	bytes_downloaded = 0
	bytes_cleaned = 0
	
	for p in names:	
		try:
			i+=1
			json_url = 'https://pypi.python.org/pypi/%s/json' % p
			resp = session.get(json_url, timeout=30)

			if not resp.status_code == requests.codes.ok:
				resp.raise_for_status()

			# get json
			package = resp.json()		
			
			# write json info
			json.dump(package, afile, indent=3)
			afile.write(',\n')

		except Exception as ex:
			if not 'Not Found' in repr(ex):
				logging.error('%s: %s' % (json_url, ex))
				# time.sleep(random.uniform(1.0,2.5))
			continue

		info 	= package['info']
		name 	= info['name']
		version = info['version']

		# delete old versions if they are local
		bytes_cleaned += prune(package['releases'], version)

		
		for url in package['urls']:
			filename 		= url['filename']
			packagetype 	= url['packagetype']
			python_version  = url['python_version']
			download_url 	= url['url']						
			size 			= url['size']
			md5_digest 		= url['md5_digest']			
			
			if python_version not in PYTHON_VERSIONS:
				logging.info('Skipping python version %s: %s...' % (python_version, filename))
				continue
	
			
			if packagetype not in PACKAGE_TYPES:
				logging.info('Skipping package type %s: %s...' % (packagetype, filename))
				continue
			
			extention = ''
			if '.' in filename:
				extension = filename.split('.')[-1]
			if extension not in EXTENSIONS:
				logging.info('Skipping extension %s: %s...' % (extension, filename))
				continue

			if len([p for p in PLATFORMS if not p in filename]) > 0:
				logging.info('Skipping package patform.')
				continue

			# if 'macosx' in filename or 'linux' in filename: # macosx package
			# 	print(filename)
			# 	assert False
			


			# skip if already in repo
			path = '%s/%s' % (REPOSITORY, filename)
			if os.path.exists(path) and os.lstat(path).st_size == size:
				logging.info('Already local: %s' % filename)
				continue
			
			try:
				resp = session.get(download_url, timeout=300)
				if not resp.status_code == requests.codes.ok:
					resp.raise_for_status()
				
				# save file
				with open(path,'wb') as w:
					w.write(resp.content)
				
				# sum total bytes and count
				bytes_downloaded += size
				packages_downloaded += 1

				# verify with md5
				check = 'Ok' if hashlib.md5(resp.content).hexdigest() == md5_digest else 'md5 failed'
				progress = int(i/total*100.0)
				logging.warning('Downloaded: %-50s %s pid:%s %s%% [%s/%s]' % (filename,check,pid,progress,i,total))
				
			except Exception as ex:
				logging.error('Failed    : %s. %s' % (download_url, ex))
			
		# for testing, a minimal number of downloads will be specified
		if MAX > 0 and i==MAX:
			break

	afile.close()
	return (pid, packages_downloaded, bytes_downloaded, bytes_cleaned)

def get_config():
	config_file = os.path.expanduser("~/.minirepo")
	repository = "/home/minirepo"
	processes = 10
	try:
		config 	= json.load(open(config_file))
	except:
		newrepo = raw_input('Repository folder [%s]: ' % repository)
		if newrepo:
			repository = newrepo
		newprocesses = raw_input('Number of processes [%s]: ' % processes)
		if newprocesses:
			processes = newprocesses
		config = {}
		config["repository"]		= repository
		config["processes"]			= processes
		config["python_versions"]	= PYTHON_VERSIONS
		config["package_types"]		= PACKAGE_TYPES
		config["extensions"]		= EXTENSIONS

		with open(config_file, 'w') as w:
			json.dump(config, w, indent=2)

	for c in sorted(config):
		print('%-15s = %s' % (c,config[c]))
	print('Using config file %s ' % config_file)

	return config

def save_json(pids):
	# concatenate output from each worker
	db = REPOSITORY + '/packages.json'
	with open(db,'w') as w:
		w.write('[\n')
		for pid in pids:
			wfile = TEMP + '/worker.%s' % pid
			with open(wfile) as r:
				w.write(r.read())
			os.remove(wfile)
			print('deleted: %s' % wfile)
	
	# remove tailing comma, remove last 2 characters (',\n')
	with open(db, 'rb+') as w:
		w.seek(-2, os.SEEK_END)
		w.truncate()

	# complete json list
	with open(db, 'a') as a:
		a.write('\n]\n')

# def make_tarfile(tarfilename, directory):
# 	import tarfile
#     with tarfile.open(tarfilename, "w") as tar:
#         tar.add(directory, arcname=os.path.basename(os.path.realpath(directory)))



def main(repository='', processes=0):
	global REPOSITORY,PROCESSES,PYTHON_VERSIONS,PACKAGE_TYPES,EXTENSIONS
	
	print('/******** Minirepo ********/')
	
	# get configuraiton values
	config 			= get_config()
	REPOSITORY		= config["repository"]
	PROCESSES		= config["processes"]
	PYTHON_VERSIONS	= config["python_versions"]
	PACKAGE_TYPES	= config["package_types"]
	EXTENSIONS		= config["extensions"]
	
	# overwrite with paramerer
	if repository: 		
		REPOSITORY = repository
		print('Overriten:\nrepository      = %s' % repository)
	if processes:	
		PROCESSES = processes
		print('Overriten:\nprocesses       = %s' % processes)


	assert REPOSITORY
	assert PROCESSES

	if not os.path.isdir(REPOSITORY):
		os.mkdir(REPOSITORY)

	assert os.path.isdir(REPOSITORY)

	logging.basicConfig(
		level=logging.WARNING, 
		format="%(asctime)s:%(levelname)s: %(message)s")
	
	logging.warning('starting minirepo mirror...')
	start = time.time()	

	# prepare
	names = get_names()
	pool = mp.Pool(int(PROCESSES))
	random.shuffle(names)
	chunks = list(get_chunks(names, PROCESSES))
	
	# run in parallel
	# (pids, totals, bytes, cleaned)
	results = pool.map_async(worker, chunks).get(timeout=99999)
	
	# get summary
	pids 				= [r[0] for r in results]
	packages_downloaded = sum([r[1] for r in results])
	bytes_downloaded 	= sum([r[2] for r in results])
	bytes_cleaned 		= sum([r[3] for r in results])

	# store full list of packages in json format for later analysis
	save_json(pids)

	# cleanup
	shutil.rmtree(TEMP)
	logging.warning('temp folder deleted: %s' % TEMP)


	# print summary
	print('summary:')
	print('packages downloaded = %s' % packages_downloaded)
	print('bytes downloaded    = %s' % bytes_human(bytes_downloaded))
	print('bytes cleaned       = %s' % bytes_human(bytes_cleaned))
	
	print('time:', (time.time()-start))

	# logging.warning('making tar file...')
	# tar = '/home/minirepo.tar'
	# make_tarfile(tar, REPOSITORY)
	logging.warning('minirepo mirror completed.')
	


if __name__ == '__main__':
	main()
