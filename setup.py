from setuptools import setup
import json

with open("metadata.json", encoding="utf-8") as fp:
    metadata = json.load(fp)

setup(
    name='lexibank_alt',
    py_modules=['lexibank_alt'],
    include_package_data=True,
    url=metadata.get("url",""),
    zip_safe=False,
    entry_points={
        'lexibank.dataset': [
            'alt=lexibank_alt:Dataset',
        ]
    },
    install_requires=[
        "pylexibank>=3.0.0"
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
