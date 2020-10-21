from setuptools import setup
import sqlalchemy

setup(
    name="timesheet",
    version="v23",
    install_requires=["sqlalchemy~=1.3", "click~=7"],
    packages=["timesheet"],
    entry_points={"console_scripts": ["timesheet = timesheet:main"]},
)