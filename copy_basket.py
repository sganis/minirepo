#!/usr/bin/env python
#
# filter latest package source from mirror
import sys
import subprocess
import shutil

cmd = 'find /home/user/repo/pypi/web/packages/source'
packages = subprocess.check_output(cmd.split()).split()
DST = '/home/user/.basket/'

def to_int(s):
	try:
		return int(s)
	except:
		return [ord(c) for c in str(s)]

class Package(object):
	def __init__(self, path):
		self.path = path
		self.name = ''
		self.version = []
		self.extension = ''
		if not path.startswith('/'):
			return
		f = path.split('/')[-1]		
		self.extension = f.split('.')[-1]
		if self.extension in ['gz','zip','tgz','bz2']:
			aux = f.split('-')
			if len(aux)>1:
				self.name = aux[0]
				self.version = aux[1].strip('.'+self.extension).strip('.tar').strip('.').split('.')
			if len(aux)>2:
				if aux[1] and aux[1][0] not in '0123456789':
					self.name += '-' + aux[1]
					self.version = aux[2].strip('.'+self.extension).strip('.tar').strip('.').split('.')
			if len(aux)>3:
				if aux[2] and aux[2][0] not in '0123456789':
					self.name += '-' + aux[2]
					self.version = aux[3].strip('.'+self.extension).strip('.tar').strip('.').split('.')
			self.version = [to_int(i) for i in self.version]
						
	def to_string(self):
		return self.name + ' ' + str(self.version) +' '+ self.path

packages = [Package(p) for p in packages]

latest = {}
for p in packages:
	if p.name not in latest:
		# print 'added to dict:', p.name, p.version
		latest[p.name] = p
	# print '\t' + p.name +' '+ str(p.version)
	if p.version > latest[p.name].version:		
		latest[p.name] = p
		# print '\t\tnew version for', p.name, p.version


for p in sorted(latest.values()):
	if p.name:
		# print p.path
		shutil.copy(p.path, DST)
