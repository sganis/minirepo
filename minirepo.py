#!/usr/bin/env python
#
# download all source packages from https://pypi.python.org

import sys
import os
import requests
import json
import time
import random
import multiprocessing as mp
import hashlib
import logging
from xml.etree import ElementTree

REPO = '/home/user/repo/minirepo'

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
	for v, dist_list in releases.iteritems():
		if v == current_version:
			continue
		for dist in dist_list:
			path = '%s/%s' % (REPO, dist['filename']) 
			if os.path.exists(path):
				os.remove(path)
				logging.info('Deleted %s' % dist['filename'])


def worker(names):
	package = None
	pid = os.getpid()
	wname = 'worker.%s' % pid
	print 'starting worker file %s...' % wname
	afile = open(wname, 'a')

	for p in names:
		try:
			json_url = 'https://pypi.python.org/pypi/%s/json' % p
			resp = requests.get(json_url, timeout=10)
			if not resp.status_code == requests.codes.ok:
				continue
			package = resp.json()		
		
		except Exception, ex:
			logging.error('Failed to get json from %s, error: %s' % (json_url, ex))
		
		# delete old versions if they are local
		prune(package['releases'], package['info']['version'])

		# pak = Package()
		info = package['info']
		
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

			name 			= info['name']
			download_url 	= url['url']						
			version 		= info['version']
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
				afile.write('%s,\n' % resp.json())
				
				# save file
				with open(path,'wb') as w:
					w.write(resp.content)
				
				# verify with md5
				check = 'Ok' if hashlib.md5(resp.content).hexdigest() == md5_digest else 'md5 failed'
				logging.warning('Downloaded: %-60s %s' % (filename,check))
				
			except Exception, ex:
				logging.error('Faild to download %s: %s' % (download_url, ex))
	
	afile.close()	
	return pid


def main():
	logging.basicConfig(level=logging.WARNING)
	start = time.time()
	
	names = get_names()

	N = 5
	pool = mp.Pool(N)
	random.shuffle(names)
	chunks = list(get_chunks(names, N))
	processes = pool.map_async(worker, chunks).get(timeout=99999)
	
	# save json database
	packages_list = []
	with open('pypilist.json','w') as w:
		w.write('[\n')
		for pid in processes:
			wfile = 'worker.%s' % pid
			with open(wfile) as r:
				w.write(r.read())
			os.remove(wfile)
		w.write(']\n')

	print 'time:', (time.time()-start)




if __name__ == '__main__':
	main()