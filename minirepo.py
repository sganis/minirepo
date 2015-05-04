#!/usr/bin/env python
#
# download all source packages from https://pypi.python.org

import sys
import os
import re
import urllib2
import json
import time
import random
import multiprocessing as mp
import hashlib
import requests

REPO = '/home/user/repo/minirepo'

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
	def __init__(self, info):
		self.name = info['name']
		self.version = info['version']
		self.url = ''
		self.filename = ''
		self.size = 0
		self.md5_digest = ''
		self.extension = ''

def worker(packages_names):
	packages = []
	package = None
	for p in packages_names:
		try:
			json_url = 'https://pypi.python.org/pypi/%s/json' % p
			js = urllib2.urlopen(json_url, timeout=10).read()
			package = json.loads(js)			
		except urllib2.HTTPError, ex:
			if ex.code==404:
				continue
			print 'HTTP Error: Failed to get json %s: %s' % (json_url, ex)
			continue
		except Exception, ex:
			print 'Failed to get json from %s, error: %s' % (json_url, ex)
			continue
		
		pak = Package(package['info'])

		for url in package['urls']:
			if url['python_version'] != 'source':	
				continue
			pak.url = url['url']
			pak.size = url['size']
			pak.filename = url['filename']
			if '.' in pak.filename:
				pak.extension = os.path.splitext(pak.filename)[1]
			pak.md5_digest = url['md5_digest']
			packages.append(pak)
			path = '%s/%s' % (REPO, pak.filename)
			if os.path.exists(path) and os.lstat(path).st_size == pak.size:
				# print 'Already local: %s' % pak.filename
				break
			if not pak.extension in ['gz','bz2','zip']:
				continue
			try:
				data = urllib2.urlopen(pak.url, timeout=300).read()
				# data = requests.get(pak.url, timeout=60).raw.read()
				with open(path,'wb') as w:
					w.write(data)
				print 'Downloaded: %s' % pak.filename,
				if hashlib.md5(data).hexdigest() == pak.md5_digest: 	
					print 'OK'
				else:						
					print 'Check failed'
			except Exception, ex:
				print 'Faild to download %s: %s' % (pak.url, ex)
			break

	return packages

def main():
	start = time.time()
	response = urllib2.urlopen('https://pypi.python.org/simple')
	html = response.read()
	pattern = re.compile(r"href='[\w\d_\.-]+'>[^<]+")
	captures = pattern.findall(html)
	packages_names = sorted([c.split('>')[1] for c in captures])
	N = 20
	pool = mp.Pool(N)
	random.shuffle(packages_names)
	chunks = list(get_chunks(packages_names, N))
	packages = pool.map_async(worker, chunks).get(timeout=99999)
	with open('packages.txt','w') as w:
		for pak in packages:
			for p in pak:
				w.write('%s\n' % p.url)
	print 'time:', (time.time()-start)



if __name__ == '__main__':
	main()