from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in lifelong_erpnext/__init__.py
from lifelong_erpnext import __version__ as version

setup(
	name="lifelong_erpnext",
	version=version,
	description="Lifelong ERPNext",
	author="Frappe",
	author_email="contact@erpnext.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
