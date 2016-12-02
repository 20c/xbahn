
from setuptools import find_packages, setup


version = open('facsimile/VERSION').read().strip()
requirements = open('facsimile/requirements.txt').read().split("\n")
test_requirements = open('facsimile/requirements-test.txt').read().split("\n")


setup(
    name='xbahn',
    version=version,
    author='20C',
    author_email='code@20c.com',
    description='xbahn description',
    long_description='',
    license='LICENSE.txt',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: Apache Software License',
    ],
    packages = find_packages(),
    include_package_data=True,
    #url='https://github.com/20c/xbahn',
    #download_url='https://github.com/20c/xbahn/%s' % version,

    entry_points={
        'console_scripts' : [
            'engineer=xbahn.engineer:engineer'
        ]
    },

    install_requires=requirements,
    test_requires=test_requirements,

    zip_safe=True
)
