from setuptools import setup, find_packages

setup(
    name='orka_vector_api',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask~=1.1.2',
        'psycopg2-binary~=2.8.6',
        'PyYAML~=5.4.1',
        'uuid~=1.30',
        'requests~=2.25.1',
        'flasgger~=0.9.5'
    ],
)
