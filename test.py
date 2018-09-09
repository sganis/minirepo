import os
import tempfile
import shutil
import json
import logging
import minirepo

def test():
	logging.basicConfig(level=logging.DEBUG)
	repository = tempfile.mkdtemp()
	minirepo.MAX = 1
	processes = 2
	print ('repo will be', repository)
	
	minirepo.main(repository, processes)

	files = os.listdir(repository)
	print(files)
	if len(files)==3:
		print('test Ok')
	else:		
		print('test failed')

	db = repository + '/packages.json'
	with open(db) as r:
		packages = json.load(r)
	assert packages

	shutil.rmtree(repository)
	print('done')

if __name__ == '__main__':
	test()
	# main()