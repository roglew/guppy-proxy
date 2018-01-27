#!/usr/bin/env python

import pkgutil
from setuptools import setup, find_packages

VERSION = "0.1.0"

setup(name='guppyproxy',
      version=VERSION,
      description='The Guppy Intercepting Proxy',
      author='Rob Glew',
      author_email='rglew56@gmail.com',
      packages=['guppyproxy'],
      include_package_data = True,
      #package_data={'pappyproxy': ['templates', 'lists']},
      license='MIT',
      entry_points = {
          'console_scripts':['guppy = guppyproxy.gup:start'],
          },
      long_description="The Guppy Proxy",
      keywords='http proxy hacking 1337hax pwnurmum',
      install_requires=[
          #'cmd2>=0.6.8',
          #'Jinja2>=2.8',
          'Pygments>=2.0.2',
          'PyQt5>=5.9',
          ],
      classifiers=[
          'Intended Audience :: Developers',
          'Intended Audience :: Information Technology',
          'Operating System :: MacOS',
          'Operating System :: POSIX :: Linux',
          'Development Status :: 2 - Pre-Alpha',
          'Programming Language :: Python :: 3.6',
          'License :: OSI Approved :: MIT License',
          'Topic :: Security',
        ]
)
