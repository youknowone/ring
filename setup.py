from __future__ import with_statement

from setuptools import setup


def get_version():
    with open('cachain/version.txt') as f:
        return f.read().strip()


def get_readme():
    try:
        with open('README.rst') as f:
            return f.read().strip()
    except IOError:
        return ''


setup(
    name='cachain',
    version=get_version(),
    description='Cache chain manager for abstract models.',
    long_description=get_readme(),
    author='Jeong YunWon',
    author_email='cachain@youknowone.org',
    url='https://github.com/youknowone/cachain',
    packages=(
        'cachain',
    ),
    package_data={
        'cachain': ['version.txt']
    },
    install_requires=[
        'prettyexc>=0.6.0',
    ],
    tests_require=[
        'pytest', 'tox', 'mock', 'patch',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
