.. _pypi.python.org: http://pypi.python.org
.. _pip: https://pip.pypa.io
.. _bandersnatch: https://pypi.python.org/pypi/bandersnatch
.. _basket: https://pypi.python.org/pypi/Basket
.. _pypi.python.org/pypi/minirepo: https://pypi.python.org/pypi/minirepo
.. _github: https://github.com/sganis/minirepo

********
Minirepo
********

Create a local pypi repository to use pip off-line.

.. contents:: 

Minirepo is a command-line program that downloads Python packages from pypi.python.org_, so you can use pip_ without internet. I needed to maintain a python repository in an isolated cluster environment, and after trying several tools to mirror pypi index, I dedided to make my own tool. 

Some mirroring tools such us bandersnatch_ didn't meet my requirements, because I wanted to do a selective mirror, only downlowing all sources for python 2.7, for example. Bandersnatch gets the full content, about 140GB at the time of my first version of minirepo.

Then I was inspired by basket_, which is almost what I wanted, but you need to specify the list of packages to download. I ended up using the json API to get the packages that I needed, and then calling basket to download or update the packages. In the end, that approach was slow and buggy, so I wrote this small program to do what I just needed. Now, my minirepo folder has about 12GB with only the latest packages, and it takes about 20 minutes to mirror.


Installation
============

Use pip
-------

The easiest way to install it is to use pip:

.. code:: bash

    $ pip install minirepo

Or download and install
-----------------------

Download the package file from https://pypi.python.org/pypi/minirepo, or the latest development version from https://github.com/sganis/minirepo, then:

.. code:: bash

    $ tar xvzf minirepo-1.0.3.tar.gz
    $ cd minirepo-1.0.3
    $ python setup.py install

You can also use git:

.. code:: bash

    $ git clone https://github.com/sganis/minirepo.git
    $ cd minirepo
    $ python setup.py install


Usage
=====

.. code::
	
	# run it from the command line:
	$ minirepo

	# or run the python script if you didn't install it:
	$ ./minirepo.py

The firt time it's executed, the program will ask you for the local repository path, which defaults to ~/minirepo in Linux. A json configuration file is created and saved as ~/.minirepo, that you can edit to your preferences. This configuration file looks like this:

.. code:: javascript

	{
		"processes"       : 20, 
		"repository"      : "/home/user/minirepo"
		"package_types"   : ["bdist_egg","bdist_wheel","sdist"], 
		"extensions"      : ["bz2","egg","gz","tgz","whl","zip"], 
		"python_versions" : ["2.7","any","cp27","py2","py27","source"], 
	}


Minirepo uses packages_types, extensions, and python_versions as filters. I was analysing the full list of packages available in pypi.python.org_, and it looks that all the options are something like the list below, you can try any other option. For me, I was only interested in python 2.7 packages, sources, wheels and eegs distributions, and some extensions.

.. code:: python

	PYTHON_VERSIONS = [
		'2', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.7.6', '3.0', '3.1', 
		'3.2', '3.3', '3.4', '3.5', 'any', 'cp25', 'cp26', 'cp27', 'cp31', 
		'cp32', 'cp33', 'cp34', 'cp35', 'py2', 'py2.py3', 'py26', 'py27', 
		'py3', 'py32, py33, py34', 'py33', 'py34', 'python', 'source'
	]
	
	PACKAGE_TYPES = [
		'bdist_dmg', 'bdist_dumb', 'bdist_egg', 'bdist_msi', 'bdist_rpm', 
		'bdist_wheel', 'bdist_wininst', 'sdist'
	]
	
	EXTENSIONS = [
		'bz2', 'deb', 'dmg', 'egg', 'exe', 'gz', 'msi', 'rpm', 'tgz', 'whl', 'zip'
	]


Use pip without internet
========================

.. code:: bash

	$ pip install --no-index --find-links=/home/user/minirepo <package-name>


I prefer to setup environment variables in my profile so I don't have to provide extra command line arguments.

.. code:: bash

	# save these 2 variable in your profile 
	$ export PIP_NO_INDEX=true
	$ export PIP_FIND_LINKS=/home/user/minirepo
	
	# then run pip as usual
	$ pip install <package-name>



