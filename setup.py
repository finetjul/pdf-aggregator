import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pdf-aggregator",
    version="0.0.1",
    author="Julien Finet",
    author_email="julien.finet@kitware.com",
    description="Aggregate account PDF statements into JSON and visualize aggregated financial data as timeline",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/finetjul/pdf-aggregator",
    packages=setuptools.find_packages(exclude=["tests"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: OS Independent",
    ],
    keywords='pdf aggregate extract banking financial statement',
    # Define an executable calls pdf-aggregator from a specific file
    entry_points={
        'console_scripts': [
            'pdf-aggregator = aggregator.aggregate:main',
            'pdf-plot = aggregator.plot:main'
        ]
    },
    python_requires='>=3.6',
)
