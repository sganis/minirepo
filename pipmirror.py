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
	def __init__(self):
		self.name = ''
		self.version = ''
		self.url = ''
		self.filename = ''
		self.size = 0
		self.md5_digest = ''


def worker(packages_names):
	packages = []
	package = None
	for p in packages_names:
		try:
			resp = urllib2.urlopen('https://pypi.python.org/pypi/%s/json' % p)
			js = resp.read()
			package = json.loads(js)
		except Exception, ex:
			print ex
		if not package:
			continue
		pak = Package()
		pak.name = package['info']['name']
		pak.version = package['info']['version']
		urls = package['urls']
		for url in urls:
			if url['python_version'] != 'source':	
				continue
			pak.url = url['url']
			pak.size = url['size']
			pak.filename = url['filename']
			pak.md5_digest = url['md5_digest']
			packages.append(pak)
			path = '%s/%s' % (REPO, pak.filename)
			if os.path.exists(path) and os.lstat(path).st_size == pak.size:
				print 'Already local: %s' % pak.filename
				break
			try:
				data = urllib2.urlopen(pak.url).read()
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
	N = 50
	pool = mp.Pool(N)
	random.shuffle(packages_names)
	chunks = list(get_chunks(packages_names, N))
	packages = pool.map(worker, chunks)
	with open('packages.txt','w') as w:
		for pak in packages:
			for p in pak:
				w.write('%s\n' % p.url)
	print 'time:', (time.time()-start)


if __name__ == '__main__':
	main()