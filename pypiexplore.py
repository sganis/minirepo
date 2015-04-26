#!/usr/bin/env python
#
# download all source packages from https://pypi.python.org

import sys
import os
import time
import yaml

def main():
	start = time.time()

	with open('pypilist.json') as r:
		packages = yaml.load(r)

	total = 0
	combinations = {}
	pyversions = {}
	packagetypes = {}
	extensions = {}
	for p in packages:
		total += 1
		info = p['info']
		urls = p['urls']
		for u in urls:
			extension = u['filename'].split('.')[-1]
			if extension not in extensions:
				extensions[extension] = extension
			packagetype = u['packagetype']
			if packagetype not in packagetypes:
				packagetypes[packagetype] = packagetype
			python_version = u['python_version']
			if python_version not in pyversions:
				pyversions[python_version] = python_version

			key = '%s %s %s' % (python_version, packagetype , extension)
			if key not in combinations:
				combinations[key] = [u['filename'],0]
			combinations[key][1] += 1

	print "Total packages:", total
	print "Pyton versions:", sorted(pyversions)
	print "Package types:", sorted(packagetypes)
	print "Extensions:", sorted(extensions)
	
	print "Combinations:"

	i = 0
	for t in sorted(combinations):
		i += 1
		# print '%3d) %-30s [packages: %6d]' % (i, t, combinations[t][1])
		print '%s,%s,%s' % (i, t, combinations[t][1])

	print 'time:', (time.time()-start)




if __name__ == '__main__':
	main()