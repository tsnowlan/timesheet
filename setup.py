#!/usr/bin/env python3
from setuptools import setup

setup(
    name="timesheet",
    version_config={
        "version_file": "timesheet/VERSION",
        "count_commits_from_version_file": True,
    },
    python_requires=">=3.9",
    setup_requires=["setuptools-git-versioning"],
    install_requires=[
        "click>=7.1",
        "sqlalchemy>=1.3,<2",
    ],
    extras_require={
        "dev": [
            "black>=23.1.0",
            "ipython>=7.19.0",
            "pdbpp>=0.10.2",
            "pylint>=2.6.0",
            "sqlalchemy-stubs>=0.3",
        ],
        "full": [
            "PyYAML>=5.3",
            "toml>=0.10.2",
        ],
    },
    include_package_data=True,
    packages=["timesheet"],
    entry_points={
        "console_scripts": [
            "clock = timesheet.cli:clock",
            "timesheet = timesheet:main",
        ]
    },
)
