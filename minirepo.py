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

REPO = os.path.expanduser("~/minirepo")
TEMP = tempfile.mkdtemp()
MAX = 0
PROCESSES = 5

# PYTHON_VERSIONS = ['2', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.7.6', '3.0', '3.1', '3.2', '3.3', '3.4', '3.5', 'any', 'cp25', 'cp26', 'cp27', 'cp31', 'cp32', 'cp33', 'cp34', 'cp35', 'image/tools/scikit_image', 'py2', 'py2.py3', 'py2.py3.cp26.cp27.cp32.cp33.cp34.cp35.pp27.pp32', 'py2.py3.cp27.cp26.cp32.cp33.cp34.pp27', 'py26', 'py27', 'py27.py32.py33', 'py3', 'py32, py33, py34', 'py33', 'py34', 'python', 'source']
# PACKAGE_TYPES = ['bdist_dmg', 'bdist_dumb', 'bdist_egg', 'bdist_msi', 'bdist_rpm', 'bdist_wheel', 'bdist_wininst', 'sdist']
# EXTENSIONS = ['bz2', 'deb', 'dmg', 'egg', 'exe', 'gz', 'msi', 'rpm', 'tgz', 'whl', 'zip']

# only interested in this types
PYTHON_VERSIONS = ['2.7', 'any', 'cp27', 'py2', 'py2.py3', 'py27', 'source']
PACKAGE_TYPES = ['bdist_egg', 'bdist_wheel', 'sdist']
EXTENSIONS = ['bz2', 'egg', 'gz', 'tgz', 'whl', 'zip']


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
	for v, dist_list in releases.items():
		if v == current_version:
			continue
		for dist in dist_list:
			path = '%s/%s' % (REPO, dist['filename']) 
			if os.path.exists(path):
				os.remove(path)
				logging.warning('Deleted %s' % dist['filename'])


def worker(names):
	package = None
	pid = os.getpid()
	wname = TEMP + '/worker.%s' % pid
	print('starting worker file %s...' % wname)
	afile = open(wname, 'a')
	total = len(names)
	i = 0
	for p in names:	
		try:
			i+=1
			json_url = 'https://pypi.python.org/pypi/%s/json' % p
			resp = requests.get(json_url, timeout=10)

			if not resp.status_code == requests.codes.ok:
				continue
			package = resp.json()		
			
			# wait to avoid getting refused from server due to too many connections
			# if (i % 10) == 0:
			# 	time.sleep(random.uniform(1.0,2.5)) 
		
		except Exception as ex:
			logging.error('Failed to get json from %s, error: %s' % (json_url, ex))
			continue

		info 	= package['info']
		name 	= info['name']
		version = info['version']

		# delete old versions if they are local
		prune(package['releases'], version)

		
		for url in package['urls']:
			filename 		= url['filename']
			packagetype 	= url['packagetype']
			python_version  = url['python_version']
			
			if python_version not in PYTHON_VERSIONS:
				logging.debug('Skipping python version %s: %s...' % (python_version, filename))
				continue
			
			
			if packagetype not in PACKAGE_TYPES:
				logging.debug('Skipping package type %s: %s...' % (packagetype, filename))
				continue
			
			
			extention = ''
			if '.' in filename:
				extension = filename.split('.')[-1]
			if extension not in EXTENSIONS:
				logging.debug('Skipping extension %s: %s...' % (extension, filename))
				continue

			download_url 	= url['url']						
			size 			= url['size']
			md5_digest 		= url['md5_digest']			
			
			# skip if already in repo
			path = '%s/%s' % (REPO, filename)
			if os.path.exists(path) and os.lstat(path).st_size == size:
				logging.debug('Already local: %s' % filename)
				continue
			
			try:
				resp = requests.get(download_url, timeout=300)
				if not resp.status_code == requests.codes.ok:
					resp.raise_for_status()
				
				# write json info
				afile.write('%s,\n' % package)				

				# save file
				with open(path,'wb') as w:
					w.write(resp.content)
				
				# verify with md5
				check = 'Ok' if hashlib.md5(resp.content).hexdigest() == md5_digest else 'md5 failed'
				progress = int(i/float(total)/PROCESSES*100.0)
				logging.warning('Downloaded: %-60s %s process %s %s%% %s/%s' % (filename,check,pid,progress,i,int(total/float(PROCESSES))))
				
			except Exception as ex:
				logging.error('Faild to download %s: %s' % (download_url, ex))
			
		# for testing, a minimal number of downloads will be specified
		if MAX > 0 and i==MAX:
			break

	afile.close()	
	return pid


def get_config():
	global REPO, PROCESSES
	config_file = os.path.expanduser("~/.minirepo")
	try:
		config 		= json.load(open(config_file))
		REPO 		= config['repository']
		PROCESSES 	= config['processes']
	except:
		newrepo = raw_input('Repository folder [%s]: ' % REPO)
		if newrepo:
			REPO = newrepo
		newprocesses = raw_input('Number of processes [%s]: ' % PROCESSES)
		if newprocesses:
			PROCESSES = newprocesses
		config = {}
		config["repository"]=REPO
		config["processes"]=PROCESSES
		config["python_versions"]=PYTHON_VERSIONS
		config["package_types"]=PACKAGE_TYPES
		config["extensions"]=EXTENSIONS

		with open(config_file, 'w') as w:
			json.dump(config, w, indent=2)

	for c in sorted(config):
		print('%-15s = %s' % (c,config[c]))
	print('Using config file %s ' % config_file)

	return config


def main():
	print('/******** Minirepo ********/')
	config = get_config()
	if not os.path.isdir(REPO):
		os.mkdir(REPO)

	logging.basicConfig(level=logging.WARNING)
	start = time.time()	
	names = get_names()
	pool = mp.Pool(PROCESSES)
	random.shuffle(names)
	chunks = list(get_chunks(names, PROCESSES))
	pids = pool.map_async(worker, chunks).get(timeout=99999)
	
	# save json database
	packages_list = []
	with open(REPO + '/packages.json','w') as w:
		w.write('[\n')
		for pid in pids:
			wfile = TEMP + '/worker.%s' % pid
			with open(wfile) as r:
				w.write(r.read())
			os.remove(wfile)
		w.write(']\n')
	# cleanup
	shutil.rmtree(TEMP)
	print('time:', (time.time()-start))



if __name__ == '__main__':
	main()