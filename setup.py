from setuptools import setup

setup(
    name='Configuration Difference generator',
    version='1.0',
    py_modules=['run'],
    install_requires=[
        'click',
        'netmiko',
        'colorama',
        'PyYAML',
        # 'genie',
        # 'pyats'
    ],
    entry_points='''
        [console_scripts]
        run=run:cli
    '''
)