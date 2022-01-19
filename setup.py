import pathlib

from setuptools import setup, find_packages

README = (pathlib.Path(__file__).parent / 'README.md').read_text()

setup(
    name='orka_vector_api',
    version='0.1.0',
    description='Rest API for orka vector data',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://github.com/terrestris/OrKa-Vector-API',
    author='Jan Suleiman @ terrestris GmbH & Co. KG',
    author_email='info@terrestris.de',
    license='Apache-2.0',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask~=1.1.2',
        'psycopg2~=2.8.6',
        'PyYAML~=5.4.1',
        'uuid~=1.30',
        'requests~=2.25.1',
        'flasgger~=0.9.5'
    ],
)
