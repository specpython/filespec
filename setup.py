from distutils.core import setup

files = ["*.py"]

setup(name="filespec",
   version = "1.0",
   description = "python module to access spec data files",
   author = "Bixente Rey Bakaikoa",
   author_email = "txo@txolutions.com",
   url = "http://www.certif.com",
   packages = ['src'],
   package_data = {'src': files},  
   scripts = {"specfile"}, 
   long_description = """
This module gives full access to scans recorded in files writing with the spec file format.

The spec file format organizes scans (data from experimental acquisitions sequences) in blocks
inside a file.  Each block of data if preceded by a header block containing the metadata 
associated with the acquisition.

For a full description of the format and the description of its organization and keywords
refer to the documentation distributed with this package.

spec is an application by Certified Scientific Software (http://www.certif.com/)
specialized in instrument control and data acquisition in X-Ray diffraction experiments
and it is largely used and many synchrotrons, universities and laboratories around the
world.
"""

)
