#!/usr/bin/env python
#
# download json database

import sys
import os
import re
import urllib2
import json
import time
import random
import multiprocessing as mp
import minirepo


def worker(names):
	package = None
	pid = os.getpid()
	wfile = 'worker.%s' % pid
	print 'starting worker file %s...' % wfile
	i = 0
	with open(wfile, 'a') as a:
		for p in names:
			try:
				json_url = 'https://pypi.python.org/pypi/%s/json' % p
				js = urllib2.urlopen(json_url, timeout=10).read()
			except urllib2.HTTPError, ex:
				# ignore broken links
				if ex.code==404:
					continue
				print 'HTTP Error: Failed to get json %s: %s' % (json_url, ex)
			except Exception, ex:
				print 'Failed to get json from %s, error: %s' % (json_url, ex)
			a.write('%s,\n' % js)
			# i+=1
			# if i==20:
			# 	break
	return pid



def main():
	start = time.time()
	names = minirepo.get_names()
	N = 10
	pool = mp.Pool(N)
	random.shuffle(names)
	chunks = list(minirepo.get_chunks(names, N))
	processes = pool.map_async(worker, chunks).get(timeout=99999)
	
	# save database
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