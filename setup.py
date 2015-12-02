try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

requirements = [
    'argparse==1.2.1',
    'backports.ssl-match-hostname==3.4.0.2',
    'certifi==2015.04.28',
    'cookies==2.2.1',
    'funcsigs==0.4',
    'mock==1.3.0',
    'pbr==1.3.0',
    'py==1.4.30',
    'pytest==2.7.2',
    'requests==2.7.0',
    'responses==0.4.0',
    'six==1.9.0',
    'tornado==4.2.1',
    'wsgiref==0.1.2',
    'python-consul==0.4.5',
]

test_requirements = [
    'pytest'
]

setup(
    name='teleport',
    description='teleportation device',
    author='quatrix',
    author_email='evil.legacy@gmail.com',
    url='https://github.com/quatrix/teleport',
    version='1.0.32',
    packages=['teleport'],
    install_requires=requirements,
    tests_require=test_requirements,
)
