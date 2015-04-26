#!/usr/bin/env python
#
# download all source packages from https://pypi.python.org

import sys
import re
import urllib2
import subprocess
# import multiprocessing as mp

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

response = urllib2.urlopen('https://pypi.python.org/simple')
html = response.read()

# pattern = re.compile(r'href=[^>]+')
pattern = re.compile(r"href='[\w\d_\.-]+'>[^<]+")
captures = pattern.findall(html)

# with open('packages.html', 'w') as w: 
# 	w.write(html)

# with open('captures.txt', 'w') as w: 
# 	w.write('\n'.join(captures))

packages = sorted([c.split('>')[1] for c in captures])

# with open('packages.txt', 'w') as w: 
# 	w.write('\n'.join(packages))

# print len(packages), 'packages'

# for p in packages:
# 	cmd  = 'basket update ' + p
# 	print cmd
# 	subprocess.call(cmd.split())

cmd = 'basket download ' + ' '.join(packages)
print cmd
subprocess.call(cmd.split())


# chunks = get_chunks(packages, 4)
# pool = mp.Pool(int(NP))
# pool.map(worker, chunks)

# for i in range(4):
# 	print chunks[i]
# 	cmd  = 'basket download ' + ' '.join(sorted(chunks[i], reverse=True))
# 	p = subprocess.call(cmd.split())



