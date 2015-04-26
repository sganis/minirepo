#!/usr/bin/env python
#
# download all source packages from https://pypi.python.org

import sys
import os
import re
# import urllib2
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

class Package(object):
	def __init__(self):
		self.name = ''
		self.version = ''
		self.url = ''
		self.filename = ''
		self.size = 0
		self.md5_digest = ''
		self.python_version = ''
		self.packagetype = ''

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
	packages = []
	package = None
	for p in names:
		try:
			json_url = 'https://pypi.python.org/pypi/%s/json' % p
			# js = urllib2.urlopen(json_url, timeout=10).read()
			# package = json.loads(js)			
			resp = requests.get(json_url, timeout=10)
			if not resp.status_code == requests.codes.ok:
				continue
				# resp.raise_for_status()
			
			# package = json.loads(resp.content)			
			package = resp.json()		
		
		except Exception, ex:
			logging.error('Failed to get json from %s, error: %s' % (json_url, ex))
		
		# delete old versions if they are local
		prune(package['releases'], package['info']['version'])

		pak = Package()
		info = package['info']
		
		for url in package['urls']:
			pak.filename 		= url['filename']
			pak.packagetype 	= url['packagetype']
			pak.python_version  = url['python_version']
			
			if pak.python_version not in PYTHON_VERSIONS:
				logging.debug('Skipping python version %s: %s...' % (pak.python_version, pak.filename))
				continue
			
			
			if pak.packagetype not in PACKAGE_TYPES:
				logging.debug('Skipping package type %s: %s...' % (pak.packagetype, pak.filename))
				continue
			
			
			extention = ''
			if '.' in pak.filename:
				extension = pak.filename.split('.')[-1]
			if extension not in EXTENSIONS:
				logging.debug('Skipping extension %s: %s...' % (extension, pak.filename))
				continue

			pak.name 		= info['name']
			pak.url 		= url['url']						
			pak.version 	= info['version']
			pak.size 		= url['size']
			pak.md5_digest 	= url['md5_digest']			
			packages.append(pak)

			# skip if already in repo
			path = '%s/%s' % (REPO, pak.filename)
			if os.path.exists(path) and os.lstat(path).st_size == pak.size:
				logging.debug('Already local: %s' % pak.filename)
				continue
			
			try:
				# data = urllib2.urlopen(pak.url, timeout=300).read()
				resp = requests.get(pak.url, timeout=300)
				if not resp.status_code == requests.codes.ok:
					resp.raise_for_status()

				data = resp.content
				with open(path,'wb') as w:
					w.write(data)
				
				# verify with md5
				check = 'Ok' if hashlib.md5(data).hexdigest() == pak.md5_digest else 'md5 failed'
				logging.warning('Downloaded: %-60s %s' % (pak.filename,check))
				
			except Exception, ex:
				logging.error('Faild to download %s: %s' % (pak.url, ex))
			

	return packages


def main():
	logging.basicConfig(level=logging.WARNING)
	start = time.time()
	# response = urllib2.urlopen('https://pypi.python.org/simple')
	# html = response.read()
	# pattern = re.compile(r"href='[\w\d_\.-]+'>[^<]+")
	# captures = pattern.findall(html)
	# names = sorted([c.split('>')[1] for c in captures])
	
	names = get_names()

	N = 20

	pool = mp.Pool(N)
	random.shuffle(names)
	chunks = list(get_chunks(names, N))
	packages = pool.map_async(worker, chunks).get(timeout=99999)
	
	# save database
	packages_dic = {}
	for pak in packages:
		for p in pak:
			if p.name:
				packages_dic[p.name] = p.__dict__
	with open('packages.json','w') as w:
		json.dump(packages_dic, w, indent=2, sort_keys=True)

	print 'time:', (time.time()-start)




if __name__ == '__main__':
	main()