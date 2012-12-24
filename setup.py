#!/usr/bin/python

from distutils.core import setup

setup(name='Pamac',
      version='0.2',
      description='A gtk3 frontend for pyalpm',
      license='GPL',
      author='Guillaume Benoit',
      author_email='guillaume@manjaro.org',
      url='https://git.manjaro.org/core/pamac',
      packages=['backend'],
     )