#!/usr/bin/env python
#
# download all source packages from https://pypi.python.org

from xml.etree import ElementTree
import urllib2
import requests
import time
import xmlrpclib

SIMPLE_URL = 'https://pypi.python.org/simple/'

def get_package_names_simple(simple_index=SIMPLE_URL):
    # resp = urllib2.urlopen(simple_index)
    # tree = ElementTree.parse(resp)
    resp = requests.get(simple_index)
    tree = ElementTree.fromstring(resp.content)
    return [a.text for a in tree.iter('a')]

def scrape_links(dist, simple_index=SIMPLE_URL):
    resp = urllib2.urlopen(simple_index + dist + '/')
    tree = ElementTree.parse(resp)
    return [a.attrib['href'] for a in tree.iter('a')]

def get_packages_names_xmlrpc():
	client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
	return client.list_packages()

def main():
	# logging.basicConfig(level=logging.INFO)
	start = time.time()
	
	# for d in sorted(get_package_names()):
	# 	link = scrape_links(d)
	# 	print link
	
	simple = get_package_names_simple()
	print len(simple)
	print 'simple:', (time.time()-start)
	
	
	start = time.time()
	xmlrpc = get_packages_names_xmlrpc()
	print len(xmlrpc)
	print 'xmlrpc:', (time.time()-start)



if __name__ == '__main__':
	main()