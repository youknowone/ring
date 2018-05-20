from __future__ import with_statement

from setuptools import setup
import sys


def get_version():
    with open('ring/version.txt') as f:
        return f.read().strip()


install_requires = [
    'prettyexc>=0.6.0',
]
tests_require = [
    'pytest>=3.0.2', 'pytest-cov', 'pytest-lazy-fixture', 'mock', 'patch',
    'pymemcache',
    'redis', 'requests',
    'diskcache',
    'django',
]
docs_require = [
    'sphinx',
    'django',
]

dev_require = tests_require + docs_require

try:
    import __pypy__  # noqa
except ImportError:
    # CPython-only
    tests_require.extend([
        'pylibmc',
    ])

# new feature support
if (3, 3) <= sys.version_info:
    if sys.version_info < (3, 5):
        tests_require.append('pytest-asyncio==0.5.0')
    else:
        tests_require.append('pytest-asyncio')
    tests_require.extend([
        'aiomcache',
        'aioredis>=1.0.0',
    ])

if sys.version_info[0] == 2:
    tests_require.extend([
        'python-memcached',
    ])
else:
    tests_require.extend([
        'python3-memcached',
    ])

# backports - py2
if sys.version_info[0] == 2:
    install_requires.extend([
        'inspect2==0.1.0',
        'functools32==3.2.3-2',
    ])

# backports - py34
if sys.version_info[:2] <= (3, 4):
    install_requires.extend([
        'typing',
    ])
    if (3, 3) <= sys.version_info[:2]:
        install_requires.extend([
            'asyncio',
        ])


def get_readme():
    try:
        with open('README.rst') as f:
            return f.read().strip()
    except IOError:
        return ''


setup(
    name='ring',
    version=get_version(),
    description='Shift cache paradigm to code and forget about storages. With built-in memcache & redis + asyncio support.',
    long_description=get_readme(),
    author='Jeong YunWon',
    author_email='ring@youknowone.org',
    url='https://github.com/youknowone/ring',
    packages=(
        'ring',
    ),
    package_data={
        'ring': ['version.txt'],
    },
    install_requires=install_requires,
    tests_require=tests_require + ['tox', 'tox-pyenv'],
    extras_require={
        'tests': tests_require,
        'docs': docs_require,
        'dev': dev_require,
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)  # noqa
