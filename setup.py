#!/usr/bin/env python
from setuptools import setup, find_packages

entry_points = {
	'console_scripts': [
		'publish_content = nti.deploymenttools.content.publish_content:main',
		'reindex_content = nti.deploymenttools.content.reindex:main',
		'render_content = nti.deploymenttools.content.render:main',
		'release_content = nti.deploymenttools.content.release_content:main',
		'update_content = nti.deploymenttools.content.update_content:main',
		'update_default_sharing = nti.deploymenttools.content.update_default_sharing:main',
		'build_content_catalog = nti.deploymenttools.content.build_catalog:main',
		'gc_content_catalog = nti.deploymenttools.content.gc_catalog:main',
		'nti_update_library = nti.deploymenttools.content.update_library:main',
		'nti_s3_publish_landingpage = nti.deploymenttools.landingpage.s3_publish_landing:main',
	]
}

setup(
	name = 'nti.deploymenttools',
	version = '0.0',
	keywords = 'web',
	author = 'NTI',
	author_email = 'sean.jones@nextthought.com',
	description = 'NextThought Platform Deployment Tools',
	long_description = 'Dataserver README',
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: Developers :: Education",
		"Operating System :: OS Independent",
		"Programming Language :: Python :: 2.7",
		"Framework :: Pylons :: ZODB :: Pyramid",
		"Internet :: WWW/HTTP",
		"Natural Language :: English",
		"Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
		],
        requires = [ 'nti.dataserver' ],
	packages = find_packages( 'src' ),
	package_dir = {'': 'src'},
        package_data = {'nti': [ 'deploymenttools/content/default_sharing.json' ]},
	include_package_data = True,
	namespace_packages=['nti',],
	zip_safe = False,
	entry_points = entry_points
	)
