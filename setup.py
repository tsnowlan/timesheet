from setuptools import setup

setup(
    name="timesheet",
    version="v1.0.0",
    install_requires=[
        "click>=7.1",
        "sqlalchemy>=1.3",
    ],
    python_requires=">=3.9",
    extras_require={
        "dev": [
            "black>=20.8b1",
            "flake8>=s.8.4",
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
    packages=["timesheet"],
    entry_points={
        "console_scripts": [
            "clock = timesheet:clock",
            "timesheet = timesheet:main",
        ]
    },
)
