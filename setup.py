from setuptools import setup, find_packages

setup(
    name='api',
    version='0.0.1',
    description='alternate django api',
    author='Victor Kotseruba',
    author_email='barbuzaster@gmail.com',
    url='https://github.com/barbuza/api',
    include_package_data=True,
    packages=find_packages(exclude=['test_project']),
    install_requires=[
        'Django >= 1.10',
        'jsonschema >= 2.5.1',
        'PyYAML >= 3.12'
    ]
)
