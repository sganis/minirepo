import os
import tempfile
import shutil
import minirepo

def test():
	# logging.basicConfig(level=logging.DEBUG)
	minirepo.REPO = tempfile.mkdtemp()
	minirepo.MAX = 1
	minirepo.PROCESSES = 2
	print ('repo will be', minirepo.REPO)
	minirepo.main()
	if len(os.listdir(minirepo.REPO))==2:
		print('test Ok')
	else:
		print('test failed')
	shutil.rmtree(minirepo.REPO)

if __name__ == '__main__':
	test()
	# main()